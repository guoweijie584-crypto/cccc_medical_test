import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { medicalApiUrl } from "./api";
import type { MemoryNodeData } from "./MemoryPalaceView";

export type { MemoryNodeData };

/** Category color map — matching the star-map node colors. */
const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string; glow: string }> = {
  profile: { bg: "bg-amber-500/15", text: "text-amber-300", border: "border-amber-500/30", glow: "shadow-amber-500/20" },
  glucose: { bg: "bg-cyan-500/15", text: "text-cyan-300", border: "border-cyan-500/30", glow: "shadow-cyan-500/20" },
  medications: { bg: "bg-blue-500/15", text: "text-blue-300", border: "border-blue-500/30", glow: "shadow-blue-500/20" },
  diet: { bg: "bg-emerald-500/15", text: "text-emerald-300", border: "border-emerald-500/30", glow: "shadow-emerald-500/20" },
  alerts: { bg: "bg-red-500/15", text: "text-red-300", border: "border-red-500/30", glow: "shadow-red-500/20" },
  consultations: { bg: "bg-violet-500/15", text: "text-violet-300", border: "border-violet-500/30", glow: "shadow-violet-500/20" },
  exercise: { bg: "bg-lime-500/15", text: "text-lime-300", border: "border-lime-500/30", glow: "shadow-lime-500/20" },
};

const DEFAULT_COLOR = { bg: "bg-slate-500/15", text: "text-slate-300", border: "border-slate-500/30", glow: "shadow-slate-500/20" };

const PRIORITY_LABELS: Record<number, string> = {
  0: "SAFETY",
  1: "CORE",
  2: "KEY EVENT",
  3: "NORMAL",
  4: "AUXILIARY",
  5: "LOW",
};

interface MemoryDetailPanelProps {
  node: MemoryNodeData | null;
  onClose: () => void;
  onDelete?: (node: MemoryNodeData) => void;
  onUpdate?: (path: string, content: string) => void;
}

export function MemoryDetailPanel({ node, onClose, onDelete, onUpdate }: MemoryDetailPanelProps) {
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [saving, setSaving] = useState(false);

  if (!node) return null;

  const color = CATEGORY_COLORS[node.category] ?? DEFAULT_COLOR;
  const contentText = node.content || "";
  const priorityLabel = PRIORITY_LABELS[node.priority] ?? `P${node.priority}`;
  const disclosureText = node.disclosure ?? "";
  const createdAt = node.timestamp ?? "";
  const children = node.children ?? [];

  const handleStartEdit = () => {
    setEditContent(contentText);
    setEditing(true);
  };

  const handleSave = async () => {
    if (!onUpdate) return;
    setSaving(true);
    try {
      await fetch(medicalApiUrl(`/api/memory/${node.path}`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editContent }),
      });
      onUpdate(node.path, editContent);
      setEditing(false);
    } catch {
      /* swallow — UI stays in edit mode */
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete || !node) return;
    setDeleting(true);
    try {
      const resp = await fetch(medicalApiUrl(`/api/memory/${node.path}`), { method: "DELETE" });
      if (resp.ok) {
        onDelete(node);
        onClose();
      }
    } catch {
      /* swallow */
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        key="detail-panel"
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 40, opacity: 0 }}
        transition={{ type: "spring", damping: 22, stiffness: 260 }}
        className={`rounded-xl border ${color.border} ${color.bg} backdrop-blur-md shadow-lg ${color.glow} overflow-hidden`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
          <div className="flex items-center gap-3">
            <span className={`inline-block w-3 h-3 rounded-full ${color.text} ring-2 ring-current animate-pulse`} />
            <span className={`text-sm font-semibold uppercase tracking-wider ${color.text}`}>{node.category}</span>
            <span className="text-xs text-slate-400 font-mono">{node.path}</span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors text-lg leading-none px-1"
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        {/* Meta row */}
        <div className="grid grid-cols-3 gap-4 px-5 py-3 border-b border-white/5 text-xs">
          <div>
            <span className="text-slate-500 block">Priority</span>
            <span className={`font-medium ${node.priority <= 1 ? "text-amber-300" : "text-slate-300"}`}>
              {priorityLabel}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Created</span>
            <span className="text-slate-300">{createdAt ? new Date(createdAt).toLocaleString() : "\u2014"}</span>
          </div>
          <div>
            <span className="text-slate-500 block">Disclosure</span>
            <span className="text-slate-300">{disclosureText || "\u2014"}</span>
          </div>
        </div>

        {/* Content */}
        <div className="px-5 py-4">
          {editing ? (
            <textarea
              className="w-full min-h-[120px] rounded-lg bg-slate-800/60 border border-slate-600/40 text-sm text-slate-200 p-3 focus:outline-none focus:border-cyan-500/50 resize-y"
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
            />
          ) : (
            <pre className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed max-h-60 overflow-auto">
              {contentText || <span className="text-slate-500 italic">Empty</span>}
            </pre>
          )}
        </div>

        {/* Children summary */}
        {children.length > 0 && (
          <div className="px-5 pb-3">
            <span className="text-xs text-slate-500">{children.length} child node(s)</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 px-5 py-3 border-t border-white/5">
          {editing ? (
            <>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-1.5 text-sm rounded-lg bg-cyan-600/80 text-white hover:bg-cyan-500/80 transition-colors disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save"}
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-4 py-1.5 text-sm rounded-lg bg-slate-700/60 text-slate-300 hover:bg-slate-600/60 transition-colors"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleStartEdit}
                className="px-4 py-1.5 text-sm rounded-lg bg-slate-700/60 text-slate-300 hover:bg-slate-600/60 transition-colors"
              >
                Edit
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-1.5 text-sm rounded-lg bg-red-600/20 text-red-400 hover:bg-red-600/40 transition-colors disabled:opacity-50"
              >
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export default MemoryDetailPanel;
