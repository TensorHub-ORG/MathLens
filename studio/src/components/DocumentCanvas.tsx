import { useLayoutEffect, useMemo, useRef, useState } from "react";

import type {
  BoundingBox,
  EditorTool,
  GoldenBlock,
  PredictionBlock,
  Selection,
} from "../types";

interface DocumentCanvasProps {
  imageUrl: string;
  zoom: number;
  tool: EditorTool;
  blocks: GoldenBlock[];
  predictions: PredictionBlock[];
  selection: Selection;
  fitPage: boolean;
  onSelect: (selection: Selection) => void;
  onCreate: (bbox: BoundingBox) => void;
  onChangeBbox: (id: string, bbox: BoundingBox) => void;
  onFitZoom: (zoom: number) => void;
}

type Handle = "nw" | "ne" | "se" | "sw";
type Gesture =
  | { mode: "draw"; startX: number; startY: number }
  | {
      mode: "move" | "resize";
      id: string;
      startX: number;
      startY: number;
      original: BoundingBox;
      handle?: Handle;
    };

const clamp = (value: number) => Math.max(0, Math.min(1000, value));

function pointerPosition(event: React.PointerEvent<SVGSVGElement>) {
  const bounds = event.currentTarget.getBoundingClientRect();
  return {
    x: clamp(((event.clientX - bounds.left) / bounds.width) * 1000),
    y: clamp(((event.clientY - bounds.top) / bounds.height) * 1000),
  };
}

function normalizedBox(x0: number, y0: number, x1: number, y1: number): BoundingBox {
  return {
    x0: Math.min(x0, x1),
    y0: Math.min(y0, y1),
    x1: Math.max(x0, x1),
    y1: Math.max(y0, y1),
    space: "normalized",
  };
}

export function DocumentCanvas({
  imageUrl,
  zoom,
  tool,
  blocks,
  predictions,
  selection,
  fitPage,
  onSelect,
  onCreate,
  onChangeBbox,
  onFitZoom,
}: DocumentCanvasProps) {
  const scrollContainer = useRef<HTMLDivElement | null>(null);
  const pageImage = useRef<HTMLImageElement | null>(null);
  const gesture = useRef<Gesture | null>(null);
  const [draft, setDraft] = useState<BoundingBox | null>(null);
  const liveBox = useRef<{ id: string; bbox: BoundingBox } | null>(null);
  const [, renderLiveBox] = useState(0);
  const acceptedIds = useMemo(() => new Set(blocks.map((block) => block.id)), [blocks]);
  const visiblePredictions = useMemo(
    () => predictions.filter((block) => !acceptedIds.has(block.id)),
    [acceptedIds, predictions],
  );

  useLayoutEffect(() => {
    if (!fitPage) return;
    const container = scrollContainer.current;
    const image = pageImage.current;
    if (!container || !image) return;
    const updateFit = () => {
      if (!image.naturalWidth || !image.naturalHeight) return;
      const style = window.getComputedStyle(container);
      const horizontalPadding = Number.parseFloat(style.paddingLeft)
        + Number.parseFloat(style.paddingRight);
      const verticalPadding = Number.parseFloat(style.paddingTop)
        + Number.parseFloat(style.paddingBottom);
      const availableWidth = Math.max(1, container.clientWidth - horizontalPadding);
      const availableHeight = Math.max(1, container.clientHeight - verticalPadding);
      const baseHeight = 620 * image.naturalHeight / image.naturalWidth;
      const nextZoom = Math.max(
        0.25,
        Math.min(1.45, availableWidth / 620, availableHeight / baseHeight),
      );
      onFitZoom(Math.floor(nextZoom * 100) / 100);
    };
    let frameRequest = 0;
    const scheduleFit = () => {
      window.cancelAnimationFrame(frameRequest);
      frameRequest = window.requestAnimationFrame(updateFit);
    };
    const observer = new ResizeObserver(scheduleFit);
    observer.observe(container);
    image.addEventListener("load", scheduleFit);
    scheduleFit();
    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frameRequest);
      image.removeEventListener("load", scheduleFit);
    };
  }, [fitPage, onFitZoom]);

  const previewBbox = (id: string, bbox: BoundingBox) => {
    liveBox.current = { id, bbox };
    renderLiveBox((version) => version + 1);
  };

  const handlePointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    const position = pointerPosition(event);
    const target = event.target as SVGElement;
    const blockId = target.dataset.blockId;
    const handle = target.dataset.handle as Handle | undefined;
    event.currentTarget.setPointerCapture(event.pointerId);

    if (tool === "draw" && !blockId) {
      gesture.current = { mode: "draw", startX: position.x, startY: position.y };
      setDraft(normalizedBox(position.x, position.y, position.x + 1, position.y + 1));
      onSelect(null);
      return;
    }
    if (blockId && target.dataset.layer === "golden") {
      const block = blocks.find((candidate) => candidate.id === blockId);
      if (!block) return;
      onSelect({ layer: "golden", id: blockId });
      gesture.current = {
        mode: handle ? "resize" : "move",
        id: blockId,
        startX: position.x,
        startY: position.y,
        original: block.bbox,
        handle,
      };
      return;
    }
    if (blockId) {
      onSelect({ layer: "prediction", id: blockId });
      return;
    }
    onSelect(null);
  };

  const handlePointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const active = gesture.current;
    if (!active) return;
    const position = pointerPosition(event);
    if (active.mode === "draw") {
      setDraft(normalizedBox(active.startX, active.startY, position.x, position.y));
      return;
    }
    const deltaX = position.x - active.startX;
    const deltaY = position.y - active.startY;
    if (active.mode === "move") {
      const width = active.original.x1 - active.original.x0;
      const height = active.original.y1 - active.original.y0;
      const x0 = Math.max(0, Math.min(1000 - width, active.original.x0 + deltaX));
      const y0 = Math.max(0, Math.min(1000 - height, active.original.y0 + deltaY));
      previewBbox(active.id, normalizedBox(x0, y0, x0 + width, y0 + height));
      return;
    }
    let { x0, y0, x1, y1 } = active.original;
    if (active.handle?.includes("n")) y0 = clamp(active.original.y0 + deltaY);
    if (active.handle?.includes("s")) y1 = clamp(active.original.y1 + deltaY);
    if (active.handle?.includes("w")) x0 = clamp(active.original.x0 + deltaX);
    if (active.handle?.includes("e")) x1 = clamp(active.original.x1 + deltaX);
    if (Math.abs(x1 - x0) >= 4 && Math.abs(y1 - y0) >= 4) {
      previewBbox(active.id, normalizedBox(x0, y0, x1, y1));
    }
  };

  const handlePointerUp = (event: React.PointerEvent<SVGSVGElement>) => {
    const active = gesture.current;
    gesture.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
    if (active?.mode === "draw" && draft) {
      if (draft.x1 - draft.x0 >= 5 && draft.y1 - draft.y0 >= 5) onCreate(draft);
      setDraft(null);
    }
    if ((active?.mode === "move" || active?.mode === "resize") && liveBox.current) {
      onChangeBbox(active.id, liveBox.current.bbox);
      liveBox.current = null;
      renderLiveBox((version) => version + 1);
    }
  };

  return (
    <div ref={scrollContainer} className={`canvas-scroll tool-${tool}`}>
      <div className="paper-shell" style={{ width: `${620 * zoom}px` }}>
        <img ref={pageImage} src={imageUrl} alt="当前扫描试卷页面" draggable={false} />
        <svg
          className="annotation-layer"
          viewBox="0 0 1000 1000"
          preserveAspectRatio="none"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        >
          {visiblePredictions.map((block, index) => (
            <g key={`prediction-${block.id}`}>
              <rect
                className={`bbox prediction ${selection?.layer === "prediction" && selection.id === block.id ? "selected" : ""}`}
                x={block.bbox.x0}
                y={block.bbox.y0}
                width={block.bbox.x1 - block.bbox.x0}
                height={block.bbox.y1 - block.bbox.y0}
                data-block-id={block.id}
                data-layer="prediction"
                vectorEffect="non-scaling-stroke"
              />
              <text className="bbox-label prediction-label" x={block.bbox.x0} y={Math.max(12, block.bbox.y0 - 4)}>
                M{index + 1}
              </text>
            </g>
          ))}
          {blocks.map((block, index) => {
            const selected = selection?.layer === "golden" && selection.id === block.id;
            const bbox = liveBox.current?.id === block.id ? liveBox.current.bbox : block.bbox;
            return (
              <g key={`golden-${block.id}`}>
                <rect
                  className={`bbox golden ${selected ? "selected" : ""}`}
                  x={bbox.x0}
                  y={bbox.y0}
                  width={bbox.x1 - bbox.x0}
                  height={bbox.y1 - bbox.y0}
                  data-block-id={block.id}
                  data-layer="golden"
                  vectorEffect="non-scaling-stroke"
                />
                <text className="bbox-label golden-label" x={bbox.x0} y={Math.max(12, bbox.y0 - 4)}>
                  {index + 1}
                </text>
                {selected
                  ? ([
                      ["nw", bbox.x0, bbox.y0],
                      ["ne", bbox.x1, bbox.y0],
                      ["se", bbox.x1, bbox.y1],
                      ["sw", bbox.x0, bbox.y1],
                    ] as const).map(([handle, cx, cy]) => (
                      <circle
                        key={handle}
                        className="resize-handle"
                        cx={cx}
                        cy={cy}
                        r="7"
                        data-block-id={block.id}
                        data-layer="golden"
                        data-handle={handle}
                        vectorEffect="non-scaling-stroke"
                      />
                    ))
                  : null}
              </g>
            );
          })}
          {draft ? (
            <rect
              className="bbox draft"
              x={draft.x0}
              y={draft.y0}
              width={draft.x1 - draft.x0}
              height={draft.y1 - draft.y0}
              vectorEffect="non-scaling-stroke"
            />
          ) : null}
        </svg>
      </div>
    </div>
  );
}
