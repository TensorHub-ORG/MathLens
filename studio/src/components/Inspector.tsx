import { lazy, Suspense, useCallback, useEffect, useState } from "react";

import { CheckIcon, GripIcon, SaveIcon, TrashIcon } from "../icons";
import {
  canVerifyPage,
  collectReviewQueue,
  contentAspectForBlock,
  reviewAspectLabels,
} from "../review";
import { SourceCrop } from "./SourceCrop";
import type {
  BlockType,
  GoldenBlock,
  GoldenPage,
  PredictionBlock,
  PredictionPage,
  ReviewAspect,
  Selection,
} from "../types";

const FormulaPreview = lazy(() => import("./FormulaPreview"));
const reviewAspects: ReviewAspect[] = ["layout", "reading_order"];

const blockTypeLabels: Record<BlockType, string> = {
  title: "标题",
  text: "文本",
  formula: "公式",
  figure: "图像",
  table: "表格",
  page_header: "页眉",
  page_footer: "页脚",
  page_number: "页码",
  unknown: "未知",
};

interface InspectorProps {
  page: GoldenPage;
  imageUrl: string;
  prediction: PredictionPage | undefined;
  selection: Selection;
  saving: boolean;
  error: string | null;
  onSelect: (selection: Selection) => void;
  onUpdateBlock: (id: string, patch: Partial<GoldenBlock>) => void;
  onDeleteBlock: (id: string) => void;
  onAcceptPrediction: (block: PredictionBlock) => void;
  onAcceptAll: () => void;
  onReorder: (sourceId: string, targetId: string) => void;
  onSave: () => void;
  onVerifyAspect: (aspect: ReviewAspect) => void;
  onVerifyBlock: (id: string) => void;
}

export function Inspector({
  page,
  imageUrl,
  prediction,
  selection,
  saving,
  error,
  onSelect,
  onUpdateBlock,
  onDeleteBlock,
  onAcceptPrediction,
  onAcceptAll,
  onReorder,
  onSave,
  onVerifyAspect,
  onVerifyBlock,
}: InspectorProps) {
  const golden = selection?.layer === "golden"
    ? page.blocks.find((block) => block.id === selection.id)
    : undefined;
  const suggestion = selection?.layer === "prediction"
    ? prediction?.blocks.find((block) => block.id === selection.id)
    : undefined;
  const candidate = suggestion?.selected_candidate == null
    ? suggestion?.candidates[0]
    : suggestion.candidates[suggestion.selected_candidate];
  const queue = collectReviewQueue(page);
  const contentAspect = golden ? contentAspectForBlock(golden) : null;
  const contentVerified = contentAspect
    ? golden?.verified_aspects.includes(contentAspect)
    : false;
  const previewLatex = golden?.type === "formula"
    ? golden.latex
    : suggestion?.type === "formula" ? candidate?.content : null;
  const [formulaValid, setFormulaValid] = useState(true);
  const handleFormulaValidity = useCallback((valid: boolean) => setFormulaValid(valid), []);
  useEffect(() => setFormulaValid(true), [golden?.id, previewLatex]);

  return (
    <aside className="inspector">
      <section className="inspector-section selection-section">
        <div className="panel-heading">
          <span>标注</span>
          <div className="legend">
            <span><i className="legend-model" />模型建议</span>
            <span><i className="legend-golden" />人工真值</span>
          </div>
        </div>
        {golden ? (
          <div className="field-stack">
            <div className="selection-title">
              <div>
                <span className="eyeline">
                  人工真值 · {golden.id}
                  {golden.suggested_by ? ` · 建议来源 ${golden.suggested_by.engine}` : ""}
                </span>
                <strong>{blockTypeLabels[golden.type]}</strong>
              </div>
              <button className="icon-danger" type="button" aria-label="删除标注" onClick={() => onDeleteBlock(golden.id)}>
                <TrashIcon />
              </button>
            </div>
            <SourceCrop imageUrl={imageUrl} bbox={golden.bbox} />
            <label>
              <span>类型</span>
              <select value={golden.type} onChange={(event) => onUpdateBlock(golden.id, { type: event.target.value as BlockType })}>
                {Object.entries(blockTypeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <div className="bbox-grid">
              {(["x0", "y0", "x1", "y1"] as const).map((coordinate) => (
                <label key={coordinate}>
                  <span>{coordinate}</span>
                  <input
                    type="number"
                    min="0"
                    max="1000"
                    value={Math.round(golden.bbox[coordinate] * 10) / 10}
                    onChange={(event) => onUpdateBlock(golden.id, {
                      bbox: { ...golden.bbox, [coordinate]: Number(event.target.value) },
                    })}
                  />
                </label>
              ))}
            </div>
            <label>
              <span>原文转写</span>
              <textarea rows={5} value={golden.source_transcription ?? ""} onChange={(event) => onUpdateBlock(golden.id, { source_transcription: event.target.value || null })} />
            </label>
            <label>
              <span>LaTeX</span>
              <textarea className="code-field" rows={4} spellCheck={false} value={golden.latex ?? ""} onChange={(event) => onUpdateBlock(golden.id, { latex: event.target.value || null })} />
            </label>
            {previewLatex ? (
              <Suspense fallback={<p className="formula-loading">正在载入公式渲染器…</p>}>
                <FormulaPreview latex={previewLatex} onValidityChange={handleFormulaValidity} />
              </Suspense>
            ) : null}
            {contentAspect ? (
              <button
                type="button"
                className={contentVerified ? "content-verified" : "primary"}
                disabled={saving || contentVerified || !formulaValid || !(golden.latex || golden.source_transcription)?.trim()}
                onClick={() => onVerifyBlock(golden.id)}
              >
                <CheckIcon />
                {contentVerified
                  ? `${reviewAspectLabels[contentAspect]}已确认`
                  : `确认${reviewAspectLabels[contentAspect]}并前往下一项`}
              </button>
            ) : null}
            <label>
              <span>标注备注</span>
              <textarea rows={2} value={golden.notes ?? ""} onChange={(event) => onUpdateBlock(golden.id, { notes: event.target.value || null })} />
            </label>
          </div>
        ) : suggestion ? (
          <div className="suggestion-card">
            <span className="eyeline">{prediction?.engine} {prediction?.engine_version}</span>
            <strong>{blockTypeLabels[suggestion.type]} · {suggestion.id}</strong>
            <p>{candidate?.content || "没有候选内容"}</p>
            {previewLatex ? (
              <Suspense fallback={<p className="formula-loading">正在载入公式渲染器…</p>}>
                <FormulaPreview latex={previewLatex} />
              </Suspense>
            ) : null}
            <button type="button" className="primary" onClick={() => onAcceptPrediction(suggestion)}>
              接受为人工真值
            </button>
          </div>
        ) : (
          <div className="empty-selection">
            <strong>选择一个标注框</strong>
            <p>检查模型建议，或使用绘制工具添加人工真值。</p>
            {prediction?.blocks.length ? (
              <button type="button" onClick={onAcceptAll}>接受本页全部建议</button>
            ) : null}
          </div>
        )}
      </section>

      <section className="inspector-section order-section">
        <div className="panel-heading">
          <span>阅读顺序</span>
          <span className="count">{page.reading_order.length}/{page.blocks.length}</span>
        </div>
        {page.reading_order.length ? (
          <ol className="order-list">
            {page.reading_order.map((id, index) => {
              const block = page.blocks.find((candidateBlock) => candidateBlock.id === id);
              if (!block) return null;
              return (
                <li
                  key={id}
                  draggable
                  onDragStart={(event) => event.dataTransfer.setData("text/plain", id)}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => onReorder(event.dataTransfer.getData("text/plain"), id)}
                >
                  <GripIcon />
                  <span>{index + 1}</span>
                  <strong>{blockTypeLabels[block.type]}</strong>
                  <small>{block.source_transcription || block.latex || block.id}</small>
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="order-empty">接受或创建标注后，阅读顺序会出现在这里。</p>
        )}
      </section>

      <section className="inspector-section review-section">
        <div className="panel-heading">
          <span>分维度复核</span>
          <span className="count">{page.verified_aspects.length}/2</span>
        </div>
        <div className="review-grid">
          {reviewAspects.map((aspect) => {
            const verified = page.verified_aspects.includes(aspect);
            return (
              <button
                type="button"
                className={verified ? "verified" : ""}
                disabled={saving || verified || !canVerifyPage(page, aspect)}
                key={aspect}
                onClick={() => onVerifyAspect(aspect)}
              >
                <CheckIcon />
                <span>{reviewAspectLabels[aspect]}</span>
                <small>{verified ? "已验证" : "待验证"}</small>
              </button>
            );
          })}
        </div>
        <div className="risk-list">
          <div><strong>内容复核队列</strong><span>{queue.length}</span></div>
          {queue.length ? queue.map((risk) => (
            <button
              type="button"
              key={`${risk.blockId}-${risk.aspect}`}
              onClick={() => onSelect({ layer: "golden", id: risk.blockId })}
            >
              <span>{risk.blockId}</span><small>{risk.priority === "sample" ? "抽样 · " : "重点 · "}{risk.reason}</small>
            </button>
          )) : <p>本页重点项与稳定抽样均已完成。</p>}
        </div>
      </section>

      <section className="inspector-actions">
        {error ? <p className="save-error" role="alert">{error}</p> : null}
        <button type="button" onClick={onSave} disabled={saving}>
          <SaveIcon />立即保存
        </button>
        <p>修改会自动撤销受影响维度的验证，不再重复复核无关内容。</p>
      </section>
    </aside>
  );
}
