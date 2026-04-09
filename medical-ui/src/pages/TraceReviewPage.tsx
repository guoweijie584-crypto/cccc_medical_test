import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  useTraceStore,
  type TraceItem,
  type TraceDetail,
  type ExpertOutput,
  type SafetyVerdict,
  type TraceStatus,
  type WritebackStatus,
} from '../stores/traceStore';
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

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function statusConfig(status: TraceStatus) {
  switch (status) {
    case 'success':
      return { label: '成功', color: 'bg-green-500/20 text-green-400', dot: 'bg-green-400' };
    case 'partial_failure':
      return { label: '部分失败', color: 'bg-yellow-500/20 text-yellow-400', dot: 'bg-yellow-400' };
    case 'failure':
      return { label: '失败', color: 'bg-red-500/20 text-red-400', dot: 'bg-red-400' };
  }
}

function safetyColor(verdict: SafetyVerdict) {
  switch (verdict) {
    case 'safe':
      return { bg: 'bg-green-500/10 border-green-500/30', text: 'text-green-400', label: '安全' };
    case 'caution':
      return { bg: 'bg-yellow-500/10 border-yellow-500/30', text: 'text-yellow-400', label: '注意' };
    case 'warning':
      return { bg: 'bg-orange-500/10 border-orange-500/30', text: 'text-orange-400', label: '警告' };
    case 'danger':
      return { bg: 'bg-red-500/10 border-red-500/30', text: 'text-red-400', label: '危险' };
  }
}

function writebackStatusConfig(status: WritebackStatus) {
  switch (status) {
    case 'approved':
      return { label: '已批准', color: 'text-green-400 bg-green-500/20' };
    case 'pending':
      return { label: '待审批', color: 'text-yellow-400 bg-yellow-500/20' };
    case 'rejected':
      return { label: '已拒绝', color: 'text-red-400 bg-red-500/20' };
  }
}

const EXPERT_ICONS: Record<string, string> = {
  doctor: '🩺',
  pharmacist: '💊',
  nutritionist: '🥗',
  primary: '👨‍⚕️',
};

// ─── Main Page ────────────────────────────────────────────────────

export function TraceReviewPage() {
  const {
    traces,
    selectedTrace,
    loading,
    detailLoading,
    error,
    fetchRecentTraces,
    fetchTraceDetail,
    clearSelection,
  } = useTraceStore();

  useEffect(() => {
    fetchRecentTraces();
  }, [fetchRecentTraces]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full overflow-auto p-4 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Trace 审阅</h1>
          <p className="text-xs text-gray-500 mt-0.5">查看咨询流程的完整追踪记录</p>
        </div>
        <div className="flex items-center gap-2">
          {traces.length > 0 && (
            <span className="text-xs text-gray-500">
              共 {traces.length} 条记录
            </span>
          )}
          <button
            onClick={() => fetchRecentTraces()}
            disabled={loading}
            className="px-3 py-1.5 text-xs rounded-btn bg-surface-800 border border-white/10 text-gray-300
                       hover:bg-surface-700 hover:border-white/20 transition-colors disabled:opacity-50"
          >
            {loading ? '刷新中…' : '刷新'}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
        {/* Left: Trace List */}
        <div className="lg:col-span-1 space-y-2">
          <h2 className="text-sm font-medium text-gray-400 mb-3">最近咨询</h2>
          {loading && traces.length === 0 ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 animate-pulse rounded-lg bg-white/5" />
              ))}
            </div>
          ) : traces.length === 0 ? (
            <div className="rounded-lg bg-surface-800/50 border border-white/5 p-8 text-center">
              <p className="text-gray-500 text-sm">暂无咨询记录</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[calc(100vh-200px)] overflow-auto pr-1">
              {traces.map((trace) => (
                <TraceListItem
                  key={trace.trace_id}
                  trace={trace}
                  isSelected={selectedTrace?.trace_id === trace.trace_id}
                  onClick={() => fetchTraceDetail(trace.trace_id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right: Trace Detail */}
        <div className="lg:col-span-2">
          <h2 className="text-sm font-medium text-gray-400 mb-3">
            {selectedTrace ? '详情' : '选择一条记录查看详情'}
          </h2>
          <AnimatePresence mode="wait">
            {detailLoading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-3"
              >
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-24 animate-pulse rounded-lg bg-white/5" />
                ))}
              </motion.div>
            ) : selectedTrace ? (
              <motion.div
                key={selectedTrace.trace_id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="space-y-4 max-h-[calc(100vh-200px)] overflow-auto pr-1"
              >
                <TraceDetailView trace={selectedTrace} onClose={clearSelection} />
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-lg bg-surface-800/50 border border-white/5 p-12 text-center"
              >
                <div className="text-3xl mb-3">📋</div>
                <p className="text-gray-500 text-sm">点击左侧列表中的记录查看完整 Trace</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <ErrorToast message={error} onDismiss={() => useTraceStore.setState({ error: null })} />
    </motion.div>
  );
}

// ─── List Item ────────────────────────────────────────────────────

function TraceListItem({
  trace,
  isSelected,
  onClick,
}: {
  trace: TraceItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  const sc = statusConfig(trace.status);

  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-lg p-3 border transition-all duration-150 ${
        isSelected
          ? 'bg-primary-600/10 border-primary-500/30 ring-1 ring-primary-500/20'
          : 'bg-surface-800/50 border-white/5 hover:bg-surface-800 hover:border-white/10'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className="text-xs font-mono text-gray-500 truncate">{trace.trace_id}</span>
        <span className={`flex-shrink-0 inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${sc.color}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
          {sc.label}
        </span>
      </div>
      <p className="text-sm text-gray-200 line-clamp-2 mb-1.5">{trace.query}</p>
      <div className="flex items-center gap-3 text-[10px] text-gray-500">
        <span>{formatTime(trace.created_at)}</span>
        {trace.duration_ms && <span>{formatDuration(trace.duration_ms)}</span>}
        {trace.expert_count && <span>{trace.expert_count} 位专家</span>}
        {trace.has_safety_issues && <span className="text-yellow-500">⚠️ 安全问题</span>}
      </div>
    </button>
  );
}

// ─── Detail View ──────────────────────────────────────────────────

function TraceDetailView({
  trace,
  onClose,
}: {
  trace: TraceDetail;
  onClose: () => void;
}) {
  const sc = statusConfig(trace.status);

  return (
    <>
      {/* Header card */}
      <Card>
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-gray-400">{trace.trace_id}</span>
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${sc.color}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
                {sc.label}
              </span>
            </div>
            <p className="text-xs text-gray-500">
              患者: {trace.patient_id} · {formatTime(trace.created_at)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-xs px-2 py-1 rounded hover:bg-white/5"
          >
            ✕ 关闭
          </button>
        </div>
      </Card>

      {/* Query comparison */}
      <Card title="💬 问题">
        <div className="space-y-2">
          <div>
            <label className="text-[10px] text-gray-500 uppercase tracking-wide">原始问题</label>
            <p className="text-sm text-gray-200 mt-0.5">{trace.original_query}</p>
          </div>
          {trace.rephrased_query && (
            <div>
              <label className="text-[10px] text-gray-500 uppercase tracking-wide">重述后</label>
              <p className="text-sm text-gray-300 mt-0.5 italic">{trace.rephrased_query}</p>
            </div>
          )}
        </div>
      </Card>

      {/* Memory context */}
      {trace.memory_context_summary && (
        <Card title="🏛️ 记忆上下文">
          <p className="text-sm text-gray-300 leading-relaxed">{trace.memory_context_summary}</p>
        </Card>
      )}

      {/* Routed experts */}
      <Card title="🧑‍⚕️ 专家路由">
        <div className="flex flex-wrap gap-2">
          {trace.routed_experts.map((expertId) => (
            <span
              key={expertId}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-700 border border-white/10 text-xs text-gray-300"
            >
              <span>{EXPERT_ICONS[expertId] || '👤'}</span>
              {expertId}
            </span>
          ))}
        </div>
      </Card>

      {/* Expert outputs — collapsible panels */}
      <Card title="📊 专家意见">
        <div className="space-y-2">
          {trace.expert_outputs.map((expert) => (
            <ExpertPanel key={expert.expert_id} expert={expert} />
          ))}
        </div>
      </Card>

      {/* Safety review */}
      {trace.safety_review && <SafetyReviewCard review={trace.safety_review} />}

      {/* Final response */}
      <Card title="✅ 最终答复">
        <div className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
          {trace.final_response}
        </div>
      </Card>

      {/* Writeback candidates */}
      {trace.writeback_candidates.length > 0 && (
        <Card title="💾 写回候选">
          <div className="space-y-2">
            {trace.writeback_candidates.map((wb) => {
              const wsc = writebackStatusConfig(wb.status);
              return (
                <div
                  key={wb.id}
                  className="rounded bg-surface-800 border border-white/5 p-2.5"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-gray-400">{wb.path}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${wsc.color}`}>
                      {wsc.label}
                    </span>
                  </div>
                  <p className="text-xs text-gray-300">{wb.content}</p>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Timing breakdown */}
      <Card title="⏱️ 耗时分解">
        <TimingBar timing={trace.timing} />
      </Card>

      {/* Errors */}
      {trace.errors.length > 0 && (
        <Card title="❌ 错误">
          <ul className="space-y-1">
            {trace.errors.map((err, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-red-400">
                <span className="text-red-500 mt-0.5">•</span>
                {err}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}

// ─── Sub-components ───────────────────────────────────────────────

function Card({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-surface-800/50 border border-white/5 p-4">
      {title && (
        <h3 className="text-sm font-medium text-gray-300 mb-3">{title}</h3>
      )}
      {children}
    </div>
  );
}

function ExpertPanel({ expert }: { expert: ExpertOutput }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="rounded bg-surface-800 border border-white/10 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span>{EXPERT_ICONS[expert.expert_id] || '👤'}</span>
          <span className="text-sm font-medium text-gray-200">{expert.expert_name}</span>
          {expert.duration_ms && (
            <span className="text-[10px] text-gray-500">{formatDuration(expert.duration_ms)}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-500">
            {expert.recommendations.length} 建议
            {expert.risks.length > 0 && ` · ${expert.risks.length} 风险`}
            {expert.uncertainties.length > 0 && ` · ${expert.uncertainties.length} 不确定`}
          </span>
          <span className={`text-gray-500 text-xs transition-transform ${isOpen ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-3 border-t border-white/5 pt-3">
              {/* Recommendations */}
              {expert.recommendations.length > 0 && (
                <div>
                  <label className="text-[10px] text-green-400 uppercase tracking-wide font-medium">建议</label>
                  <ul className="mt-1 space-y-1">
                    {expert.recommendations.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-300">
                        <span className="text-green-500 mt-0.5">•</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {/* Risks */}
              {expert.risks.length > 0 && (
                <div>
                  <label className="text-[10px] text-yellow-400 uppercase tracking-wide font-medium">风险</label>
                  <ul className="mt-1 space-y-1">
                    {expert.risks.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-300">
                        <span className="text-yellow-500 mt-0.5">⚠</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {/* Uncertainties */}
              {expert.uncertainties.length > 0 && (
                <div>
                  <label className="text-[10px] text-blue-400 uppercase tracking-wide font-medium">不确定因素</label>
                  <ul className="mt-1 space-y-1">
                    {expert.uncertainties.map((u, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-300">
                        <span className="text-blue-500 mt-0.5">?</span>
                        {u}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SafetyReviewCard({ review }: { review: TraceDetail['safety_review'] }) {
  if (!review) return null;
  const sc = safetyColor(review.verdict);

  return (
    <div className={`rounded-lg border p-4 ${sc.bg}`}>
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-sm font-medium text-gray-300">🛡️ 安全审查</h3>
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${sc.text}`}>
          {sc.label}
        </span>
      </div>
      {review.details && (
        <p className="text-xs text-gray-300 mb-2">{review.details}</p>
      )}
      {review.issues.length > 0 && (
        <ul className="space-y-1">
          {review.issues.map((issue, i) => (
            <li key={i} className={`flex items-start gap-2 text-xs ${sc.text}`}>
              <span className="mt-0.5">•</span>
              {issue}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TimingBar({ timing }: { timing: TraceDetail['timing'] }) {
  const total = timing.total_ms || 1;
  const segments = [
    { label: '记忆检索', ms: timing.memory_retrieval_ms, color: 'bg-blue-500' },
    { label: '专家调用', ms: timing.expert_consultation_ms, color: 'bg-purple-500' },
    { label: '安全审查', ms: timing.safety_review_ms, color: 'bg-green-500' },
  ];
  const other = total - segments.reduce((acc, s) => acc + s.ms, 0);

  return (
    <div>
      {/* Bar */}
      <div className="flex h-3 rounded-full overflow-hidden bg-surface-700 mb-3">
        {segments.map((seg) => (
          <div
            key={seg.label}
            className={`${seg.color} transition-all duration-300`}
            style={{ width: `${(seg.ms / total) * 100}%` }}
            title={`${seg.label}: ${formatDuration(seg.ms)}`}
          />
        ))}
        {other > 0 && (
          <div
            className="bg-gray-600"
            style={{ width: `${(other / total) * 100}%` }}
            title={`其他: ${formatDuration(other)}`}
          />
        )}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {segments.map((seg) => (
          <div key={seg.label} className="flex items-center gap-1.5 text-[10px] text-gray-400">
            <span className={`w-2 h-2 rounded-sm ${seg.color}`} />
            {seg.label}: {formatDuration(seg.ms)}
            <span className="text-gray-600">({((seg.ms / total) * 100).toFixed(0)}%)</span>
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-[10px] text-gray-400">
          <span className="w-2 h-2 rounded-sm bg-gray-600" />
          总计: {formatDuration(total)}
        </div>
      </div>
    </div>
  );
}
