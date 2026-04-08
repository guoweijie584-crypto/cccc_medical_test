import { motion, AnimatePresence } from 'framer-motion';
import { MemoryNode } from '../../stores/memoryStore';

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

const PRIORITY_LABELS = ['最高', '高', '中高', '中', '中低', '低'];

interface MemoryDetailProps {
  memory: MemoryNode | null;
  onClose: () => void;
  onEdit: (memory: MemoryNode) => void;
  onDelete: (path: string) => void;
}

export function MemoryDetail({ memory, onClose, onEdit, onDelete }: MemoryDetailProps) {
  if (!memory) return null;

  const parsedContent = parseContent(memory.content);
  const categoryLabel = CATEGORY_LABELS[memory.category] || memory.category;
  const priorityLabel = PRIORITY_LABELS[memory.priority] || `${memory.priority}`;
  const vitality = Math.round((memory.vitality ?? 0.5) * 100);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 20 }}
        className="glass-panel p-4 space-y-4"
      >
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-200">记忆详情</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-sm">
            ✕
          </button>
        </div>

        {/* Category & Stats */}
        <div className="flex flex-wrap gap-2">
          <span className="badge bg-primary-500/20 text-primary-300">{categoryLabel}</span>
          <span className="badge bg-accent-500/20 text-accent-300">优先级: {priorityLabel}</span>
          <span className="badge bg-white/10 text-gray-300">活力: {vitality}%</span>
        </div>

        {/* Vitality bar */}
        <div>
          <div className="text-xs text-gray-500 mb-1">活力值</div>
          <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${vitality}%` }}
              transition={{ duration: 0.8 }}
              className="h-full rounded-full bg-gradient-to-r from-primary-600 to-accent-500"
            />
          </div>
        </div>

        {/* Content */}
        <div>
          <div className="text-xs text-gray-500 mb-1">内容</div>
          <div className="text-sm text-gray-300 bg-white/5 rounded-lg p-3 leading-relaxed">
            {parsedContent.text || memory.content}
          </div>
        </div>

        {/* Disclosure */}
        {memory.disclosure && (
          <div>
            <div className="text-xs text-gray-500 mb-1">触发条件</div>
            <div className="text-sm text-accent-300 bg-accent-500/10 rounded-lg p-2">
              {memory.disclosure}
            </div>
          </div>
        )}

        {/* Path */}
        <div>
          <div className="text-xs text-gray-500 mb-1">路径</div>
          <div className="text-xs text-gray-500 font-mono bg-white/5 rounded p-2 break-all">
            {memory.path}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2 border-t border-white/5">
          <button
            onClick={() => onEdit(memory)}
            className="btn-ghost text-xs flex-1"
          >
            编辑
          </button>
          <button
            onClick={() => {
              if (confirm('确定删除这条记忆？')) {
                onDelete(memory.path);
              }
            }}
            className="btn-ghost text-xs flex-1 text-red-400 hover:text-red-300 hover:bg-red-500/10"
          >
            删除
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

function parseContent(content: string): { text: string; [key: string]: unknown } {
  try {
    const obj = JSON.parse(content);
    return { text: obj.content || obj.query || JSON.stringify(obj, null, 2), ...obj };
  } catch {
    return { text: content };
  }
}
