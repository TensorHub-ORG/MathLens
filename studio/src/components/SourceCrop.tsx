import { useEffect, useRef } from "react";

import type { BoundingBox } from "../types";

interface SourceCropProps {
  imageUrl: string;
  bbox: BoundingBox;
}

export function SourceCrop({ imageUrl, bbox }: SourceCropProps) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const frame = frameRef.current;
    const canvas = canvasRef.current;
    if (!frame || !canvas) return;
    const crop = {
      x0: Math.max(0, bbox.x0 - 12),
      y0: Math.max(0, bbox.y0 - 24),
      x1: Math.min(1000, bbox.x1 + 12),
      y1: Math.min(1000, bbox.y1 + 24),
    };
    const image = new Image();
    image.decoding = "async";
    let lastWidth = 0;
    let frameRequest = 0;

    const render = () => {
      if (!image.naturalWidth || !image.naturalHeight) return;
      const frameWidth = frame.clientWidth;
      if (Math.abs(frameWidth - lastWidth) < 0.5) return;
      lastWidth = frameWidth;
      const cropWidth = (crop.x1 - crop.x0) * image.naturalWidth / 1000;
      const cropHeight = (crop.y1 - crop.y0) * image.naturalHeight / 1000;
      const cropRatio = cropWidth / cropHeight;
      const frameHeight = Math.max(88, Math.min(260, frameWidth / cropRatio));
      frame.style.height = `${frameHeight}px`;

      const pixelRatio = Math.min(window.devicePixelRatio, 2);
      canvas.width = Math.round(frameWidth * pixelRatio);
      canvas.height = Math.round(frameHeight * pixelRatio);
      const context = canvas.getContext("2d");
      if (!context) return;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      context.fillStyle = "#fff";
      context.fillRect(0, 0, frameWidth, frameHeight);
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = "high";

      const destinationWidth = Math.min(frameWidth, frameHeight * cropRatio);
      const destinationHeight = destinationWidth / cropRatio;
      context.drawImage(
        image,
        crop.x0 * image.naturalWidth / 1000,
        crop.y0 * image.naturalHeight / 1000,
        cropWidth,
        cropHeight,
        (frameWidth - destinationWidth) / 2,
        (frameHeight - destinationHeight) / 2,
        destinationWidth,
        destinationHeight,
      );
    };

    const scheduleRender = () => {
      window.cancelAnimationFrame(frameRequest);
      frameRequest = window.requestAnimationFrame(render);
    };
    const observer = new ResizeObserver(scheduleRender);
    observer.observe(frame);
    image.addEventListener("load", scheduleRender);
    image.src = imageUrl;
    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frameRequest);
      image.removeEventListener("load", scheduleRender);
    };
  }, [bbox.x0, bbox.x1, bbox.y0, bbox.y1, imageUrl]);

  return (
    <div ref={frameRef} className="source-crop-frame">
      <canvas ref={canvasRef} role="img" aria-label="所选块的原始扫描裁剪" />
    </div>
  );
}
