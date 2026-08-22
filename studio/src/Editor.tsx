import { useCallback, useEffect, useRef, useState } from "react";

import { savePage } from "./api";
import { DocumentCanvas } from "./components/DocumentCanvas";
import { Inspector } from "./components/Inspector";
import { StatusBar } from "./components/StatusBar";
import { Toolbar } from "./components/Toolbar";
import { collectReviewQueue, contentAspectForBlock, invalidateAspects } from "./review";
import type {
  BoundingBox,
  EditorTool,
  GoldenBlock,
  GoldenPage,
  PredictionBlock,
  PredictionPage,
  ReviewAspect,
  Selection,
} from "./types";

interface EditorProps {
  initialPage: GoldenPage;
  imageUrl: string;
  prediction: PredictionPage | undefined;
  initialRevision: string;
  sourcePageCount: number;
  onSaved: (page: GoldenPage, revision: string) => void;
}

function predictionContent(block: PredictionBlock) {
  const index = block.selected_candidate ?? 0;
  return block.candidates[index]?.content ?? null;
}

function acceptedBlock(
  block: PredictionBlock,
  engine: string,
  engineVersion: string | null,
  configurationHash: string | null,
): GoldenBlock {
  const content = predictionContent(block);
  return {
    id: block.id,
    type: block.type,
    bbox: block.bbox,
    source_transcription: block.type === "formula" ? null : content,
    latex: block.type === "formula" ? content : null,
    notes: null,
    suggested_by: {
      engine,
      engine_version: engineVersion,
      configuration_hash: configurationHash,
      block_id: block.id,
    },
    verified_aspects: [],
  };
}

export function Editor({
  initialPage,
  imageUrl,
  prediction,
  initialRevision,
  sourcePageCount,
  onSaved,
}: EditorProps) {
  const [page, setPage] = useState(initialPage);
  const [past, setPast] = useState<GoldenPage[]>([]);
  const [future, setFuture] = useState<GoldenPage[]>([]);
  const [selection, setSelection] = useState<Selection>(null);
  const [tool, setTool] = useState<EditorTool>("select");
  const [zoom, setZoom] = useState(0.82);
  const [fitPage, setFitPage] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const revisionRef = useRef(initialRevision);
  const pageRef = useRef(page);
  const saveSequence = useRef(0);
  const updateFitZoom = useCallback((nextZoom: number) => {
    setZoom((current) => Math.abs(current - nextZoom) < 0.005 ? current : nextZoom);
  }, []);

  useEffect(() => {
    pageRef.current = page;
  }, [page]);

  const commit = useCallback((
    update: (current: GoldenPage) => GoldenPage,
    invalidatedAspects: readonly ReviewAspect[] = [],
  ) => {
    setPage((current) => {
      setPast((history) => [...history.slice(-49), current]);
      setFuture([]);
      const next = update(current);
      return invalidateAspects(next, invalidatedAspects);
    });
    setDirty(true);
    setError(null);
    saveSequence.current += 1;
  }, []);

  const persist = useCallback(async (pageToSave?: GoldenPage) => {
    const target = pageToSave ?? pageRef.current;
    const sequence = saveSequence.current;
    setSaving(true);
    setError(null);
    try {
      const result = await savePage(target, revisionRef.current);
      revisionRef.current = result.revision;
      onSaved(result.page, result.revision);
      if (sequence === saveSequence.current) setDirty(false);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }, [onSaved]);

  useEffect(() => {
    if (!dirty || saving) return;
    const timer = window.setTimeout(() => void persist(), 900);
    return () => window.clearTimeout(timer);
  }, [dirty, page, persist, saving]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return;
      if (event.key.toLowerCase() === "v") setTool("select");
      if (event.key.toLowerCase() === "b") setTool("draw");
      if ((event.key === "Delete" || event.key === "Backspace") && selection?.layer === "golden") {
        event.preventDefault();
        const id = selection.id;
        commit((current) => ({
          ...current,
          blocks: current.blocks.filter((block) => block.id !== id),
          reading_order: current.reading_order.filter((blockId) => blockId !== id),
        }), ["layout"]);
        setSelection(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commit, selection]);

  const createBlock = (bbox: BoundingBox) => {
    const id = `p${page.page_number}-g${crypto.randomUUID().slice(0, 8)}`;
    const block: GoldenBlock = {
      id,
      type: "unknown",
      bbox,
      source_transcription: null,
      latex: null,
      notes: null,
      suggested_by: null,
      verified_aspects: [],
    };
    commit((current) => ({
      ...current,
      blocks: [...current.blocks, block],
      reading_order: [...current.reading_order, id],
    }), ["layout"]);
    setSelection({ layer: "golden", id });
    setTool("select");
  };

  const updateBlock = (id: string, patch: Partial<GoldenBlock>) => {
    const invalidated: ReviewAspect[] = [];
    if (patch.bbox || patch.type) invalidated.push("layout");
    commit((current) => ({
      ...current,
      blocks: current.blocks.map((block) => {
        if (block.id !== id) return block;
        const next = { ...block, ...patch };
        if (patch.type) next.verified_aspects = [];
        if ("source_transcription" in patch) {
          next.verified_aspects = next.verified_aspects.filter((item) => item !== "transcription");
        }
        if ("latex" in patch) {
          next.verified_aspects = next.verified_aspects.filter((item) => item !== "formula");
        }
        return next;
      }),
    }), invalidated);
  };

  const acceptPrediction = (block: PredictionBlock) => {
    if (page.blocks.some((existing) => existing.id === block.id)) {
      setSelection({ layer: "golden", id: block.id });
      return;
    }
    const accepted = acceptedBlock(
      block,
      prediction?.engine ?? "unknown",
      prediction?.engine_version ?? null,
      prediction?.configuration_hash ?? null,
    );
    commit((current) => ({
      ...current,
      blocks: [...current.blocks, accepted],
      reading_order: [...current.reading_order, accepted.id],
    }), ["layout"]);
    setSelection({ layer: "golden", id: accepted.id });
  };

  const acceptAll = () => {
    if (!prediction) return;
    commit((current) => {
      const existing = new Set(current.blocks.map((block) => block.id));
      const additions = prediction.blocks
        .filter((block) => !existing.has(block.id))
        .map((block) => acceptedBlock(
          block,
          prediction.engine,
          prediction.engine_version,
          prediction.configuration_hash,
        ));
      return {
        ...current,
        blocks: [...current.blocks, ...additions],
        reading_order: [...current.reading_order, ...additions.map((block) => block.id)],
      };
    }, ["layout"]);
  };

  const undo = () => {
    const previous = past.at(-1);
    if (!previous) return;
    setPast((history) => history.slice(0, -1));
    setFuture((history) => [page, ...history].slice(0, 50));
    setPage(previous);
    setDirty(true);
    saveSequence.current += 1;
  };

  const redo = () => {
    const next = future[0];
    if (!next) return;
    setFuture((history) => history.slice(1));
    setPast((history) => [...history.slice(-49), page]);
    setPage(next);
    setDirty(true);
    saveSequence.current += 1;
  };

  const verifyAspect = (aspect: ReviewAspect) => {
    if (pageRef.current.verified_aspects.includes(aspect)) return;
    const verified: GoldenPage = {
      ...pageRef.current,
      verified_aspects: [...pageRef.current.verified_aspects, aspect],
    };
    setPast((history) => [...history.slice(-49), pageRef.current]);
    setFuture([]);
    setPage(verified);
    pageRef.current = verified;
    setDirty(true);
    setError(null);
    saveSequence.current += 1;
    void persist(verified);
  };

  const verifyBlock = (id: string) => {
    const current = pageRef.current;
    const block = current.blocks.find((candidate) => candidate.id === id);
    if (!block) return;
    const aspect = contentAspectForBlock(block);
    const content = aspect === "formula" ? block.latex : block.source_transcription;
    if (!aspect || !content?.trim() || block.verified_aspects.includes(aspect)) return;
    const verified = {
      ...current,
      blocks: current.blocks.map((candidate) => candidate.id === id
        ? { ...candidate, verified_aspects: [...candidate.verified_aspects, aspect] }
        : candidate),
    };
    setPast((history) => [...history.slice(-49), current]);
    setFuture([]);
    setPage(verified);
    pageRef.current = verified;
    setDirty(true);
    setError(null);
    saveSequence.current += 1;
    const next = collectReviewQueue(verified)[0];
    setSelection(next ? { layer: "golden", id: next.blockId } : null);
    void persist(verified);
  };

  return (
    <>
      <main className="editor-main">
        <section className="document-stage">
          <Toolbar
            tool={tool}
            zoom={zoom}
            canUndo={past.length > 0}
            canRedo={future.length > 0}
            fitPage={fitPage}
            onToolChange={setTool}
            onZoomChange={(nextZoom) => {
              setFitPage(false);
              setZoom(nextZoom);
            }}
            onUndo={undo}
            onRedo={redo}
            onFitPage={() => setFitPage(true)}
          />
          <DocumentCanvas
            imageUrl={imageUrl}
            zoom={zoom}
            tool={tool}
            blocks={page.blocks}
            predictions={prediction?.blocks ?? []}
            selection={selection}
            fitPage={fitPage}
            onSelect={setSelection}
            onCreate={createBlock}
            onChangeBbox={(id, bbox) => updateBlock(id, { bbox })}
            onFitZoom={updateFitZoom}
          />
        </section>
        <Inspector
          page={page}
          imageUrl={imageUrl}
          prediction={prediction}
          selection={selection}
          saving={saving}
          error={error}
          onSelect={setSelection}
          onUpdateBlock={updateBlock}
          onDeleteBlock={(id) => {
            commit((current) => ({
              ...current,
              blocks: current.blocks.filter((block) => block.id !== id),
              reading_order: current.reading_order.filter((blockId) => blockId !== id),
            }), ["layout"]);
            setSelection(null);
          }}
          onAcceptPrediction={acceptPrediction}
          onAcceptAll={acceptAll}
          onReorder={(sourceId, targetId) => commit((current) => {
            if (!sourceId || sourceId === targetId) return current;
            const order = current.reading_order.filter((id) => id !== sourceId);
            const targetIndex = order.indexOf(targetId);
            if (targetIndex < 0) return current;
            order.splice(targetIndex, 0, sourceId);
            return { ...current, reading_order: order };
          }, ["reading_order"])}
          onSave={() => void persist()}
          onVerifyAspect={verifyAspect}
          onVerifyBlock={verifyBlock}
        />
      </main>
      <StatusBar
        pageNumber={page.page_number}
        sourcePageCount={sourcePageCount}
        zoom={zoom}
        verifiedAspects={page.verified_aspects}
        dirty={dirty}
        saving={saving}
      />
    </>
  );
}
