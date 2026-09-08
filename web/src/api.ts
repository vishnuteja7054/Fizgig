import type { DatasetItem, DatasetScan } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
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
