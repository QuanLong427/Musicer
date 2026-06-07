"use client";

import { useEffect, useRef } from "react";

const PARTICLE_COUNT = 300;
const ROTATION_SPEED = 0.0003; // ~0.02 deg/frame at 60fps

interface Particle {
  x: number;
  y: number;
  baseX: number;
  baseY: number;
  size: number;
  alpha: number;
  baseAlpha: number;
  twinkleSpeed: number;
  twinkleOffset: number;
  color: string;
}

function createParticles(w: number, h: number): Particle[] {
  const particles: Particle[] = [];
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const x = Math.random() * w;
    const y = Math.random() * h;
    const size = 0.5 + Math.random() * 1.5; // 0.5-2px
    const baseAlpha = 0.3 + Math.random() * 0.5;

    // Muted colors: whites, soft blues, faint warm tones
    const colorChoice = Math.random();
    let color: string;
    if (colorChoice < 0.5) {
      // White-ish
      const lightness = 80 + Math.random() * 20;
      color = `hsl(220, ${10 + Math.random() * 15}%, ${lightness}%)`;
    } else if (colorChoice < 0.8) {
      // Soft blue
      color = `hsl(${210 + Math.random() * 20}, ${20 + Math.random() * 20}%, ${75 + Math.random() * 15}%)`;
    } else {
      // Faint warm
      color = `hsl(${40 + Math.random() * 20}, ${15 + Math.random() * 15}%, ${80 + Math.random() * 15}%)`;
    }

    particles.push({
      x,
      y,
      baseX: x,
      baseY: y,
      size,
      alpha: baseAlpha,
      baseAlpha,
      twinkleSpeed: 0.5 + Math.random() * 2, // varying frequencies
      twinkleOffset: Math.random() * Math.PI * 2,
      color,
    });
  }
  return particles;
}

export function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = window.innerWidth;
    let h = window.innerHeight;
    canvas.width = w;
    canvas.height = h;

    let particles = createParticles(w, h);
    let angle = 0;
    let animationId: number;

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      const time = performance.now() * 0.001;

      ctx.clearRect(0, 0, w, h);

      // Slow rotation around center
      angle += ROTATION_SPEED;
      const cx = w / 2;
      const cy = h / 2;
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);

      for (const p of particles) {
        // Rotate around center
        const dx = p.baseX - cx;
        const dy = p.baseY - cy;
        p.x = cx + dx * cosA - dy * sinA;
        p.y = cy + dx * sinA + dy * cosA;

        // Twinkle
        const twinkle = Math.sin(time * p.twinkleSpeed + p.twinkleOffset);
        p.alpha = p.baseAlpha * (0.6 + 0.4 * twinkle);

        // Draw
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha;
        ctx.fill();
      }

      ctx.globalAlpha = 1;
    };

    animate();

    const onResize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w;
      canvas.height = h;
      particles = createParticles(w, h);
    };

    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100%",
        zIndex: 0,
        pointerEvents: "none",
      }}
    />
  );
}
