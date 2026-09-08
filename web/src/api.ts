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
