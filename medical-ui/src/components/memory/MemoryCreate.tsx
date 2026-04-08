import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const CATEGORIES = [
  { value: 'glucose', label: '血糖', icon: '🩸' },
  { value: 'medication', label: '用药', icon: '💊' },
  { value: 'diet', label: '饮食', icon: '🥗' },
  { value: 'exercise', label: '运动', icon: '🏃' },
  { value: 'safety', label: '安全', icon: '⚠️' },
  { value: 'complication', label: '并发症', icon: '🏥' },
  { value: 'consultation', label: '咨询', icon: '💬' },
];

interface MemoryCreateProps {
  patientId: string;
  open: boolean;
  onClose: () => void;
  onCreate: (data: {
    path: string;
    content: string;
    priority?: number;
    disclosure?: string;
  }) => Promise<boolean>;
}

export function MemoryCreate({ patientId, open, onClose, onCreate }: MemoryCreateProps) {
  const [category, setCategory] = useState('glucose');
  const [content, setContent] = useState('');
  const [priority, setPriority] = useState(3);
  const [disclosure, setDisclosure] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!content.trim()) return;
    setSubmitting(true);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '_');
    const path = `patients/${patientId}/${category}/${timestamp}`;
    const memContent = JSON.stringify({
      patient_id: patientId,
      category,
      content: content.trim(),
      timestamp: new Date().toISOString(),
    });
    const ok = await onCreate({ path, content: memContent, priority, disclosure: disclosure || undefined });
    setSubmitting(false);
    if (ok) {
      setContent('');
      setDisclosure('');
      setPriority(3);
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={(e) => {
            if (e.target === e.currentTarget) onClose();
          }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="glass-panel w-full max-w-md p-6 space-y-4"
          >
            <h3 className="text-lg font-semibold text-gray-200">新建记忆</h3>

            {/* Category */}
            <div>
              <label className="text-xs text-gray-500 mb-1 block">类别</label>
              <div className="flex flex-wrap gap-2">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat.value}
                    onClick={() => setCategory(cat.value)}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-btn text-xs transition-colors ${
                      category === cat.value
                        ? 'bg-primary-600 text-white'
                        : 'bg-white/5 text-gray-400 hover:bg-white/10'
                    }`}
                  >
                    <span>{cat.icon}</span>
                    <span>{cat.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Content */}
            <div>
              <label className="text-xs text-gray-500 mb-1 block">内容</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="输入记忆内容..."
                rows={3}
                className="w-full rounded-btn bg-surface-800 border border-white/10 px-3 py-2 text-sm
                           text-gray-200 placeholder-gray-500 resize-none
                           focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              />
            </div>

            {/* Priority */}
            <div>
              <label className="text-xs text-gray-500 mb-1 block">
                优先级: {priority} ({['最高', '高', '中高', '中', '中低', '低'][priority] || priority})
              </label>
              <input
                type="range"
                min={0}
                max={5}
                value={priority}
                onChange={(e) => setPriority(Number(e.target.value))}
                className="w-full accent-primary-500"
              />
            </div>

            {/* Disclosure */}
            <div>
              <label className="text-xs text-gray-500 mb-1 block">触发条件（可选）</label>
              <input
                type="text"
                value={disclosure}
                onChange={(e) => setDisclosure(e.target.value)}
                placeholder="例：当评估血糖控制情况时"
                className="w-full rounded-btn bg-surface-800 border border-white/10 px-3 py-2 text-sm
                           text-gray-200 placeholder-gray-500
                           focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={onClose} className="btn-ghost text-sm">
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={!content.trim() || submitting}
                className="btn-primary text-sm"
              >
                {submitting ? '创建中...' : '创建'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
