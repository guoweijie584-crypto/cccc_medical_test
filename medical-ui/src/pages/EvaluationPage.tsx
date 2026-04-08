import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useEvaluationStore } from '../stores/evaluationStore';
import { usePatientStore } from '../stores/patientStore';
import { EvalStats } from '../components/evaluation/EvalStats';
import { EvalPending } from '../components/evaluation/EvalPending';
import { EvalHistory } from '../components/evaluation/EvalHistory';
import { EvolutionTrigger } from '../components/evaluation/EvolutionTrigger';
import { ErrorToast } from '../components/common/ErrorToast';

export function EvaluationPage() {
  const { stats, error, fetchStats, fetchPending } = useEvaluationStore();
  const selectedPatientId = usePatientStore((s) => s.selectedPatientId);

  // Refresh when patient changes
  useEffect(() => {
    fetchStats();
    fetchPending();
  }, [selectedPatientId, fetchStats, fetchPending]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full overflow-auto p-4 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">评价管理</h1>
          <p className="text-xs text-gray-500 mt-0.5">人工评价驱动系统自进化</p>
        </div>
        {stats && stats.pending_count > 0 && (
          <span className="badge bg-purple-500/20 text-purple-400 text-sm px-3 py-1">
            待评价: {stats.pending_count} 条
          </span>
        )}
      </div>

      {/* Stats */}
      <section>
        <h2 className="text-sm font-medium text-gray-400 mb-3">统计概览</h2>
        <EvalStats stats={stats} />
      </section>

      {/* Pending evaluations */}
      <section>
        <h2 className="text-sm font-medium text-gray-400 mb-3">待评价</h2>
        <EvalPending />
      </section>

      {/* History */}
      <section>
        <h2 className="text-sm font-medium text-gray-400 mb-3">历史评价</h2>
        <EvalHistory />
      </section>

      {/* Evolution trigger */}
      <section>
        <h2 className="text-sm font-medium text-gray-400 mb-3">自进化优化</h2>
        <EvolutionTrigger />
      </section>

      <ErrorToast message={error} onDismiss={() => useEvaluationStore.setState({ error: null })} />
    </motion.div>
  );
}
