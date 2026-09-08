import type { DatasetItem, DatasetScan } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // Keep the HTTP status when the server did not return JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function scanDataset(folder: string): Promise<DatasetScan> {
  const params = new URLSearchParams({ folder });
  return request<DatasetScan>(`/api/datasets/scan?${params}`);
}

export function loadWorkspaceState(): Promise<{ values: Record<string, unknown> }> {
  return request("/api/workspace/state");
}

export function updateWorkspaceState(values: Record<string, unknown>) {
  return request<{ values: Record<string, unknown> }>("/api/workspace/state", {
    method: "PATCH",
    body: JSON.stringify({ values }),
  });
}

export function importDataset(folder: string, files: File[]) {
  const form = new FormData();
  form.append("folder", folder);
  files.forEach((file) => form.append("files", file, file.name));
  return request<{ folder: string; imported: string[]; skipped: string[] }>(
    "/api/datasets/import",
    { method: "POST", body: form },
  );
}

export interface ImagePrepResult {
  folder: string;
  mode: "resize_only";
  target_megapixels: number;
  target_area: number;
  converted: number;
  skipped: number;
  errors: number;
  files: Array<{
    source_relative_path: string;
    output_relative_path: string | null;
    status: "converted" | "skipped" | "error";
    original_size: [number, number] | null;
    output_size: [number, number] | null;
    detail: string;
  }>;
}

export function resizeOnly(folder: string, targetMegapixels: number, replaceOriginals: boolean) {
  return request<ImagePrepResult>("/api/image-prep/resize-only", {
    method: "POST",
    body: JSON.stringify({
      folder,
      target_megapixels: targetMegapixels,
      replace_originals: replaceOriginals,
    }),
  });
}

export interface TrainingConfigResult {
  config_relative_path: string;
  content: string;
}

export interface TrainingLaunchValues {
  architecture: string;
  dataset_config: string;
  dit: string;
  output_dir: string;
  output_name: string;
  vae: string;
  text_encoder: string;
  network_dim: number;
  network_alpha: number;
  learning_rate: number;
  max_train_epochs: number;
  save_every_n_epochs: number;
  blocks_to_swap: number | string;
  gradient_checkpointing: boolean;
}

export interface TrainingCommandPreview {
  architecture: string;
  command: string[];
  shell_command: string;
  working_directory: string;
  execution_ready: boolean;
}

export function previewTrainingCommand(values: TrainingLaunchValues) {
  return request<TrainingCommandPreview>("/api/training/command-preview", {
    method: "POST",
    body: JSON.stringify({
      ...values,
      seed: 42,
      optimizer_type: "adamw8bit",
      save_state: true,
      save_state_on_train_end: true,
    }),
  });
}

export function startTrainingJob(values: TrainingLaunchValues) {
  return request<JobRecord>("/api/training/start", {
    method: "POST",
    body: JSON.stringify({
      ...values,
      seed: 42,
      optimizer_type: "adamw8bit",
      save_state: true,
      save_state_on_train_end: true,
    }),
  });
}

export function writeTrainingDatasetConfig(values: {
  name: string;
  folder: string;
  target_megapixels: number;
  batch_size: number;
  caption_extension: string;
  enable_bucket: boolean;
  bucket_no_upscale: boolean;
  cache_root: string;
}) {
  return request<TrainingConfigResult>("/api/training/dataset-config", {
    method: "POST",
    body: JSON.stringify(values),
  });
}

export function listPresets(architecture: string) {
  return request<{ architecture: string; names: string[] }>(
    `/api/presets/${encodeURIComponent(architecture)}`,
  );
}

export function loadPreset(architecture: string, name: string) {
  return request<Record<string, unknown>>(
    `/api/presets/${encodeURIComponent(architecture)}/${encodeURIComponent(name)}`,
  );
}

export function savePreset(architecture: string, name: string, values: Record<string, unknown>, overwrite: boolean) {
  return request<{ architecture: string; name: string; values: Record<string, unknown> }>(
    `/api/presets/${encodeURIComponent(architecture)}/${encodeURIComponent(name)}`,
    { method: "PUT", body: JSON.stringify({ values, overwrite }) },
  );
}

export function deletePreset(architecture: string, name: string) {
  return request<{ architecture: string; name: string }>(
    `/api/presets/${encodeURIComponent(architecture)}/${encodeURIComponent(name)}`,
    { method: "DELETE" },
  );
}

export interface JobRecord {
  id: string;
  kind: string;
  status: "queued" | "starting" | "running" | "cancel_requested" | "completed" | "failed" | "cancelled";
  progress: number;
  message: string;
  payload: Record<string, unknown>;
  result: unknown;
  error: string | null;
}

export function startResizeOnlyJob(folder: string, targetMegapixels: number, replaceOriginals: boolean) {
  return request<JobRecord>("/api/jobs", {
    method: "POST",
    body: JSON.stringify({
      kind: "image_prep.resize_only",
      payload: {
        folder,
        target_megapixels: targetMegapixels,
        replace_originals: replaceOriginals,
      },
    }),
  });
}

export function getJob(jobId: string) {
  return request<JobRecord>(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function readCaption(item: string): Promise<{ item: string; text: string }> {
  const params = new URLSearchParams({ item });
  return request(`/api/datasets/caption?${params}`);
}

export function writeCaption(item: string, text: string) {
  return request<{ item: string; text: string }>("/api/datasets/caption", {
    method: "PUT",
    body: JSON.stringify({ item, text }),
  });
}

export function removeDatasetItem(item: string) {
  return request<{ media_relative_path: string; caption_relative_path: string | null }>(
    "/api/datasets/remove",
    { method: "POST", body: JSON.stringify({ item }) },
  );
}

export type { DatasetItem };
