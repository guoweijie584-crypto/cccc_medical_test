import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { medicalApiUrl } from "./api";

const CATEGORIES = [
  { value: "glucose", label: "Blood Glucose", color: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30" },
  { value: "medications", label: "Medication", color: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  { value: "diet", label: "Diet", color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
  { value: "exercise", label: "Exercise", color: "bg-lime-500/20 text-lime-300 border-lime-500/30" },
  { value: "alerts", label: "Safety Alert", color: "bg-red-500/20 text-red-300 border-red-500/30" },
  { value: "consultations", label: "Consultation", color: "bg-violet-500/20 text-violet-300 border-violet-500/30" },
  { value: "general", label: "General", color: "bg-slate-500/20 text-slate-300 border-slate-500/30" },
];

const PRIORITY_OPTIONS = [
  { value: 0, label: "SAFETY (0)" },
  { value: 1, label: "CORE (1)" },
  { value: 2, label: "KEY EVENT (2)" },
  { value: 3, label: "NORMAL (3)" },
  { value: 4, label: "AUXILIARY (4)" },
  { value: 5, label: "LOW (5)" },
];

interface MemoryCreateModalProps {
  patientId?: string;
  open?: boolean;
  onClose: () => void;
  onCreated?: (node: Record<string, unknown>) => void;
  /** Alternate callback used by MemoryPalaceView */
  onCreate?: (params: { title: string; content: string; category: string; priority: number; disclosure: string }) => void;
}

export function MemoryCreateModal({ patientId, open: openProp, onClose, onCreated, onCreate }: MemoryCreateModalProps) {
  // If `open` is not provided, the component is always visible (controlled by AnimatePresence in parent).
  const isOpen = openProp !== undefined ? openProp : true;
  const [category, setCategory] = useState("general");
  const [content, setContent] = useState("");
  const [priority, setPriority] = useState(3);
  const [disclosure, setDisclosure] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!content.trim()) {
      setError("Content is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      // If parent provides onCreate, delegate to it (MemoryPalaceView pattern)
      if (onCreate) {
        await onCreate({ title: category, content: content.trim(), category, priority, disclosure: disclosure.trim() });
        setContent("");
        setDisclosure("");
        setCategory("general");
        setPriority(3);
        onClose();
        return;
      }
      const resp = await fetch(medicalApiUrl("/api/memory/create"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: patientId,
          category,
          content: content.trim(),
          priority,
          disclosure: disclosure.trim(),
        }),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error((body as Record<string, string>).detail || "Failed to create memory");
      }
      const data = await resp.json();
      onCreated?.(data);
      // Reset form
      setContent("");
      setDisclosure("");
      setCategory("general");
      setPriority(3);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            key="modal"
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 20 }}
            transition={{ type: "spring", damping: 24, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
          >
            <div
              className="pointer-events-auto w-full max-w-lg rounded-2xl border border-slate-600/40 bg-slate-900/95 backdrop-blur-xl shadow-2xl shadow-cyan-500/5 overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50">
                <h3 className="text-lg font-semibold text-slate-100">Create Memory</h3>
                <button
                  onClick={onClose}
                  className="text-slate-400 hover:text-white transition-colors text-xl leading-none"
                  aria-label="Close"
                >
                  &times;
                </button>
              </div>

              {/* Body */}
              <div className="px-6 py-5 space-y-5">
                {/* Patient */}
                <div className="text-xs text-slate-500">
                  Patient: <span className="text-slate-300 font-mono">{patientId}</span>
                </div>

                {/* Category */}
                <div>
                  <label className="block text-xs text-slate-400 mb-2">Category</label>
                  <div className="flex flex-wrap gap-2">
                    {CATEGORIES.map((c) => (
                      <button
                        key={c.value}
                        onClick={() => setCategory(c.value)}
                        className={`px-3 py-1 text-xs rounded-full border transition-all ${
                          category === c.value
                            ? `${c.color} ring-1 ring-current`
                            : "bg-slate-800/40 text-slate-500 border-slate-700/40 hover:border-slate-600/60"
                        }`}
                      >
                        {c.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Content */}
                <div>
                  <label className="block text-xs text-slate-400 mb-2">Content</label>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Memory content..."
                    rows={4}
                    className="w-full rounded-lg bg-slate-800/60 border border-slate-600/40 text-sm text-slate-200 p-3 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 resize-y transition-colors"
                  />
                </div>

                {/* Priority */}
                <div>
                  <label className="block text-xs text-slate-400 mb-2">Priority</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(Number(e.target.value))}
                    className="w-full rounded-lg bg-slate-800/60 border border-slate-600/40 text-sm text-slate-200 px-3 py-2 focus:outline-none focus:border-cyan-500/50 transition-colors"
                  >
                    {PRIORITY_OPTIONS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Disclosure */}
                <div>
                  <label className="block text-xs text-slate-400 mb-2">Disclosure Condition (optional)</label>
                  <input
                    type="text"
                    value={disclosure}
                    onChange={(e) => setDisclosure(e.target.value)}
                    placeholder="e.g. When discussing medication adjustments"
                    className="w-full rounded-lg bg-slate-800/60 border border-slate-600/40 text-sm text-slate-200 px-3 py-2 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
                  />
                </div>

                {/* Error */}
                {error && (
                  <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</div>
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-700/50">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm rounded-lg bg-slate-700/60 text-slate-300 hover:bg-slate-600/60 transition-colors"
                >
                  Cancel
                </button>
                <motion.button
                  onClick={handleSubmit}
                  disabled={submitting || !content.trim()}
                  whileTap={{ scale: 0.97 }}
                  className="px-5 py-2 text-sm rounded-lg bg-cyan-600/80 text-white hover:bg-cyan-500/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/10"
                >
                  {submitting ? (
                    <span className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                        <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                      </svg>
                      Creating...
                    </span>
                  ) : (
                    "Create Memory"
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export default MemoryCreateModal;
