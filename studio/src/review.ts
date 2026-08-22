import type { BlockType, GoldenPage, ReviewAspect } from "./types";

export const reviewAspectLabels: Record<ReviewAspect, string> = {
  layout: "版面与类型",
  reading_order: "阅读顺序",
  transcription: "原文转写",
  formula: "公式 LaTeX",
};

const transcribableTypes = new Set<BlockType>([
  "title",
  "text",
  "table",
  "page_header",
  "page_footer",
  "page_number",
]);

export function canVerifyPage(page: GoldenPage, aspect: ReviewAspect): boolean {
  if (aspect === "layout") return page.blocks.length > 0;
  if (!page.verified_aspects.includes("layout")) return false;
  if (aspect === "reading_order") {
    return page.reading_order.length === page.blocks.length
      && new Set(page.reading_order).size === page.blocks.length;
  }
  return false;
}

export function invalidateAspects(
  page: GoldenPage,
  aspects: readonly ReviewAspect[],
): GoldenPage {
  const invalid = new Set(aspects);
  if (invalid.has("layout")) {
    return { ...page, verified_aspects: [] };
  }
  return {
    ...page,
    verified_aspects: page.verified_aspects.filter((aspect) => !invalid.has(aspect)),
  };
}

export interface ReviewRisk {
  blockId: string;
  aspect: "transcription" | "formula";
  reason: string;
  priority: "risk" | "sample";
}

function hasBalancedBraces(value: string): boolean {
  let depth = 0;
  for (const character of value) {
    if (character === "{") depth += 1;
    if (character === "}") depth -= 1;
    if (depth < 0) return false;
  }
  return depth === 0;
}

function stableSample(blockId: string): boolean {
  let hash = 2166136261;
  for (const character of blockId) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) % 10 === 0;
}

export function contentAspectForBlock(block: GoldenPage["blocks"][number]) {
  if (block.type === "formula") return "formula" as const;
  if (transcribableTypes.has(block.type)) return "transcription" as const;
  return null;
}

export function collectReviewQueue(page: GoldenPage): ReviewRisk[] {
  const risks: ReviewRisk[] = [];
  for (const block of page.blocks) {
    const aspect = contentAspectForBlock(block);
    if (!aspect || block.verified_aspects.includes(aspect)) continue;
    if (block.type === "formula") {
      const latex = block.latex?.trim() ?? "";
      if (!latex) {
        risks.push({ blockId: block.id, aspect, reason: "缺少 LaTeX", priority: "risk" });
      } else if (!hasBalancedBraces(latex)) {
        risks.push({ blockId: block.id, aspect, reason: "花括号不平衡", priority: "risk" });
      } else if (/\\qqua(?!d)|\?{2,}|�/.test(latex)) {
        risks.push({ blockId: block.id, aspect, reason: "包含可疑字符或命令", priority: "risk" });
      } else {
        risks.push({ blockId: block.id, aspect, reason: "公式视觉复核", priority: "risk" });
      }
    } else if (transcribableTypes.has(block.type) && !block.source_transcription?.trim()) {
      risks.push({ blockId: block.id, aspect, reason: "缺少原文转写", priority: "risk" });
    } else if (stableSample(block.id)) {
      risks.push({ blockId: block.id, aspect, reason: "10% 稳定抽样", priority: "sample" });
    }
  }
  return risks.sort((first, second) => first.priority.localeCompare(second.priority));
}
