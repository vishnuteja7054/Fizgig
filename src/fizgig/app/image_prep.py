"""Frontend-neutral image preparation operations.

The first browser slice exposes Fizgig's non-model ``Resize Only`` mode.  It
keeps the same area-based sizing rule as the desktop GUI and never overwrites
an unrelated output file.
"""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from fizgig.app.dataset import IMAGE_EXTENSIONS
from fizgig.app.state import WorkspacePaths


@dataclass(frozen=True)
class PrepFileResult:
    source_relative_path: str
    output_relative_path: str | None
    status: str
    original_size: tuple[int, int] | None = None
    output_size: tuple[int, int] | None = None
    detail: str = ""


@dataclass(frozen=True)
class PrepResult:
    folder: str
    target_megapixels: float
    target_area: int
    converted: int
    skipped: int
    errors: int
    files: tuple[PrepFileResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "folder": self.folder,
            "mode": "resize_only",
            "target_megapixels": self.target_megapixels,
            "target_area": self.target_area,
            "converted": self.converted,
            "skipped": self.skipped,
            "errors": self.errors,
            "files": [
                {
                    "source_relative_path": item.source_relative_path,
                    "output_relative_path": item.output_relative_path,
                    "status": item.status,
                    "original_size": item.original_size,
                    "output_size": item.output_size,
                    "detail": item.detail,
                }
                for item in self.files
            ],
        }


class ImagePrepService:
    """Prepare top-level dataset images without importing the desktop GUI."""

    BUCKET_STEP = 16

    def __init__(self, workspace_root: str | Path) -> None:
        self.paths = WorkspacePaths(workspace_root)

    @classmethod
    def target_area_for_megapixels(cls, value: float) -> int:
        try:
            megapixels = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("target megapixels must be a number") from exc
        if not math.isfinite(megapixels) or megapixels <= 0 or megapixels > 100:
            raise ValueError("target megapixels must be greater than 0 and at most 100")
        side = max(
            cls.BUCKET_STEP,
            int(math.sqrt(megapixels * 1_000_000)) // cls.BUCKET_STEP * cls.BUCKET_STEP,
        )
        return side * side

    @classmethod
    def _resize(cls, image: Image.Image, target_area: int) -> tuple[Image.Image, bool]:
        width, height = image.size
        if width * height <= target_area:
            return image, False
        scale = math.sqrt(target_area / (width * height))
        new_width = max(cls.BUCKET_STEP, int(width * scale) // cls.BUCKET_STEP * cls.BUCKET_STEP)
        new_height = max(cls.BUCKET_STEP, int(height * scale) // cls.BUCKET_STEP * cls.BUCKET_STEP)
        if (new_width, new_height) == image.size:
            return image, False
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS), True

    def resize_only(
        self,
        folder: str | Path,
        target_megapixels: float = 1.0,
        *,
        replace_originals: bool = False,
    ) -> PrepResult:
        """Convert top-level images to PNG, preserving aspect ratio and captions."""

        root = self.paths.resolve_child(folder)
        if not root.is_dir():
            raise NotADirectoryError(f"dataset folder does not exist: {folder}")
        target_area = self.target_area_for_megapixels(target_megapixels)
        original_dirs: dict[Path, Path] = {}
        results: list[PrepFileResult] = []
        converted = skipped = errors = 0

        for source in sorted(root.iterdir(), key=lambda path: path.name.casefold()):
            if not source.is_file() or source.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            relative_source = source.relative_to(self.paths.root).as_posix()
            try:
                with Image.open(source) as opened:
                    image = opened.convert("RGBA" if "A" in opened.getbands() else "RGB")
                original_size = image.size
                processed, resized = self._resize(image, target_area)
                output = self._safe_output_path(source, root / f"{source.stem}.png")
                if output == source and not resized and source.suffix.lower() == ".png":
                    image.close()
                    skipped += 1
                    results.append(PrepFileResult(
                        relative_source, relative_source, "skipped", original_size, original_size,
                        "already PNG and at or below target",
                    ))
                    continue

                if output == source and not replace_originals:
                    originals = original_dirs.setdefault(root, self._originals_dir(root))
                    originals.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, originals / source.name)
                self._atomic_png_save(processed, output)
                processed.close()
                if output != source:
                    if replace_originals:
                        source.unlink()
                    else:
                        originals = original_dirs.setdefault(root, self._originals_dir(root))
                        originals.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(source), str(self._unique_destination(originals / source.name)))
                output_relative = output.relative_to(self.paths.root).as_posix()
                with Image.open(output) as saved:
                    output_size = saved.size
                converted += 1
                results.append(PrepFileResult(
                    relative_source, output_relative, "converted", original_size, output_size,
                ))
            except Exception as exc:  # one bad image must not abort the batch
                errors += 1
                results.append(PrepFileResult(relative_source, None, "error", detail=str(exc)))

        return PrepResult(
            folder=str(folder),
            target_megapixels=float(target_megapixels),
            target_area=target_area,
            converted=converted,
            skipped=skipped,
            errors=errors,
            files=tuple(results),
        )

    @staticmethod
    def _atomic_png_save(image: Image.Image, output: Path) -> None:
        temporary = output.with_name(output.name + ".fizgig-tmp")
        try:
            image.save(temporary, "PNG")
            temporary.replace(output)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _safe_output_path(source: Path, output: Path) -> Path:
        if not output.exists():
            return output
        try:
            if output.samefile(source):
                return output
        except OSError:
            pass
        stem, suffix = output.stem, output.suffix
        index = 2
        while True:
            candidate = output.with_name(f"{stem}_{index}{suffix}")
            if not candidate.exists():
                return candidate
            index += 1

    @staticmethod
    def _originals_dir(root: Path) -> Path:
        candidate = root / "originals"
        index = 2
        while candidate.exists() and any(path.is_file() for path in candidate.iterdir()):
            candidate = root / f"originals_{index}"
            index += 1
        return candidate

    @staticmethod
    def _unique_destination(path: Path) -> Path:
        if not path.exists():
            return path
        index = 2
        while True:
            candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
            if not candidate.exists():
                return candidate
            index += 1
