import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useEvaluationStore } from '../../stores/evaluationStore';

export function EvolutionTrigger() {
  const { stats, evolutionReport, fetchEvolutionReport, triggerEvolution } = useEvaluationStore();
  const [running, setRunning] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    fetchEvolutionReport();
  }, [fetchEvolutionReport]);

  const badCount = stats ? stats.bad + stats.error : 0;

  const handleTrigger = async () => {
    setRunning(true);
    setSuccess(false);
    const ok = await triggerEvolution();
    setRunning(false);
    if (ok) setSuccess(true);
  };

  return (
    <div className="glass-panel p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-300">自进化优化</h3>
        <span className="text-xs text-gray-500">Line 3</span>
      </div>

      {/* BAD/ERROR count */}
      <div className="flex items-center gap-4">
        <div>
          <span className="text-xs text-gray-500">BAD/ERROR 评价</span>
          <div className="text-xl font-bold text-orange-400">{badCount}</div>
        </div>

        <motion.button
          onClick={handleTrigger}
          disabled={running || badCount === 0}
          whileTap={{ scale: 0.97 }}
          className={`btn-primary text-sm flex items-center gap-2 ${running ? 'animate-pulse' : ''}`}
        >
          {running ? (
            <>
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
              </svg>
              优化中...
            </>
          ) : (
            '🔄 触发自进化优化'
          )}
        </motion.button>
      </div>

      {/* Success feedback */}
      {success && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-btn px-3 py-2"
        >
          ✅ 优化完成！系统已自动改进。
        </motion.div>
      )}

      {/* Last run summary */}
      {evolutionReport && (
        <div className="text-xs text-gray-500 space-y-1 border-t border-white/5 pt-3">
          {evolutionReport.last_run && (
            <p>最近优化: {new Date(evolutionReport.last_run).toLocaleString()}</p>
          )}
          <p>
            → {evolutionReport.prompt_optimizations} 个提示词优化
            + {evolutionReport.memory_reinforcements} 个记忆强化
          </p>
          {evolutionReport.summary && (
            <p className="text-gray-600">{evolutionReport.summary}</p>
          )}
        </div>
      )}
    </div>
  );
}
