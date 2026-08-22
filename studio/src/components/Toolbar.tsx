import { BoxIcon, PointerIcon, RedoIcon, UndoIcon } from "../icons";
import type { EditorTool } from "../types";

interface ToolbarProps {
  tool: EditorTool;
  zoom: number;
  canUndo: boolean;
  canRedo: boolean;
  fitPage: boolean;
  onToolChange: (tool: EditorTool) => void;
  onZoomChange: (zoom: number) => void;
  onUndo: () => void;
  onRedo: () => void;
  onFitPage: () => void;
}

export function Toolbar({
  tool,
  zoom,
  canUndo,
  canRedo,
  fitPage,
  onToolChange,
  onZoomChange,
  onUndo,
  onRedo,
  onFitPage,
}: ToolbarProps) {
  return (
    <div className="toolbar" role="toolbar" aria-label="标注工具">
      <div className="tool-group">
        <button
          className={tool === "select" ? "selected" : ""}
          type="button"
          aria-label="选择和调整标注框"
          title="选择 (V)"
          onClick={() => onToolChange("select")}
        >
          <PointerIcon />
        </button>
        <button
          className={tool === "draw" ? "selected" : ""}
          type="button"
          aria-label="绘制标注框"
          title="绘制标注框 (B)"
          onClick={() => onToolChange("draw")}
        >
          <BoxIcon />
        </button>
      </div>
      <div className="tool-separator" />
      <div className="tool-group">
        <button type="button" aria-label="撤销" onClick={onUndo} disabled={!canUndo}>
          <UndoIcon />
        </button>
        <button type="button" aria-label="重做" onClick={onRedo} disabled={!canRedo}>
          <RedoIcon />
        </button>
      </div>
      <div className="tool-separator" />
      <button
        type="button"
        className={`fit-page-button ${fitPage ? "selected" : ""}`}
        aria-label="缩放以显示完整页面"
        title="适合整页"
        onClick={onFitPage}
      >
        整页
      </button>
      <div className="tool-separator" />
      <label className="zoom-control">
        <span>缩放</span>
        <input
          type="range"
          min="25"
          max="145"
          step="5"
          value={Math.round(zoom * 100)}
          onChange={(event) => onZoomChange(Number(event.target.value) / 100)}
        />
        <output>{Math.round(zoom * 100)}%</output>
      </label>
    </div>
  );
}
