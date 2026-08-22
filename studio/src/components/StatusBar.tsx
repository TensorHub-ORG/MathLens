import type { ReviewAspect } from "../types";

interface StatusBarProps {
  pageNumber: number;
  sourcePageCount: number;
  zoom: number;
  verifiedAspects: ReviewAspect[];
  dirty: boolean;
  saving: boolean;
}

export function StatusBar({
  pageNumber,
  sourcePageCount,
  zoom,
  verifiedAspects,
  dirty,
  saving,
}: StatusBarProps) {
  const saveLabel = saving ? "正在保存" : dirty ? "等待自动保存" : "已自动保存";
  return (
    <footer className="status-bar">
      <div><span className={`save-dot ${dirty ? "dirty" : ""}`} />{saveLabel}</div>
      <div className="status-center">坐标：归一化 0–1000 · Golden Schema v3</div>
      <div>
        <span>结构 {verifiedAspects.length}/2</span>
        <span>{Math.round(zoom * 100)}%</span>
        <span>第 {pageNumber} 页 / {sourcePageCount}</span>
      </div>
    </footer>
  );
}
