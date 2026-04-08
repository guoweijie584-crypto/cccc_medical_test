import { useRef, useEffect, useCallback, useState } from 'react';
import { MemoryNode } from '../../stores/memoryStore';

// ─── Category colors & labels ───────────────────────────────────────
const CATEGORY_COLORS: Record<string, { r: number; g: number; b: number }> = {
  profile: { r: 255, g: 215, b: 0 },
  glucose: { r: 0, g: 220, b: 220 },
  medication: { r: 80, g: 140, b: 255 },
  diet: { r: 80, g: 220, b: 120 },
  exercise: { r: 130, g: 200, b: 255 },
  safety: { r: 255, g: 80, b: 80 },
  complication: { r: 255, g: 160, b: 60 },
  consultation: { r: 170, g: 120, b: 255 },
  general: { r: 150, g: 150, b: 200 },
};

const CATEGORY_LABELS: Record<string, string> = {
  profile: '档案',
  glucose: '血糖',
  medication: '用药',
  diet: '饮食',
  exercise: '运动',
  safety: '安全',
  complication: '并发症',
  consultation: '咨询',
};

interface StarNode {
  memory: MemoryNode;
  x: number;
  y: number;
  radius: number;
  color: { r: number; g: number; b: number };
  angle: number;
  distance: number;
  pulsePhase: number;
  pulseSpeed: number;
}

interface StarDust {
  x: number;
  y: number;
  size: number;
  alpha: number;
  speed: number;
  twinklePhase: number;
}

interface EnergyParticle {
  nodeIndex: number;
  progress: number;
  speed: number;
  size: number;
}

interface MemoryStarMapProps {
  memories: MemoryNode[];
  searchResults?: MemoryNode[];
  onSelectMemory: (memory: MemoryNode) => void;
  selectedMemory?: MemoryNode | null;
}

export function MemoryStarMap({
  memories,
  searchResults,
  onSelectMemory,
  selectedMemory,
}: MemoryStarMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const nodesRef = useRef<StarNode[]>([]);
  const dustRef = useRef<StarDust[]>([]);
  const particlesRef = useRef<EnergyParticle[]>([]);
  const [hovered, setHovered] = useState<StarNode | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: StarNode } | null>(null);

  const searchPaths = searchResults?.map((r) => r.path) || [];
  const isSearchActive = searchPaths.length > 0;

  // ─── Initialize nodes from memories ─────────────────────────────
  useEffect(() => {
    const nodes: StarNode[] = memories.map((mem, i) => {
      const cat = mem.category || 'general';
      const color = CATEGORY_COLORS[cat] || CATEGORY_COLORS.general;
      const priority = mem.priority ?? 3;
      const vitality = mem.vitality ?? 0.5;
      const angle = (i / Math.max(memories.length, 1)) * Math.PI * 2 + Math.random() * 0.3;
      const distance = 120 + Math.random() * 160 + priority * 15;
      const radius = Math.max(8, 22 - priority * 3);

      return {
        memory: mem,
        x: 0,
        y: 0,
        radius,
        color,
        angle,
        distance,
        pulsePhase: Math.random() * Math.PI * 2,
        pulseSpeed: 0.5 + vitality * 2,
      };
    });
    nodesRef.current = nodes;
  }, [memories]);

  // ─── Initialize star dust ───────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dust: StarDust[] = [];
    for (let i = 0; i < 150; i++) {
      dust.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        size: Math.random() * 1.5 + 0.3,
        alpha: Math.random() * 0.6 + 0.1,
        speed: Math.random() * 0.15 + 0.02,
        twinklePhase: Math.random() * Math.PI * 2,
      });
    }
    dustRef.current = dust;

    // Energy particles
    const particles: EnergyParticle[] = [];
    for (let i = 0; i < Math.min(memories.length * 2, 40); i++) {
      particles.push({
        nodeIndex: Math.floor(Math.random() * Math.max(memories.length, 1)),
        progress: Math.random(),
        speed: 0.002 + Math.random() * 0.004,
        size: 1 + Math.random() * 2,
      });
    }
    particlesRef.current = particles;
  }, [memories.length]);

  // ─── Resize ─────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        canvas.width = rect.width * window.devicePixelRatio;
        canvas.height = rect.height * window.devicePixelRatio;
        canvas.style.width = `${rect.width}px`;
        canvas.style.height = `${rect.height}px`;
      }
    };
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  // ─── Animation loop ─────────────────────────────────────────────
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    const dpr = window.devicePixelRatio;
    const cx = w / 2;
    const cy = h / 2;
    const t = Date.now() / 1000;

    ctx.save();
    ctx.scale(dpr, dpr);
    const sw = w / dpr;
    const sh = h / dpr;
    const scx = sw / 2;
    const scy = sh / 2;

    // ─── Background ───────────────────────────────────────────────
    const bgGrad = ctx.createRadialGradient(scx, scy, 0, scx, scy, Math.max(sw, sh) * 0.7);
    bgGrad.addColorStop(0, '#0c0e1a');
    bgGrad.addColorStop(0.4, '#080a14');
    bgGrad.addColorStop(1, '#020308');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, sw, sh);

    // Nebula glow
    const nebula = ctx.createRadialGradient(scx, scy, 0, scx, scy, 250);
    nebula.addColorStop(0, 'rgba(99, 102, 241, 0.08)');
    nebula.addColorStop(0.5, 'rgba(6, 182, 212, 0.03)');
    nebula.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = nebula;
    ctx.fillRect(0, 0, sw, sh);

    // ─── Star dust ────────────────────────────────────────────────
    for (const d of dustRef.current) {
      d.twinklePhase += d.speed * 0.05;
      const alpha = d.alpha * (0.5 + 0.5 * Math.sin(d.twinklePhase));
      ctx.beginPath();
      ctx.arc(d.x / dpr, d.y / dpr, d.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200, 210, 255, ${alpha})`;
      ctx.fill();
    }

    // ─── Center hub ───────────────────────────────────────────────
    const hubPulse = 1 + 0.08 * Math.sin(t * 1.5);
    const hubR = 24 * hubPulse;

    // Hub outer glow
    const hubGlow = ctx.createRadialGradient(scx, scy, hubR * 0.5, scx, scy, hubR * 4);
    hubGlow.addColorStop(0, 'rgba(99, 102, 241, 0.15)');
    hubGlow.addColorStop(0.5, 'rgba(99, 102, 241, 0.05)');
    hubGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = hubGlow;
    ctx.beginPath();
    ctx.arc(scx, scy, hubR * 4, 0, Math.PI * 2);
    ctx.fill();

    // Hub sphere
    const hubSphere = ctx.createRadialGradient(
      scx - hubR * 0.3, scy - hubR * 0.3, hubR * 0.1,
      scx, scy, hubR,
    );
    hubSphere.addColorStop(0, 'rgba(180, 160, 255, 0.9)');
    hubSphere.addColorStop(0.6, 'rgba(99, 102, 241, 0.7)');
    hubSphere.addColorStop(1, 'rgba(60, 50, 160, 0.3)');
    ctx.fillStyle = hubSphere;
    ctx.beginPath();
    ctx.arc(scx, scy, hubR, 0, Math.PI * 2);
    ctx.fill();

    // ─── Connection lines + energy particles ──────────────────────
    const nodes = nodesRef.current;
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      node.x = scx + Math.cos(node.angle + t * 0.03) * node.distance;
      node.y = scy + Math.sin(node.angle + t * 0.03) * node.distance;

      const isSearchHit = isSearchActive && searchPaths.includes(node.memory.path);
      const dimFactor = isSearchActive && !isSearchHit ? 0.15 : 1;

      // Connection line
      ctx.beginPath();
      ctx.moveTo(scx, scy);
      ctx.lineTo(node.x, node.y);
      ctx.strokeStyle = `rgba(${node.color.r}, ${node.color.g}, ${node.color.b}, ${0.12 * dimFactor})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Energy particles on lines
    for (const p of particlesRef.current) {
      if (p.nodeIndex >= nodes.length) continue;
      const node = nodes[p.nodeIndex];
      p.progress += p.speed;
      if (p.progress > 1) {
        p.progress = 0;
        p.nodeIndex = Math.floor(Math.random() * nodes.length);
      }

      const px = scx + (node.x - scx) * p.progress;
      const py = scy + (node.y - scy) * p.progress;
      const c = node.color;
      const pAlpha = Math.sin(p.progress * Math.PI) * 0.8;

      ctx.beginPath();
      ctx.arc(px, py, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${c.r}, ${c.g}, ${c.b}, ${pAlpha})`;
      ctx.fill();
    }

    // ─── Memory nodes ─────────────────────────────────────────────
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const isSearchHit = isSearchActive && searchPaths.includes(node.memory.path);
      const dimFactor = isSearchActive && !isSearchHit ? 0.15 : 1;
      const isSelected = selectedMemory?.path === node.memory.path;
      const isHov = hovered?.memory.path === node.memory.path;

      const pulse = 1 + 0.12 * Math.sin(t * node.pulseSpeed + node.pulsePhase);
      const r = node.radius * pulse * (isHov ? 1.2 : 1) * (isSelected ? 1.3 : 1);
      const { color } = node;

      // Node outer glow
      const glowR = r * 3;
      const glow = ctx.createRadialGradient(node.x, node.y, r * 0.3, node.x, node.y, glowR);
      glow.addColorStop(0, `rgba(${color.r}, ${color.g}, ${color.b}, ${0.2 * dimFactor})`);
      glow.addColorStop(1, `rgba(${color.r}, ${color.g}, ${color.b}, 0)`);
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(node.x, node.y, glowR, 0, Math.PI * 2);
      ctx.fill();

      // 3D sphere
      const sphere = ctx.createRadialGradient(
        node.x - r * 0.3, node.y - r * 0.3, r * 0.1,
        node.x, node.y, r,
      );
      sphere.addColorStop(0, `rgba(${Math.min(255, color.r + 80)}, ${Math.min(255, color.g + 80)}, ${Math.min(255, color.b + 80)}, ${0.95 * dimFactor})`);
      sphere.addColorStop(0.6, `rgba(${color.r}, ${color.g}, ${color.b}, ${0.8 * dimFactor})`);
      sphere.addColorStop(1, `rgba(${Math.floor(color.r * 0.4)}, ${Math.floor(color.g * 0.4)}, ${Math.floor(color.b * 0.4)}, ${0.5 * dimFactor})`);
      ctx.fillStyle = sphere;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fill();

      // Search hit flash
      if (isSearchHit) {
        const flashAlpha = 0.3 + 0.3 * Math.sin(t * 4);
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 4, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 255, 255, ${flashAlpha})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Selection ring
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 5, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, 0.8)`;
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    // ─── Category labels ring ─────────────────────────────────────
    const categories = Object.entries(CATEGORY_LABELS);
    const labelRadius = Math.min(sw, sh) * 0.42;
    ctx.font = '11px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (let i = 0; i < categories.length; i++) {
      const [cat, label] = categories[i];
      const a = (i / categories.length) * Math.PI * 2 - Math.PI / 2;
      const lx = scx + Math.cos(a) * labelRadius;
      const ly = scy + Math.sin(a) * labelRadius;
      const c = CATEGORY_COLORS[cat] || CATEGORY_COLORS.general;
      ctx.fillStyle = `rgba(${c.r}, ${c.g}, ${c.b}, 0.6)`;
      ctx.fillText(label, lx, ly);
    }

    ctx.restore();
    animRef.current = requestAnimationFrame(render);
  }, [memories, searchPaths, isSearchActive, selectedMemory, hovered]);

  useEffect(() => {
    animRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animRef.current);
  }, [render]);

  // ─── Mouse interaction ──────────────────────────────────────────
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      let found: StarNode | null = null;
      for (const node of nodesRef.current) {
        const dx = mx - node.x;
        const dy = my - node.y;
        if (Math.sqrt(dx * dx + dy * dy) < node.radius + 6) {
          found = node;
          break;
        }
      }

      setHovered(found);
      if (found) {
        setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top, node: found });
        canvas.style.cursor = 'pointer';
      } else {
        setTooltip(null);
        canvas.style.cursor = 'default';
      }
    },
    [],
  );

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      for (const node of nodesRef.current) {
        const dx = mx - node.x;
        const dy = my - node.y;
        if (Math.sqrt(dx * dx + dy * dy) < node.radius + 6) {
          onSelectMemory(node.memory);
          return;
        }
      }
    },
    [onSelectMemory],
  );

  return (
    <div className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        onMouseMove={handleMouseMove}
        onClick={handleClick}
        onMouseLeave={() => {
          setHovered(null);
          setTooltip(null);
        }}
      />

      {/* Tooltip overlay */}
      {tooltip && (
        <div
          className="absolute pointer-events-none z-10"
          style={{
            left: tooltip.x + 16,
            top: tooltip.y - 10,
          }}
        >
          <div className="glass-panel px-3 py-2 text-xs space-y-1 min-w-[160px] border border-white/10">
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  backgroundColor: `rgb(${tooltip.node.color.r}, ${tooltip.node.color.g}, ${tooltip.node.color.b})`,
                }}
              />
              <span className="text-gray-200 font-medium">
                {CATEGORY_LABELS[tooltip.node.memory.category] || tooltip.node.memory.category}
              </span>
            </div>
            <div className="text-gray-400 truncate max-w-[200px]">
              {parseMemoryContent(tooltip.node.memory.content)}
            </div>
            <div className="flex gap-3 text-gray-500">
              <span>优先级: {tooltip.node.memory.priority}</span>
              <span>活力: {Math.round((tooltip.node.memory.vitality ?? 0.5) * 100)}%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function parseMemoryContent(content: string): string {
  try {
    const obj = JSON.parse(content);
    return obj.content || obj.query || content.slice(0, 60);
  } catch {
    return content.slice(0, 60);
  }
}
