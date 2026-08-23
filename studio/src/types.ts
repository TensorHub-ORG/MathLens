export type BlockType =
  | "title"
  | "text"
  | "formula"
  | "figure"
  | "table"
  | "page_header"
  | "page_footer"
  | "page_number"
  | "unknown";

export type ReviewAspect = "layout" | "reading_order" | "transcription" | "formula";

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  space: "normalized";
}

export interface GoldenBlock {
  id: string;
  type: BlockType;
  bbox: BoundingBox;
  source_transcription: string | null;
  latex: string | null;
  notes: string | null;
  suggested_by: {
    engine: string;
    engine_version: string | null;
    configuration_hash: string | null;
    block_id: string;
  } | null;
  verified_aspects: ReviewAspect[];
}

export interface GoldenPage {
  page_number: number;
  strata: string[];
  rationale: string;
  verified_aspects: ReviewAspect[];
  image_artifact_id: string | null;
  blocks: GoldenBlock[];
  reading_order: string[];
}

export interface GoldenDataset {
  schema: "mathcraft.golden-dataset.v3";
  dataset_id: string;
  source: { filename: string; sha256: string };
  source_page_count: number;
  render_dpi: number;
  pages: GoldenPage[];
}

export interface PredictionBlock {
  id: string;
  type: BlockType;
  bbox: BoundingBox;
  candidates: Array<{
    content: string;
    engine: string;
    engine_version: string | null;
    confidence: number | null;
  }>;
  selected_candidate: number | null;
}

export interface PredictionPage {
  engine: string;
  engine_version: string;
  configuration_hash: string;
  blocks: PredictionBlock[];
}

export interface WorkspaceSnapshot {
  dataset: GoldenDataset;
  revision: string;
  prediction_pages: Record<string, PredictionPage>;
  image_urls: Record<string, string>;
  thumbnail_urls: Record<string, string>;
}

export type Selection =
  | { layer: "golden"; id: string }
  | { layer: "prediction"; id: string }
  | null;

export type EditorTool = "select" | "draw";
