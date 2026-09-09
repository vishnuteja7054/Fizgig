export type SectionKey =
  | "start"
  | "prep"
  | "captions"
  | "samples"
  | "training"
  | "profiler"
  | "repair"
  | "explorer"
  | "royale"
  | "extract"
  | "metadata"
  | "preferences"
  | "jobs";

export type DatasetKind = "image" | "video" | "audio";

export interface DatasetItem {
  relative_path: string;
  kind: DatasetKind;
  caption_relative_path: string;
  has_caption: boolean;
}

export interface DatasetScan {
  folder: string;
  items: DatasetItem[];
}
