import type { DocumentSummary, EvalRunDetail, EvalRunSummary, IngestResult, StreamEvent } from "./types";

// In dev, Vite proxies "/api" to the local backend (see vite.config.ts). In
// production the frontend and backend are deployed separately, so this must
// point at the deployed backend's absolute URL — set via VITE_API_BASE_URL
// at build time (see DEPLOYMENT.md).
const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const res = await fetch(`${BASE}/documents`);
  if (!res.ok) throw new Error(`Failed to load documents: ${res.status}`);
  return res.json();
}

export async function fetchEvalRuns(): Promise<EvalRunSummary[]> {
  const res = await fetch(`${BASE}/eval/runs`);
  if (!res.ok) throw new Error(`Failed to load eval runs: ${res.status}`);
  return res.json();
}

export async function fetchEvalRunDetail(runId: number): Promise<EvalRunDetail> {
  const res = await fetch(`${BASE}/eval/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to load eval run ${runId}: ${res.status}`);
  return res.json();
}

export async function uploadDocument(file: File, sourceUrl?: string): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  if (sourceUrl) form.append("source_url", sourceUrl);
  const res = await fetch(`${BASE}/ingest`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function* streamAsk(query: string, topK?: number): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${BASE}/ask/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, ...(topK ? { top_k: topK } : {}) }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`Ask failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      if (frame.startsWith("data: ")) {
        yield JSON.parse(frame.slice("data: ".length)) as StreamEvent;
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
}
