import { useEffect, useMemo, useState } from "react";

import { loadWorkspace } from "./api";
import { PageRail } from "./components/PageRail";
import { Editor } from "./Editor";
import type { GoldenPage, WorkspaceSnapshot } from "./types";

export default function App() {
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot | null>(null);
  const [activePage, setActivePage] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void loadWorkspace()
      .then((snapshot) => {
        if (cancelled) return;
        setWorkspace(snapshot);
        const preferred = snapshot.dataset.pages.find((page) => page.page_number === 7)
          ?? snapshot.dataset.pages.find((page) => snapshot.prediction_pages[String(page.page_number)])
          ?? snapshot.dataset.pages[0];
        setActivePage(preferred?.page_number ?? null);
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : "无法载入工作区");
      });
    return () => { cancelled = true; };
  }, []);

  const predictionPageNumbers = useMemo(
    () => new Set(Object.keys(workspace?.prediction_pages ?? {}).map(Number)),
    [workspace?.prediction_pages],
  );

  if (loadError) {
    return <div className="load-state error-state"><strong>无法打开 Golden Workbench</strong><p>{loadError}</p></div>;
  }
  if (!workspace || activePage == null) {
    return <div className="load-state"><div className="loading-mark" /><span>载入标注工作区…</span></div>;
  }

  const page = workspace.dataset.pages.find((candidate) => candidate.page_number === activePage);
  if (!page) return null;

  const handleSaved = (savedPage: GoldenPage, revision: string) => {
    setWorkspace((current) => current ? {
      ...current,
      revision,
      dataset: {
        ...current.dataset,
        pages: current.dataset.pages.map((candidate) => candidate.page_number === savedPage.page_number ? savedPage : candidate),
      },
    } : current);
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="wordmark"><span>MathCraft</span><strong>Golden Workbench</strong></div>
        <div className="document-identity">
          <strong>{workspace.dataset.source.filename}</strong>
          <span>{workspace.dataset.dataset_id}</span>
        </div>
        <div className="header-meta"><span>300 DPI</span><span>本地工作区</span></div>
      </header>
      <div className="workbench-grid">
        <PageRail
          pages={workspace.dataset.pages}
          activePage={activePage}
          imageUrls={workspace.image_urls}
          thumbnailUrls={workspace.thumbnail_urls}
          predictionPages={predictionPageNumbers}
          onSelect={setActivePage}
        />
        <Editor
          key={activePage}
          initialPage={page}
          imageUrl={workspace.image_urls[String(activePage)]}
          prediction={workspace.prediction_pages[String(activePage)]}
          initialRevision={workspace.revision}
          sourcePageCount={workspace.dataset.source_page_count}
          onSaved={handleSaved}
        />
      </div>
    </div>
  );
}
