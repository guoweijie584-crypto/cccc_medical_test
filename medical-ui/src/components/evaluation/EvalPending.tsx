import { useEffect } from 'react';
import { useEvaluationStore } from '../../stores/evaluationStore';
import { EvalCard } from './EvalCard';
import { CardSkeleton } from '../common/LoadingSkeleton';

export function EvalPending() {
  const { pending, loading, fetchPending, submitEvaluation } = useEvaluationStore();

  useEffect(() => {
    fetchPending();
  }, [fetchPending]);

  if (loading && pending.length === 0) {
    return (
      <div className="space-y-3">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (pending.length === 0) {
    return (
      <div className="glass-panel p-8 text-center">
        <div className="text-4xl mb-3">✅</div>
        <p className="text-gray-400 text-sm">暂无待评价记录</p>
        <p className="text-gray-600 text-xs mt-1">新的咨询对话完成后将自动创建待评价记录</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {pending.map((evaluation) => (
        <EvalCard
          key={evaluation.id}
          evaluation={evaluation}
          onSubmit={submitEvaluation}
        />
      ))}
    </div>
  );
}
