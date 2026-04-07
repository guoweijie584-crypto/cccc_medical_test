import { useRef, useEffect, useCallback, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { MemoryNodeData } from "./MemoryPalaceView";

/* ────────────────────────────────────────────────────────
   Category → color config
   ──────────────────────────────────────────────────────── */

export const CATEGORY_COLORS: Record<string, { r: number; g: number; b: number; label: string }> = {
  profile:      { r: 251, g: 191, b: 36,  label: "档案" },
  glucose:      { r: 34,  g: 211, b: 238, label: "血糖" },
  medication:   { r: 96,  g: 165, b: 250, label: "用药" },
  diet:         { r: 52,  g: 211, b: 153, label: "饮食" },
  exercise:     { r: 163, g: 230, b: 53,  label: "运动" },
  safety:       { r: 248, g: 113, b: 113, label: "安全" },
  complication: { r: 251, g: 146, b: 60,  label: "并发症" },
  consultation: { r: 167, g: 139, b: 250, label: "咨询" },
};

const DEFAULT_CLR = { r: 129, g: 140, b: 248, label: "记忆" };

function getClr(cat: string) {
  return CATEGORY_COLORS[cat] || DEFAULT_CLR;
}

/* ────────────────────────────────────────────────────────
   Particle system for background
   ──────────────────────────────────────────────────────── */

interface Star {
  x: number;
  y: number;
  r: number;
  alpha: number;
  speed: number;
  phase: number;
}

function createStars(w: number, h: number, count: number): Star[] {
  return Array.from({ length: count }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    r: Math.random() * 1.5 + 0.3,
    alpha: Math.random() * 0.5 + 0.1,
    speed: Math.random() * 0.3 + 0.1,
    phase: Math.random() * Math.PI * 2,
  }));
}

/* ────────────────────────────────────────────────────────
   Layout: force-directed-like radial
   ──────────────────────────────────────────────────────── */

interface PlacedNode {
  node: MemoryNodeData;
  x: number;
  y: number;
  size: number;
  clr: { r: number; g: number; b: number };
}

function layoutNodes(nodes: MemoryNodeData[], w: number, h: number): PlacedNode[] {
  if (!nodes.length) return [];
  const cx = w / 2, cy = h / 2;
  const grouped = new Map<string, MemoryNodeData[]>();
  for (const n of nodes) {
    const cat = n.category || "general";
    if (!grouped.has(cat)) grouped.set(cat, []);
    grouped.get(cat)!.push(n);
  }
  const cats = Array.from(grouped.keys());
  const step = (2 * Math.PI) / Math.max(cats.length, 1);
  const R = Math.min(w, h) * 0.28;
  const placed: PlacedNode[] = [];

  cats.forEach((cat, ci) => {
    const angle = step * ci - Math.PI / 2;
    const nodes = grouped.get(cat)!;
    const gcx = cx + Math.cos(angle) * R;
    const gcy = cy + Math.sin(angle) * R;
    nodes.forEach((node, ni) => {
      const subAngle = angle + ((ni - (nodes.length - 1) / 2) * 0.35);
      const subR = R * 0.15 + ni * 16;
      const x = gcx + Math.cos(subAngle) * Math.min(subR, R * 0.45);
      const y = gcy + Math.sin(subAngle) * Math.min(subR, R * 0.45);
      const size = Math.max(8, 28 - (node.priority || 3) * 3);
      placed.push({ node, x, y, size, clr: getClr(cat) });
    });
  });
  return placed;
}

/* ────────────────────────────────────────────────────────
   Canvas renderer
   ──────────────────────────────────────────────────────── */

function renderFrame(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  t: number,
  stars: Star[],
  placed: PlacedNode[],
  selectedId: string | null,
  searchIds: Set<string>,
  hoveredId: string | null,
) {
  // Clear
  ctx.clearRect(0, 0, w, h);

  // Background gradient
  const bg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.max(w, h) * 0.7);
  bg.addColorStop(0, "#0f0b2e");
  bg.addColorStop(0.5, "#0c1445");
  bg.addColorStop(1, "#060818");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, w, h);

  // Stars
  for (const s of stars) {
    const twinkle = Math.sin(t * s.speed + s.phase) * 0.3 + 0.7;
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(200,210,255,${s.alpha * twinkle})`;
    ctx.fill();
  }

  // Nebula glow in center
  const nebula = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, 120);
  nebula.addColorStop(0, "rgba(99,102,241,0.08)");
  nebula.addColorStop(0.5, "rgba(139,92,246,0.04)");
  nebula.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = nebula;
  ctx.fillRect(0, 0, w, h);

  const cx = w / 2, cy = h / 2;
  const isSearching = searchIds.size > 0;

  // Connection lines with energy flow
  for (const p of placed) {
    const dimmed = isSearching && !searchIds.has(p.node.id);
    const baseAlpha = dimmed ? 0.03 : 0.12;
    const flowPos = (Math.sin(t * 0.8 + p.x * 0.01) + 1) / 2;

    // Main line
    const grad = ctx.createLinearGradient(cx, cy, p.x, p.y);
    grad.addColorStop(0, `rgba(${p.clr.r},${p.clr.g},${p.clr.b},${baseAlpha * 0.3})`);
    grad.addColorStop(flowPos, `rgba(${p.clr.r},${p.clr.g},${p.clr.b},${baseAlpha})`);
    grad.addColorStop(1, `rgba(${p.clr.r},${p.clr.g},${p.clr.b},${baseAlpha * 0.1})`);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(p.x, p.y);
    ctx.strokeStyle = grad;
    ctx.lineWidth = dimmed ? 0.5 : 1;
    ctx.stroke();

    // Energy particle flowing along line
    if (!dimmed) {
      const ep = (t * 0.15 + p.y * 0.002) % 1;
      const ex = cx + (p.x - cx) * ep;
      const ey = cy + (p.y - cy) * ep;
      ctx.beginPath();
      ctx.arc(ex, ey, 1.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${p.clr.r},${p.clr.g},${p.clr.b},${0.6})`;
      ctx.fill();
    }
  }

  // Center hub
  const hubPulse = Math.sin(t * 1.5) * 2 + 8;
  const hubGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, hubPulse * 3);
  hubGlow.addColorStop(0, "rgba(129,140,248,0.4)");
  hubGlow.addColorStop(0.5, "rgba(129,140,248,0.1)");
  hubGlow.addColorStop(1, "rgba(129,140,248,0)");
  ctx.fillStyle = hubGlow;
  ctx.beginPath();
  ctx.arc(cx, cy, hubPulse * 3, 0, Math.PI * 2);
  ctx.fill();

  ctx.beginPath();
  ctx.arc(cx, cy, hubPulse / 2, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(199,210,254,0.9)";
  ctx.fill();

  // Memory nodes
  for (const p of placed) {
    const dimmed = isSearching && !searchIds.has(p.node.id);
    const selected = p.node.id === selectedId;
    const hovered = p.node.id === hoveredId;
    const vitality = p.node.vitality ?? 0.7;
    const pulse = Math.sin(t * (1.5 + vitality) + p.x * 0.1) * 0.3 + 0.7;
    const nodeAlpha = dimmed ? 0.1 : 1;

    // Outer glow
    const glowR = p.size * (selected ? 3.5 : hovered ? 3 : 2.5) * pulse;
    const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, glowR);
    glow.addColorStop(0, `rgba(${p.clr.r},${p.clr.g},${p.clr.b},${0.25 * vitality * nodeAlpha})`);
    glow.addColorStop(0.4, `rgba(${p.clr.r},${p.clr.g},${p.clr.b},${0.08 * vitality * nodeAlpha})`);
    glow.addColorStop(1, `rgba(${p.clr.r},${p.clr.g},${p.clr.b},0)`);
    ctx.beginPath();
    ctx.arc(p.x, p.y, glowR, 0, Math.PI * 2);
    ctx.fillStyle = glow;
    ctx.fill();

    // Pulse ring
    if (!dimmed) {
      const ringR = p.size + 4 + Math.sin(t * (1 + vitality)) * 4;
      ctx.beginPath();
      ctx.arc(p.x, p.y, ringR, 0, Math.PI * 2);
      ctx.strokeStyle = selected
        ? `rgba(251,191,36,${0.5 * pulse})`
        : `rgba(${p.clr.r},${p.clr.g},${p.clr.b},${0.3 * pulse * vitality})`;
      ctx.lineWidth = selected ? 2 : 1;
      ctx.stroke();
    }

    // Core orb
    const orbR = (p.size / 2) * (0.9 + pulse * 0.1);
    const orbGrad = ctx.createRadialGradient(p.x - orbR * 0.3, p.y - orbR * 0.3, 0, p.x, p.y, orbR);
    orbGrad.addColorStop(0, `rgba(255,255,255,${0.9 * nodeAlpha})`);
    orbGrad.addColorStop(0.3, `rgba(${p.clr.r},${p.clr.g},${p.clr.b},${0.9 * nodeAlpha})`);
    orbGrad.addColorStop(1, `rgba(${Math.max(0, p.clr.r - 40)},${Math.max(0, p.clr.g - 40)},${Math.max(0, p.clr.b - 40)},${0.8 * nodeAlpha})`);
    ctx.beginPath();
    ctx.arc(p.x, p.y, orbR, 0, Math.PI * 2);
    ctx.fillStyle = orbGrad;
    ctx.fill();

    // Highlight border for selected
    if (selected) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, orbR + 2, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(251,191,36,0.8)";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Label
    if (!dimmed) {
      ctx.font = "10px 'SF Mono', 'Fira Code', monospace";
      ctx.textAlign = "center";
      ctx.fillStyle = `rgba(255,255,255,${0.6 * nodeAlpha})`;
      ctx.fillText(p.node.title || p.node.category, p.x, p.y + orbR + 14);
    }
  }

  // Category labels around the rim
  if (!isSearching) {
    const cats = new Map<string, { x: number; y: number; clr: { r: number; g: number; b: number } }>();
    for (const p of placed) {
      if (!cats.has(p.node.category)) {
        const angle = Math.atan2(p.y - cy, p.x - cx);
        const labelR = Math.min(w, h) * 0.45;
        cats.set(p.node.category, {
          x: cx + Math.cos(angle) * labelR,
          y: cy + Math.sin(angle) * labelR,
          clr: p.clr,
        });
      }
    }
    ctx.font = "bold 11px system-ui, sans-serif";
    ctx.textAlign = "center";
    for (const [cat, pos] of cats) {
      const label = CATEGORY_COLORS[cat]?.label || cat;
      ctx.fillStyle = `rgba(${pos.clr.r},${pos.clr.g},${pos.clr.b},0.5)`;
      ctx.fillText(label, pos.x, pos.y);
    }
  }
}

/* ────────────────────────────────────────────────────────
   MemoryStarMap Component
   ──────────────────────────────────────────────────────── */

interface MemoryStarMapProps {
  nodes: MemoryNodeData[];
  selectedNode: MemoryNodeData | null;
  searchResults: Set<string>;
  onSelectNode: (node: MemoryNodeData) => void;
}

export function MemoryStarMap({ nodes, selectedNode, searchResults, onSelectNode }: MemoryStarMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 900, h: 600 });
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const starsRef = useRef<Star[]>([]);
  const placedRef = useRef<PlacedNode[]>([]);
  const animRef = useRef<number>(0);

  // Resize observer
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) setDims({ w: width, h: height });
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Recompute layout + stars when nodes/dims change
  useEffect(() => {
    starsRef.current = createStars(dims.w, dims.h, 120);
    placedRef.current = layoutNodes(nodes, dims.w, dims.h);
  }, [nodes, dims]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let running = true;
    const loop = (timestamp: number) => {
      if (!running) return;
      const t = timestamp / 1000;
      canvas.width = dims.w;
      canvas.height = dims.h;
      renderFrame(
        ctx, dims.w, dims.h, t,
        starsRef.current, placedRef.current,
        selectedNode?.id || null, searchResults, hoveredId,
      );
      animRef.current = requestAnimationFrame(loop);
    };
    animRef.current = requestAnimationFrame(loop);
    return () => { running = false; cancelAnimationFrame(animRef.current); };
  }, [dims, selectedNode, searchResults, hoveredId]);

  // Hit detection
  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (dims.w / rect.width);
    const my = (e.clientY - rect.top) * (dims.h / rect.height);
    for (const p of placedRef.current) {
      const dx = mx - p.x, dy = my - p.y;
      if (dx * dx + dy * dy < (p.size + 6) * (p.size + 6)) {
        onSelectNode(p.node);
        return;
      }
    }
  }, [dims, onSelectNode]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (dims.w / rect.width);
    const my = (e.clientY - rect.top) * (dims.h / rect.height);
    let found: string | null = null;
    for (const p of placedRef.current) {
      const dx = mx - p.x, dy = my - p.y;
      if (dx * dx + dy * dy < (p.size + 6) * (p.size + 6)) {
        found = p.node.id;
        break;
      }
    }
    setHoveredId(found);
    canvas.style.cursor = found ? "pointer" : "default";
  }, [dims]);

  // Tooltip
  const hoveredNode = hoveredId ? placedRef.current.find(p => p.node.id === hoveredId) : null;

  return (
    <div ref={containerRef} className="w-full h-full relative">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        onClick={handleClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredId(null)}
      />

      {/* Tooltip */}
      <AnimatePresence>
        {hoveredNode && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute pointer-events-none z-20 px-3 py-2 rounded-lg backdrop-blur-md border border-white/10"
            style={{
              left: Math.min(hoveredNode.x, dims.w - 200),
              top: hoveredNode.y - 60,
              background: `rgba(${hoveredNode.clr.r},${hoveredNode.clr.g},${hoveredNode.clr.b},0.15)`,
            }}
          >
            <div className="text-xs font-bold text-white/90">{hoveredNode.node.title || hoveredNode.node.category}</div>
            <div className="text-[10px] text-white/50 mt-0.5">
              优先级 {hoveredNode.node.priority} · 活力 {Math.round((hoveredNode.node.vitality ?? 0.7) * 100)}%
            </div>
            {hoveredNode.node.disclosure && (
              <div className="text-[10px] text-white/40 mt-0.5 italic">{hoveredNode.node.disclosure}</div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-2.5">
        {Object.entries(CATEGORY_COLORS).map(([cat, clr]) => (
          <div key={cat} className="flex items-center gap-1.5 text-[10px] text-white/40">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: `rgb(${clr.r},${clr.g},${clr.b})`, opacity: 0.8 }}
            />
            {clr.label}
          </div>
        ))}
      </div>

      {/* Node count */}
      <div className="absolute top-3 right-3 text-[10px] text-white/30 font-mono">
        {nodes.length} memories
      </div>
    </div>
  );
}
