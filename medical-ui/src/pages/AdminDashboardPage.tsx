import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAdminStore, type ServiceStatus, type ErrorEntry } from '../stores/adminStore';
import type { EvalStats } from '../stores/evaluationStore';
import { ErrorToast } from '../components/common/ErrorToast';

// ─── Helpers ──────────────────────────────────────────────────────

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function serviceStatusConfig(status: ServiceStatus) {
  switch (status) {
    case 'healthy':
      return { label: '正常', dot: 'bg-green-400', text: 'text-green-400' };
    case 'degraded':
      return { label: '降级', dot: 'bg-yellow-400', text: 'text-yellow-400' };
    case 'down':
      return { label: '离线', dot: 'bg-red-400', text: 'text-red-400' };
    default:
      return { label: '未知', dot: 'bg-gray-400', text: 'text-gray-400' };
  }
}

// ─── Main Page ────────────────────────────────────────────────────

export function AdminDashboardPage() {
  const {
    health,
    evalStats,
    recentErrors,
    error,
    evolutionResult,
    evolutionLoading,
    fetchHealth,
    fetchEvalStats,
    fetchRecentErrors,
    triggerEvolution,
    clearEvolutionResult,
  } = useAdminStore();

  useEffect(() => {
    fetchHealth();
    fetchEvalStats();
    fetchRecentErrors();
  }, [fetchHealth, fetchEvalStats, fetchRecentErrors]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full overflow-auto p-4 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">系统管理</h1>
          <p className="text-xs text-gray-500 mt-0.5">运维监控与系统管理</p>
        </div>
        <button
          onClick={() => {
            fetchHealth();
            fetchEvalStats();
            fetchRecentErrors();
          }}
          className="px-3 py-1.5 text-xs rounded-btn bg-surface-800 border border-white/10 text-gray-300
                     hover:bg-surface-700 hover:border-white/20 transition-colors"
        >
          刷新全部
        </button>
      </div>

      {/* System Status Cards */}
      <section>
        <h2 className="text-sm font-medium text-gray-400 mb-3">系统状态</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <StatusCard
            title="API 服务"
            icon="🌐"
            status={health?.api || 'unknown'}
            detail={health?.version ? `v${health.version}` : undefined}
            subDetail={health?.uptime ? `运行: ${health.uptime}` : undefined}
          />
          <StatusCard
            title="Memory Palace"
            icon="🏛️"
            status={health?.memory_palace || 'unknown'}
          />
          <div className="rounded-lg bg-surface-800/50 border border-white/5 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-base">🤖</span>
              <span className="text-sm font-medium text-gray-300">LLM 模式</span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  health?.llm_mode === 'llm'
                    ? 'bg-green-500/20 text-green-400'
                    : health?.llm_mode === 'mock'
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-gray-500/20 text-gray-400'
                }`}
              >
                {health?.llm_mode || '未知'}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Evaluation Stats */}
      <section>
        <h2 className="text-sm font-medium text-gray-400 mb-3">评测统计概览</h2>
        {evalStats ? <EvalStatsPanel stats={evalStats} /> : (
          <div className="h-32 animate-pulse rounded-lg bg-white/5" />
        )}
      </section>

      {/* Recent Errors */}
      <section>
        <h2 className="text-sm font-medium text-gray-400 mb-3">
          最近错误/警告
          {recentErrors.length > 0 && (
            <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-red-500/20 text-red-400">
              {recentErrors.length}
            </span>
          )}
        </h2>
        {recentErrors.length === 0 ? (
          <div className="rounded-lg bg-surface-800/50 border border-white/5 p-6 text-center">
            <p className="text-gray-500 text-sm">暂无错误或警告 🎉</p>
          </div>
        ) : (
          <div className="space-y-2">
            {recentErrors.map((entry, i) => (
              <ErrorEntryCard key={`${entry.trace_id}-${i}`} entry={entry} />
            ))}
          </div>
        )}
      </section>

      {/* Quick Actions */}
      <section>
        <h2 className="text-sm font-medium text-gray-400 mb-3">快捷操作</h2>
        <div className="rounded-lg bg-surface-800/50 border border-white/5 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-200 font-medium">触发人类评价驱动优化</p>
              <p className="text-xs text-gray-500 mt-0.5">
                基于已收集的人工评价数据，优化 prompt 和记忆策略
              </p>
            </div>
            <button
              onClick={triggerEvolution}
              disabled={evolutionLoading}
              className="flex-shrink-0 px-4 py-2 text-sm rounded-btn font-medium transition-colors
                         bg-primary-600 hover:bg-primary-500 text-white
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {evolutionLoading ? (
                <span className="flex items-center gap-2">
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  执行中…
                </span>
              ) : (
                '🚀 触发优化'
              )}
            </button>
          </div>

          {/* Evolution result */}
          {evolutionResult && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className={`mt-3 p-3 rounded border text-sm ${
                evolutionResult.success
                  ? 'bg-green-500/10 border-green-500/30 text-green-400'
                  : 'bg-red-500/10 border-red-500/30 text-red-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <span>{evolutionResult.success ? '✅' : '❌'} {evolutionResult.message}</span>
                <button
                  onClick={clearEvolutionResult}
                  className="text-xs opacity-60 hover:opacity-100"
                >
                  关闭
                </button>
              </div>
            </motion.div>
          )}
        </div>
      </section>

      <ErrorToast message={error} onDismiss={() => useAdminStore.setState({ error: null })} />
    </motion.div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────

function StatusCard({
  title,
  icon,
  status,
  detail,
  subDetail,
}: {
  title: string;
  icon: string;
  status: ServiceStatus;
  detail?: string;
  subDetail?: string;
}) {
  const sc = serviceStatusConfig(status);

  return (
    <div className="rounded-lg bg-surface-800/50 border border-white/5 p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-base">{icon}</span>
        <span className="text-sm font-medium text-gray-300">{title}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${sc.dot} animate-pulse`} />
        <span className={`text-sm font-medium ${sc.text}`}>{sc.label}</span>
        {detail && <span className="text-xs text-gray-500 ml-1">{detail}</span>}
      </div>
      {subDetail && <p className="text-[10px] text-gray-600 mt-1">{subDetail}</p>}
    </div>
  );
}

function EvalStatsPanel({ stats }: { stats: EvalStats }) {
  const total = stats.total || 1; // avoid division by zero
  const segments = [
    { label: 'Good', count: stats.good, color: 'bg-green-500', textColor: 'text-green-400' },
    { label: 'Neutral', count: stats.neutral, color: 'bg-gray-400', textColor: 'text-gray-400' },
    { label: 'Bad', count: stats.bad, color: 'bg-red-500', textColor: 'text-red-400' },
    { label: 'Error', count: stats.error, color: 'bg-orange-500', textColor: 'text-orange-400' },
  ];

  return (
    <div className="rounded-lg bg-surface-800/50 border border-white/5 p-4">
      {/* Summary numbers */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <StatNumber label="总评测" value={stats.total} />
        <StatNumber label="好评率" value={`${(stats.good_rate * 100).toFixed(0)}%`} color="text-green-400" />
        <StatNumber label="待评测" value={stats.pending_count} color="text-yellow-400" />
        <StatNumber label="需关注" value={stats.attention_count} color="text-red-400" />
      </div>

      {/* Distribution bar */}
      <div className="mb-3">
        <div className="flex h-4 rounded-full overflow-hidden bg-surface-700">
          {segments.map((seg) =>
            seg.count > 0 ? (
              <div
                key={seg.label}
                className={`${seg.color} transition-all duration-300`}
                style={{ width: `${(seg.count / total) * 100}%` }}
                title={`${seg.label}: ${seg.count}`}
              />
            ) : null,
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {segments.map((seg) => (
          <div key={seg.label} className="flex items-center gap-1.5 text-xs text-gray-400">
            <span className={`w-2.5 h-2.5 rounded-sm ${seg.color}`} />
            <span className={seg.textColor}>{seg.count}</span>
            <span>{seg.label}</span>
            <span className="text-gray-600">({((seg.count / total) * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatNumber({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color?: string;
}) {
  return (
    <div className="text-center">
      <p className={`text-lg font-bold ${color || 'text-gray-100'}`}>{value}</p>
      <p className="text-[10px] text-gray-500">{label}</p>
    </div>
  );
}

function ErrorEntryCard({ entry }: { entry: ErrorEntry }) {
  const isError = entry.severity === 'error';

  return (
    <div
      className={`rounded-lg border p-3 ${
        isError
          ? 'bg-red-500/5 border-red-500/20'
          : 'bg-yellow-500/5 border-yellow-500/20'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0">
          <span className={`text-xs mt-0.5 ${isError ? 'text-red-400' : 'text-yellow-400'}`}>
            {isError ? '❌' : '⚠️'}
          </span>
          <div className="min-w-0">
            <p className="text-sm text-gray-200">{entry.message}</p>
            <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500">
              <span className="font-mono">{entry.trace_id}</span>
              {entry.patient_id && <span>· {entry.patient_id}</span>}
            </div>
          </div>
        </div>
        <span className="flex-shrink-0 text-[10px] text-gray-500">{formatTime(entry.timestamp)}</span>
      </div>
    </div>
  );
}
