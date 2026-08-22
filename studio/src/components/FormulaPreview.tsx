import { useEffect } from "react";

import katex from "katex";
import "katex/dist/katex.min.css";

interface FormulaPreviewProps {
  latex: string;
  onValidityChange?: (valid: boolean) => void;
}

export default function FormulaPreview({ latex, onValidityChange }: FormulaPreviewProps) {
  let html = "";
  let errorMessage: string | null = null;
  try {
    html = katex.renderToString(latex, {
      displayMode: true,
      strict: "warn",
      throwOnError: true,
      trust: false,
    });
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : "无法渲染此公式";
  }
  useEffect(() => onValidityChange?.(errorMessage === null), [errorMessage, onValidityChange]);
  if (errorMessage) return <p className="formula-error" role="alert">{errorMessage}</p>;
  return <div className="formula-preview" dangerouslySetInnerHTML={{ __html: html }} />;
}
