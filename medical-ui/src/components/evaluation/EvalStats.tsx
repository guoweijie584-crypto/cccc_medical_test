import { motion } from 'framer-motion';
import type { EvalStats as EvalStatsType } from '../../stores/evaluationStore';

interface EvalStatsProps {
  stats: EvalStatsType | null;
  loading?: boolean;
}

const cards = [
  { key: 'total', label: '总计', color: 'text-gray-200', bg: 'bg-white/5' },
  { key: 'good', label: '好评', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { key: 'bad', label: '差评', color: 'text-red-400', bg: 'bg-red-500/10' },
  { key: 'neutral', label: '中立', color: 'text-gray-400', bg: 'bg-gray-500/10' },
  { key: 'error', label: '错误', color: 'text-amber-400', bg: 'bg-amber-500/10' },
  { key: 'good_rate', label: '好评率', color: 'text-cyan-400', bg: 'bg-cyan-500/10', isPercent: true },
  { key: 'pending_count', label: '待评价', color: 'text-purple-400', bg: 'bg-purple-500/10' },
  { key: 'attention_count', label: '需关注', color: 'text-orange-400', bg: 'bg-orange-500/10' },
] as const;

export function EvalStats({ stats, loading }: EvalStatsProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
      {cards.map((card, i) => {
        const value = stats ? (stats as unknown as Record<string, number>)[card.key] : 0;
        const display = card.key === 'good_rate'
          ? `${((value || 0) * 100).toFixed(0)}%`
          : String(value ?? 0);

        return (
          <motion.div
            key={card.key}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`glass-panel p-3 text-center ${loading ? 'animate-pulse' : ''}`}
          >
            <div className="text-xs text-gray-500 mb-1">{card.label}</div>
            <div className={`text-2xl font-bold ${card.color}`}>{display}</div>
          </motion.div>
        );
      })}
    </div>
  );
}
