import type { GoldenPage, WorkspaceSnapshot } from "./types";

interface SavePageResponse {
  page: GoldenPage;
  revision: string;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T | { error: string };
  if (!response.ok) {
    const message = "error" in (payload as { error?: string })
      ? (payload as { error: string }).error
      : `请求失败：${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

export async function loadWorkspace(): Promise<WorkspaceSnapshot> {
  return parseResponse<WorkspaceSnapshot>(
    await fetch("/api/workspace", { cache: "no-store" }),
  );
}

export async function savePage(
  page: GoldenPage,
  revision: string,
): Promise<SavePageResponse> {
  return parseResponse<SavePageResponse>(
    await fetch(`/api/pages/${page.page_number}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page, revision }),
    }),
  );
}
