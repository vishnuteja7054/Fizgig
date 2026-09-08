"""Browser-safe dataset and caption-sidecar operations.

The first browser vertical slice needs to inspect and edit a dataset without
depending on Tk widgets or loading any model.  The service intentionally scans
the dataset root only, matching Fizgig's current training-folder behavior:
subfolders such as ``removed`` are not treated as training items.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from typing import BinaryIO
from pathlib import Path

from fizgig.app.state import WorkspacePaths


IMAGE_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif",
})
VIDEO_EXTENSIONS = frozenset({".mp4"})
AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".flac", ".m4a"})
IMPORT_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | {".txt"}


@dataclass(frozen=True)
class DatasetItem:
    """A media item and its conventional caption sidecar."""

    relative_path: str
    kind: str
    caption_relative_path: str
    has_caption: bool


class DatasetService:
    """Operate on one workspace without exposing arbitrary filesystem paths."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.paths = WorkspacePaths(workspace_root)

    @staticmethod
    def _kind(path: Path, *, include_video: bool, include_audio: bool) -> str | None:
        extension = path.suffix.lower()
        if extension in IMAGE_EXTENSIONS:
            return "image"
        if include_video and extension in VIDEO_EXTENSIONS:
            return "video"
        if include_audio and extension in AUDIO_EXTENSIONS:
            return "audio"
        return None

    def _dataset_root(self, folder: str | Path) -> Path:
        root = self.paths.resolve_child(folder)
        if not root.is_dir():
            raise NotADirectoryError(f"dataset folder does not exist: {folder}")
        return root

    def scan(
        self,
        folder: str | Path,
        *,
        include_video: bool = True,
        include_audio: bool = True,
    ) -> list[DatasetItem]:
        """List supported top-level media files in deterministic order."""

        root = self._dataset_root(folder)
        items: list[DatasetItem] = []
        for path in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
            if not path.is_file():
                continue
            kind = self._kind(path, include_video=include_video, include_audio=include_audio)
            if kind is None:
                continue
            caption = path.with_suffix(".txt")
            items.append(DatasetItem(
                relative_path=path.relative_to(self.paths.root).as_posix(),
                kind=kind,
                caption_relative_path=caption.relative_to(self.paths.root).as_posix(),
                has_caption=caption.is_file(),
            ))
        return items

    def read_caption(self, item: str | Path) -> str:
        media = self.paths.resolve_child(item)
        caption = media.with_suffix(".txt")
        if not caption.is_file():
            return ""
        return caption.read_text(encoding="utf-8-sig").strip()

    @staticmethod
    def is_importable_filename(filename: str) -> bool:
        """Return whether a browser upload belongs in a dataset root."""

        return Path(filename).suffix.lower() in IMPORT_EXTENSIONS

    def import_file(self, folder: str | Path, filename: str, source: BinaryIO) -> str:
        """Copy one browser-selected media/caption file into a dataset folder.

        The browser is allowed to send a filename, never an arbitrary server
        path. Only the basename is used and existing files are not replaced.
        """

        if not self.is_importable_filename(filename):
            raise ValueError(f"unsupported dataset file: {filename}")
        name = Path(filename).name
        if not name or name in {".", ".."}:
            raise ValueError("uploaded filename is invalid")
        root = self.paths.resolve_child(folder)
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise NotADirectoryError(f"dataset folder does not exist: {folder}")
        destination = root / name
        if destination.exists():
            raise FileExistsError(f"dataset file already exists: {destination.name}")
        with destination.open("wb") as handle:
            shutil.copyfileobj(source, handle)
        return destination.relative_to(self.paths.root).as_posix()

    def write_caption(self, item: str | Path, text: str) -> Path:
        media = self.paths.resolve_child(item)
        if not media.is_file():
            raise FileNotFoundError(f"dataset item does not exist: {item}")
        value = str(text).strip()
        if not value:
            raise ValueError("caption cannot be empty")
        caption = media.with_suffix(".txt")
        caption.write_text(value + "\n", encoding="utf-8")
        return caption

    def move_to_removed(self, item: str | Path) -> tuple[str, str | None]:
        """Move media and caption to ``removed`` without ever deleting them."""

        media = self.paths.resolve_child(item)
        if not media.is_file():
            raise FileNotFoundError(f"dataset item does not exist: {item}")
        destination_dir = media.parent / "removed"
        destination_dir.mkdir(exist_ok=True)
        destination = self._unique_destination(destination_dir / media.name)
        shutil.move(str(media), str(destination))

        caption = media.with_suffix(".txt")
        caption_destination: Path | None = None
        if caption.is_file():
            caption_destination = self._unique_destination(destination_dir / caption.name)
            shutil.move(str(caption), str(caption_destination))

        return (
            destination.relative_to(self.paths.root).as_posix(),
            caption_destination.relative_to(self.paths.root).as_posix()
            if caption_destination else None,
        )

    def find_replace(
        self,
        folder: str | Path,
        find: str,
        replace: str,
        *,
        apply: bool = False,
    ) -> list[dict[str, str]]:
        """Return literal, case-insensitive caption replacements.

        ``apply=False`` is a preview.  Replacement text is inserted through a
        function so backslashes in user text are never interpreted as regex
        replacement syntax.
        """

        if not str(find):
            raise ValueError("find text cannot be empty")
        pattern = re.compile(re.escape(str(find)), re.IGNORECASE)
        root = self._dataset_root(folder)
        results: list[dict[str, str]] = []
        for caption in sorted(root.glob("*.txt"), key=lambda p: p.name.casefold()):
            old = caption.read_text(encoding="utf-8-sig")
            new = pattern.sub(lambda _match: str(replace), old)
            if old == new:
                continue
            result = {
                "caption_relative_path": caption.relative_to(self.paths.root).as_posix(),
                "old": old,
                "new": new,
            }
            results.append(result)
            if apply:
                caption.write_text(new, encoding="utf-8")
        return results

    @staticmethod
    def _unique_destination(path: Path) -> Path:
        if not path.exists():
            return path
        stem, suffix = path.stem, path.suffix
        index = 1
        while True:
            candidate = path.with_name(f"{stem}_{index}{suffix}")
            if not candidate.exists():
                return candidate
            index += 1
