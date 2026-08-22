import type { GoldenPage } from "../types";

interface PageRailProps {
  pages: GoldenPage[];
  activePage: number;
  imageUrls: Record<string, string>;
  thumbnailUrls: Record<string, string>;
  predictionPages: Set<number>;
  onSelect: (pageNumber: number) => void;
}

export function PageRail({
  pages,
  activePage,
  imageUrls,
  thumbnailUrls,
  predictionPages,
  onSelect,
}: PageRailProps) {
  return (
    <aside className="page-rail" aria-label="代表页面">
      <div className="panel-heading">
        <span>页面</span>
        <span className="count">{pages.length}</span>
      </div>
      <div className="page-list">
        {pages.map((page) => (
          <button
            type="button"
            className={`page-item ${activePage === page.page_number ? "active" : ""}`}
            key={page.page_number}
            onClick={() => onSelect(page.page_number)}
          >
            <div className="thumbnail-wrap">
              <img
                src={thumbnailUrls[String(page.page_number)] ?? imageUrls[String(page.page_number)]}
                alt=""
                loading="lazy"
                decoding="async"
              />
              <span>{page.page_number}</span>
            </div>
            <div className="page-item-copy">
              <strong>第 {page.page_number} 页</strong>
              <span className="status-text">
                结构 {page.verified_aspects.length}/2 · 内容 {page.blocks.filter((block) => block.verified_aspects.length).length}/{page.blocks.filter((block) => block.type !== "figure" && block.type !== "unknown").length}
              </span>
              {predictionPages.has(page.page_number) ? (
                <small>含模型建议</small>
              ) : (
                <small>暂无模型结果</small>
              )}
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
}
