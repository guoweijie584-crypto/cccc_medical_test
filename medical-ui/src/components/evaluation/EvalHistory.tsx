import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useEvaluationStore } from '../../stores/evaluationStore';
import type { EvalLabel, CompletedEvaluation } from '../../stores/evaluationStore';

const FILTER_TABS: Array<{ value: EvalLabel | 'ALL'; label: string; cls: string }> = [
  { value: 'ALL', label: '全部', cls: 'text-gray-400' },
  { value: 'GOOD', label: '好', cls: 'text-emerald-400' },
  { value: 'BAD', label: '坏', cls: 'text-red-400' },
  { value: 'NEUTRAL', label: '中立', cls: 'text-gray-400' },
  { value: 'ERROR', label: '错误', cls: 'text-amber-400' },
];

const BADGE_MAP: Record<string, string> = {
  GOOD: 'badge-good',
  BAD: 'badge-bad',
  NEUTRAL: 'badge-neutral',
  ERROR: 'badge-error',
};

export function EvalHistory() {
  const { history, fetchHistory } = useEvaluationStore();
  const [filter, setFilter] = useState<EvalLabel | 'ALL'>('ALL');

  useEffect(() => {
    fetchHistory(filter === 'ALL' ? undefined : filter);
  }, [filter, fetchHistory]);

  const filtered = filter === 'ALL'
    ? history
    : history.filter((e) => e.label === filter);

  return (
    <div className="space-y-3">
      {/* Filter tabs */}
      <div className="flex gap-1 p-1 rounded-btn bg-white/5 w-fit">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={`px-3 py-1 text-xs rounded-btn transition-all ${
              filter === tab.value
                ? 'bg-white/10 text-gray-200'
                : `${tab.cls} hover:bg-white/5`
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* History list */}
      {filtered.length === 0 ? (
        <div className="glass-panel p-6 text-center">
          <p className="text-gray-500 text-sm">暂无{filter === 'ALL' ? '' : `「${FILTER_TABS.find(t => t.value === filter)?.label}」`}评价记录</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((evaluation, i) => (
            <HistoryItem key={evaluation.id || i} evaluation={evaluation} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function HistoryItem({ evaluation, index }: { evaluation: CompletedEvaluation; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.03 }}
      className="glass-panel-hover p-3 flex items-center gap-3"
    >
      <span className={BADGE_MAP[evaluation.label] || 'badge'}>
        {evaluation.label}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-300 truncate">"{evaluation.query}"</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-gray-600">患者 {evaluation.patient_id}</span>
          {evaluation.safety && (
            <span className={`text-xs ${
              evaluation.safety === 'dangerous' ? 'text-red-400' :
              evaluation.safety === 'risky' ? 'text-amber-400' : 'text-gray-500'
            }`}>
              {evaluation.safety}
            </span>
          )}
          {evaluation.personalized !== undefined && (
            <span className="text-xs text-gray-500">
              个性化: {evaluation.personalized ? '是' : '否'}
            </span>
          )}
          {evaluation.advice_direction && (
            <span className="text-xs text-gray-500">
              方向: {evaluation.advice_direction}
            </span>
          )}
        </div>
      </div>
      <span className="text-xs text-gray-600 whitespace-nowrap">
        {evaluation.evaluated_at ? new Date(evaluation.evaluated_at).toLocaleDateString() : ''}
      </span>
    </motion.div>
  );
}
