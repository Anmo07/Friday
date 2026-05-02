'use client';

import { useEffect, useRef } from 'react';

export function WaveformVisualizer({ audioBuffer }: { audioBuffer: Float32Array }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d')!;
    const width = canvas.width;
    const height = canvas.height;

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      // Dark background with neon cyan waveform
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = '#0ff';
      const slice = audioBuffer.slice(0, Math.min(audioBuffer.length, 128));
      slice.forEach((sample, i) => {
        const x = (i / slice.length) * width;
        const y = (1 + sample) * height / 2;
        ctx.fillRect(x, height - y, 2, y);
      });
      animationRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animationRef.current);
  }, [audioBuffer]);

  return <canvas ref={canvasRef} width={256} height={100} className="bg-black" />;
}
