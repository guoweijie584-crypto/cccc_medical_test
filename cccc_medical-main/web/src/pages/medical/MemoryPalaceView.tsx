import { useState, useCallback, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { medicalApiUrl } from "./api";
import { MemoryStarMap } from "./MemoryStarMap";
import { MemoryDetailPanel } from "./MemoryDetailPanel";
import { MemorySearchBar } from "./MemorySearchBar";
import { MemoryCreateModal } from "./MemoryCreateModal";

/* ────────────────────────────────────────────────────────
   Types
   ──────────────────────────────────────────────────────── */

export interface MemoryNodeData {
  id: string;
  path: string;
  title: string;
  category: string;
  content: string;
  priority: number;
  disclosure?: string;
  vitality?: number;
  timestamp?: string;
  children?: MemoryNodeData[];
}

interface MemoryPalaceViewProps {
  isDark: boolean;
}

/* ────────────────────────────────────────────────────────
   Component
   ──────────────────────────────────────────────────────── */

export function MemoryPalaceView({ isDark }: MemoryPalaceViewProps) {
  const [patients, setPatients] = useState<{ id: string; name: string }[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [memories, setMemories] = useState<MemoryNodeData[]>([]);
  const [selectedNode, setSelectedNode] = useState<MemoryNodeData | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Set<string>>(new Set());
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load patient list
  useEffect(() => {
    fetch(medicalApiUrl("/api/patients"))
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data.patients) ? data.patients : [];
        setPatients(list.map((p: any) => ({ id: p.id, name: p.name })));
        if (list.length > 0 && !selectedPatientId) {
          setSelectedPatientId(list[0].id);
        }
      })
      .catch(() => setPatients([]));
  }, []);

  // Load memories for selected patient
  const loadMemories = useCallback(async () => {
    if (!selectedPatientId) return;
    setLoading(true);
    try {
      const res = await fetch(medicalApiUrl(`/api/memory/tree/${selectedPatientId}`));
      if (res.ok) {
        const data = await res.json();
        setMemories(Array.isArray(data.nodes) ? data.nodes : []);
      } else {
        // Fallback to flat memory list
        const res2 = await fetch(medicalApiUrl(`/api/patients/${selectedPatientId}/memories`));
        if (res2.ok) {
          const data2 = await res2.json();
          const flat = (data2.memories || []).map((m: any, i: number) => ({
            id: m.id || `mem_${i}`,
            path: m.id || `patients/${selectedPatientId}/${m.category}/${i}`,
            title: m.category || "memory",
            category: m.category || "general",
            content: m.content || "",
            priority: 3,
            timestamp: m.timestamp || "",
            children: [],
          }));
          setMemories(flat);
        }
      }
    } catch {
      setMemories([]);
    } finally {
      setLoading(false);
    }
  }, [selectedPatientId]);

  useEffect(() => {
    loadMemories();
  }, [loadMemories]);

  // Search
  const handleSearch = useCallback(
    async (query: string) => {
      setSearchQuery(query);
      if (!query.trim()) {
        setSearchResults(new Set());
        return;
      }
      try {
        const res = await fetch(
          medicalApiUrl(`/api/memory/search?q=${encodeURIComponent(query)}&patient_id=${selectedPatientId || ""}`)
        );
        if (res.ok) {
          const data = await res.json();
          const ids = new Set<string>((data.results || []).map((r: any) => r.id || r.path));
          setSearchResults(ids);
        }
      } catch {
        setSearchResults(new Set());
      }
    },
    [selectedPatientId]
  );

  // Create memory
  const handleCreate = useCallback(
    async (params: { title: string; content: string; category: string; priority: number; disclosure: string }) => {
      if (!selectedPatientId) return;
      try {
        await fetch(medicalApiUrl("/api/memory/create"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ patient_id: selectedPatientId, ...params }),
        });
        setShowCreateModal(false);
        loadMemories();
      } catch {
        // handle error
      }
    },
    [selectedPatientId, loadMemories]
  );

  // Delete memory
  const handleDelete = useCallback(
    async (node: MemoryNodeData) => {
      try {
        await fetch(medicalApiUrl(`/api/memory/${encodeURIComponent(node.path)}`), { method: "DELETE" });
        setSelectedNode(null);
        loadMemories();
      } catch {
        // handle error
      }
    },
    [loadMemories]
  );

  return (
    <div className="flex flex-col h-full relative overflow-hidden">
      {/* Cosmic background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-indigo-950 to-purple-950 z-0" />
      <StarDust />

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between px-5 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="text-xl">🏛️</span>
          <h2 className="text-lg font-bold text-white/90 tracking-wide">Memory Palace</h2>
          <span className="text-xs text-white/40 font-mono">记忆宫殿</span>
        </div>
        <div className="flex items-center gap-3">
          <MemorySearchBar value={searchQuery} onChange={handleSearch} />
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3 py-1.5 text-sm rounded-lg bg-indigo-600/80 hover:bg-indigo-500/80 text-white transition-colors"
          >
            + 新建记忆
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-1 min-h-0">
        {/* Patient sidebar */}
        <div className="w-48 border-r border-white/10 overflow-y-auto py-2">
          <div className="px-3 py-1 text-xs text-white/30 uppercase tracking-wider">患者</div>
          {patients.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                setSelectedPatientId(p.id);
                setSelectedNode(null);
              }}
              className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                selectedPatientId === p.id
                  ? "bg-indigo-600/30 text-indigo-300 border-l-2 border-indigo-400"
                  : "text-white/60 hover:bg-white/5 hover:text-white/80 border-l-2 border-transparent"
              }`}
            >
              <span className={`inline-block w-2 h-2 rounded-full mr-2 ${selectedPatientId === p.id ? "bg-indigo-400" : "bg-white/20"}`} />
              {p.name || p.id}
            </button>
          ))}
        </div>

        {/* Star map */}
        <div className="flex-1 relative">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                className="w-8 h-8 border-2 border-indigo-400/50 border-t-indigo-400 rounded-full"
              />
            </div>
          ) : (
            <MemoryStarMap
              nodes={memories}
              selectedNode={selectedNode}
              searchResults={searchResults}
              onSelectNode={setSelectedNode}
            />
          )}
        </div>

        {/* Detail panel */}
        <AnimatePresence>
          {selectedNode && (
            <MemoryDetailPanel
              node={selectedNode}
              onClose={() => setSelectedNode(null)}
              onDelete={handleDelete}
            />
          )}
        </AnimatePresence>
      </div>

      {/* Create modal */}
      <AnimatePresence>
        {showCreateModal && (
          <MemoryCreateModal
            onClose={() => setShowCreateModal(false)}
            onCreate={handleCreate}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

/* ────────────────────────────────────────────────────────
   Star Dust background particles
   ──────────────────────────────────────────────────────── */

function StarDust() {
  return (
    <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 60 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full bg-white"
          style={{
            width: Math.random() * 2 + 1,
            height: Math.random() * 2 + 1,
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            opacity: Math.random() * 0.4 + 0.1,
          }}
          animate={{
            opacity: [Math.random() * 0.2 + 0.1, Math.random() * 0.5 + 0.2, Math.random() * 0.2 + 0.1],
            scale: [1, 1.3, 1],
          }}
          transition={{
            repeat: Infinity,
            duration: Math.random() * 4 + 3,
            delay: Math.random() * 3,
          }}
        />
      ))}
    </div>
  );
}

export default MemoryPalaceView;
