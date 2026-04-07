import { useRef, useMemo } from "react";
import { motion } from "framer-motion";
import type { MemoryNodeData } from "./MemoryPalaceView";

/* ────────────────────────────────────────────────────────
   Category → color / glow mappings
   ──────────────────────────────────────────────────────── */

const CATEGORY_COLORS: Record<string, { bg: string; glow: string; ring: string }> = {
  profile:      { bg: "bg-amber-400",   glow: "shadow-amber-400/60",   ring: "ring-amber-400/40" },
  glucose:      { bg: "bg-cyan-400",    glow: "shadow-cyan-400/60",    ring: "ring-cyan-400/40" },
  medication:   { bg: "bg-blue-400",    glow: "shadow-blue-400/60",    ring: "ring-blue-400/40" },
  diet:         { bg: "bg-emerald-400", glow: "shadow-emerald-400/60", ring: "ring-emerald-400/40" },
  exercise:     { bg: "bg-lime-400",    glow: "shadow-lime-400/60",    ring: "ring-lime-400/40" },
  safety:       { bg: "bg-red-400",     glow: "shadow-red-400/60",     ring: "ring-red-400/40" },
  complication: { bg: "bg-orange-400",  glow: "shadow-orange-400/60",  ring: "ring-orange-400/40" },
  consultation: { bg: "bg-violet-400",  glow: "shadow-violet-400/60",  ring: "ring-violet-400/40" },
};

const DEFAULT_COLOR = { bg: "bg-indigo-400", glow: "shadow-indigo-400/60", ring: "ring-indigo-400/40" };

function getColor(category: string) {
  return CATEGORY_COLORS[category] || DEFAULT_COLOR;
}

/* ────────────────────────────────────────────────────────
   Layout: radial placement
   ──────────────────────────────────────────────────────── */

interface PlacedNode {
  node: MemoryNodeData;
  x: number;
  y: number;
  size: number;
}

function layoutNodes(nodes: MemoryNodeData[], width: number, height: number): PlacedNode[] {
  if (nodes.length === 0) return [];

  const cx = width / 2;
  const cy = height / 2;
  const placed: PlacedNode[] = [];

  // Group by category
  const grouped = new Map<string, MemoryNodeData[]>();
  for (const n of nodes) {
    const cat = n.category || "general";
    if (!grouped.has(cat)) grouped.set(cat, []);
    grouped.get(cat)!.push(n);
  }

  const categories = Array.from(grouped.keys());
  const angleStep = (2 * Math.PI) / Math.max(categories.length, 1);
  const baseRadius = Math.min(width, height) * 0.3;

  categories.forEach((cat, catIdx) => {
    const catAngle = angleStep * catIdx - Math.PI / 2;
    const catNodes = grouped.get(cat)!;
    const catCx = cx + Math.cos(catAngle) * baseRadius;
    const catCy = cy + Math.sin(catAngle) * baseRadius;

    catNodes.forEach((node, nodeIdx) => {
      const spread = Math.min(catNodes.length, 8);
      const nodeAngle = catAngle + ((nodeIdx - (spread - 1) / 2) * 0.3);
      const nodeRadius = baseRadius * 0.3 + nodeIdx * 18;
      const x = catCx + Math.cos(nodeAngle) * Math.min(nodeRadius, baseRadius * 0.5);
      const y = catCy + Math.sin(nodeAngle) * Math.min(nodeRadius, baseRadius * 0.5);

      // Size based on priority (0 = biggest)
      const size = Math.max(12, 32 - (node.priority || 3) * 4);

      placed.push({ node, x, y, size });
    });
  });

  return placed;
}

/* ────────────────────────────────────────────────────────
   MemoryStarMap
   ──────────────────────────────────────────────────────── */

interface MemoryStarMapProps {
  nodes: MemoryNodeData[];
  selectedNode: MemoryNodeData | null;
  searchResults: Set<string>;
  onSelectNode: (node: MemoryNodeData) => void;
}

export function MemoryStarMap({ nodes, selectedNode, searchResults, onSelectNode }: MemoryStarMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const width = 900;
  const height = 600;

  const placed = useMemo(() => layoutNodes(nodes, width, height), [nodes, width, height]);

  // Center point for connection lines
  const cx = width / 2;
  const cy = height / 2;

  const isSearching = searchResults.size > 0;

  return (
    <div ref={containerRef} className="w-full h-full flex items-center justify-center">
      <svg width={width} height={height} className="select-none" style={{ maxWidth: "100%", maxHeight: "100%" }}>
        {/* Connection lines from center to nodes */}
        {placed.map(({ node, x, y }) => (
          <motion.line
            key={`line-${node.id}`}
            x1={cx}
            y1={cy}
            x2={x}
            y2={y}
            stroke="url(#lineGradient)"
            strokeWidth={1}
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 0.15 }}
            transition={{ duration: 1.2, delay: 0.2 }}
          />
        ))}

        {/* Gradient definition for lines */}
        <defs>
          <linearGradient id="lineGradient">
            <stop offset="0%" stopColor="#818cf8" stopOpacity={0.4} />
            <stop offset="100%" stopColor="#818cf8" stopOpacity={0.05} />
          </linearGradient>
          {/* Glow filter */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glowStrong">
            <feGaussianBlur stdDeviation="6" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Center hub */}
        <motion.circle
          cx={cx}
          cy={cy}
          r={6}
          fill="#818cf8"
          filter="url(#glowStrong)"
          animate={{
            r: [5, 7, 5],
            opacity: [0.6, 0.9, 0.6],
          }}
          transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
        />

        {/* Memory nodes */}
        {placed.map(({ node, x, y, size }, i) => {
          const color = getColor(node.category);
          const isSelected = selectedNode?.id === node.id;
          const isHighlighted = isSearching && searchResults.has(node.id);
          const isDimmed = isSearching && !searchResults.has(node.id);
          const vitality = node.vitality ?? 0.7;
          const pulseDuration = 2 + (1 - vitality) * 3; // High vitality = faster pulse

          return (
            <motion.g
              key={node.id}
              initial={{ scale: 0, opacity: 0 }}
              animate={{
                scale: 1,
                opacity: isDimmed ? 0.15 : 1,
              }}
              transition={{ duration: 0.6, delay: i * 0.05 }}
              style={{ cursor: "pointer" }}
              onClick={() => onSelectNode(node)}
            >
              {/* Pulse ring */}
              <motion.circle
                cx={x}
                cy={y}
                r={size + 4}
                fill="none"
                stroke={isSelected ? "#f59e0b" : isHighlighted ? "#22d3ee" : "#818cf8"}
                strokeWidth={1.5}
                filter="url(#glow)"
                animate={{
                  r: [size + 2, size + 8, size + 2],
                  opacity: [0.3 * vitality, 0.6 * vitality, 0.3 * vitality],
                }}
                transition={{ repeat: Infinity, duration: pulseDuration, ease: "easeInOut" }}
              />

              {/* Core orb */}
              <motion.circle
                cx={x}
                cy={y}
                r={size / 2}
                className={`${isSelected ? "fill-amber-300" : ""}`}
                fill={isSelected ? "#fbbf24" : getCssFill(node.category)}
                filter="url(#glow)"
                animate={{
                  r: [size / 2 - 1, size / 2 + 1, size / 2 - 1],
                }}
                transition={{ repeat: Infinity, duration: pulseDuration, ease: "easeInOut" }}
              />

              {/* Label */}
              <text
                x={x}
                y={y + size / 2 + 14}
                textAnchor="middle"
                fill="white"
                fillOpacity={isDimmed ? 0.15 : 0.7}
                fontSize={10}
                fontFamily="monospace"
              >
                {node.title || node.category}
              </text>
            </motion.g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex flex-wrap gap-3">
        {Object.entries(CATEGORY_COLORS).map(([cat, colors]) => (
          <div key={cat} className="flex items-center gap-1.5 text-xs text-white/50">
            <span className={`w-2.5 h-2.5 rounded-full ${colors.bg} opacity-80`} />
            {cat}
          </div>
        ))}
      </div>
    </div>
  );
}

/* helper: category → CSS fill color */
function getCssFill(category: string): string {
  const map: Record<string, string> = {
    profile: "#fbbf24",
    glucose: "#22d3ee",
    medication: "#60a5fa",
    diet: "#34d399",
    exercise: "#a3e635",
    safety: "#f87171",
    complication: "#fb923c",
    consultation: "#a78bfa",
  };
  return map[category] || "#818cf8";
}
