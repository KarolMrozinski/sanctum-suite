"use client";

import React, { useEffect, useRef } from "react";

export default function ThreeAttackMatrix() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let angle = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = 60;

      angle += 0.02;

      // Rysowanie 3D Orbital Nodes
      for (let i = 0; i < 6; i++) {
        const currentAngle = angle + (i * Math.PI) / 3;
        const x = centerX + Math.cos(currentAngle) * radius;
        const y = centerY + Math.sin(currentAngle) * (radius / 2);
        const z = Math.sin(currentAngle);

        ctx.beginPath();
        ctx.arc(x, y, 6 + z * 3, 0, 2 * Math.PI);
        ctx.fillStyle = i % 2 === 0 ? "#38bdf8" : "#f43f5e";
        ctx.shadowBlur = 10;
        ctx.shadowColor = ctx.fillStyle;
        ctx.fill();

        // Połączenia ze środkiem
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(x, y);
        ctx.strokeStyle = "rgba(56, 189, 248, 0.2)";
        ctx.stroke();
      }

      // Główny rdzeń
      ctx.beginPath();
      ctx.arc(centerX, centerY, 12, 0, 2 * Math.PI);
      ctx.fillStyle = "#a855f7";
      ctx.shadowBlur = 15;
      ctx.shadowColor = "#a855f7";
      ctx.fill();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg flex flex-col items-center">
      <h4 className="text-xs text-slate-400 uppercase tracking-wider mb-2 font-mono">
        🌐 3D Threat Matrix Canvas
      </h4>
      <canvas ref={canvasRef} width={280} height={160} className="rounded bg-slate-950 border border-slate-800" />
    </div>
  );
}