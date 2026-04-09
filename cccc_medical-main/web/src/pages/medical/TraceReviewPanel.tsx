/**
 * TraceReviewPanel - Trace review panel
 * Shows the full online-loop tracing pipeline:
 * User input -> Coordinator rewrite -> Memory context -> Expert routing
 * -> Safety review -> Final response -> Memory writeback
 */
import { useCallback, useEffect, useState } from "react";
import { medicalApiUrl } from "./api";

/* ───── Types ───── */

type TraceStatus = "success" | "partial_failure" | "failure";

interface TraceItem {
  trace_id: string;
  patient_id: string;
  query: string;
  status: TraceStatus;
  created_at: string;
  duration_ms?: number;
  expert_count?: number;
  has_safety_issues?: boolean;
}

interface TraceDetail {
  trace_id: string;
  patient_id: string;
  timestamp_start: string;
  timestamp_end: string;
  original_query: string;
  rewritten_query?: string;
  query_type?: string;
  routing_decision?: Record<string, unknown>;
  retrieved_memory_keys: string[];
  memory_dossier_summary: string;
  routed_agents: string[];
  expert_outputs: Record<string, unknown>;
  final_response: string;
  safety_review_passed: boolean;
  safety_risk_level: string;
  safety_issues: string[];
  writeback_candidates: Array<Record<string, unknown>>;
  writeback_results: string[];
  latency_total_ms: number;
  latency_memory_ms: number;
  latency_experts_ms: number;
  latency_synthesis_ms: number;
  latency_safety_ms: number;
  errors: Array<Record<string, string>>;
  partial_failure: boolean;
  mode: string;
}

/* ───── Mock data ───── */

const MOCK_TRACES: TraceItem[] = [
  { trace_id: "trace-demo-001", patient_id: "p-001", query: "空腹偏高需要调药吗", status: "success", created_at: "2026-04-09T10:30:00Z", duration_ms: 4500, expert_count: 3, has_safety_issues: false },
  { trace_id: "trace-demo-002", patient_id: "p-001", query: "二甲双胍和格列美脲能一起吃吗", status: "success", created_at: "2026-04-09T09:15:00Z", duration_ms: 3800, expert_count: 2, has_safety_issues: false },
  { trace_id: "trace-demo-003", patient_id: "p-002", query: "可以吃西瓜吗", status: "partial_failure", created_at: "2026-04-08T16:45:00Z", duration_ms: 6200, expert_count: 3, has_safety_issues: true },
];

const MOCK_DETAIL: TraceDetail = {
  trace_id: "trace-demo-001", patient_id: "p-001",
  timestamp_start: "2026-04-09T10:30:00Z", timestamp_end: "2026-04-09T10:30:04.500Z",
  original_query: "空腹偏高需要调药吗",
  rewritten_query: "患者(2型,二甲双胍)近期空腹偏高,询问是否调整方案",
  query_type: "medication",
  routing_decision: { query_type: "medication", needs_specialists: ["pharmacist", "doctor"] },
  retrieved_memory_keys: ["patients/p-001/profile", "patients/p-001/glucose/recent"],
  memory_dossier_summary: "张先生 58岁 2型5年 二甲双胍500mg bid 空腹7.8-8.6 HbA1c 7.8%",
  routed_agents: ["pharmacist", "doctor", "nutritionist", "safety_reviewer"],
  expert_outputs: {
    pharmacist: { response: "二甲双胍可逐步增量至1000mg bid", recommendations: ["逐步增量", "餐中服用"], risks: ["监测B12", "肾功能调量"], confidence: 0.85 },
    doctor: { response: "建议复查HbA1c确认整体控糖", recommendations: ["复查HbA1c", "考虑增量"], risks: ["胃肠反应"], confidence: 0.75 },
    nutritionist: { response: "控制晚餐碳水，增加膳食纤维", recommendations: ["控碳水", "增纤维"], risks: [], confidence: 0.8 },
  },
  final_response: "根据空腹7.8-8.6偏高趋势:\n1. 复查HbA1c\n2. 二甲双胍可在医生指导下增量\n3. 控制晚餐碳水\n\n请务必面诊后决定用药调整。",
  safety_review_passed: true, safety_risk_level: "safe", safety_issues: [],
  writeback_candidates: [
    { category: "medication", content: "空腹偏高 建议复查HbA1c 考虑增量", confidence: 0.85 },
    { category: "diet", content: "控制晚餐碳水 增加膳食纤维", confidence: 0.7 },
  ],
  writeback_results: ["memory-palace://patients/p-001/medication/20260409"],
  latency_total_ms: 4500, latency_memory_ms: 320, latency_experts_ms: 3030, latency_synthesis_ms: 700, latency_safety_ms: 450,
  errors: [], partial_failure: false, mode: "mock",
};

/* ───── Helpers ───── */

function fmt(iso: string): string {
  try { return new Date(iso).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
}
function fmtMs(ms: number): string { return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`; }

function statusCfg(s: TraceStatus) {
  if (s === "success") return { label: "成功", cls: "text-emerald-400 bg-emerald-500/20", dot: "bg-emerald-400" };
  if (s === "partial_failure") return { label: "部分失败", cls: "text-amber-400 bg-amber-500/20", dot: "bg-amber-400" };
  return { label: "失败", cls: "text-red-400 bg-red-500/20", dot: "bg-red-400" };
}
function safetyCfg(level: string) {
  if (level === "safe") return { label: "安全", cls: "text-emerald-400", bg: "border-emerald-500/30 bg-emerald-500/10" };
  if (level === "caution") return { label: "注意", cls: "text-amber-400", bg: "border-amber-500/30 bg-amber-500/10" };
  if (level === "warning") return { label: "警告", cls: "text-orange-400", bg: "border-orange-500/30 bg-orange-500/10" };
  return { label: "危险", cls: "text-red-400", bg: "border-red-500/30 bg-red-500/10" };
}

const ICONS: Record<string, string> = { doctor: "🩺", pharmacist: "💊", nutritionist: "🥗", primary: "👨‍⚕️", safety_reviewer: "🛡️" };

/* ───── Main ───── */

interface TraceReviewPanelProps { isDark: boolean; }

export function TraceReviewPanel({ isDark }: TraceReviewPanelProps) {
  const [traces, setTraces] = useState<TraceItem[]>([]);
  const [selected, setSelected] = useState<TraceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const card = `glass-card rounded-xl p-4 ${isDark ? "bg-slate-800/30" : "bg-white/50"}`;

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(medicalApiUrl("/api/traces?limit=50"));
      if (!res.ok) throw new Error("fail");
      const d = await res.json();
      const items = Array.isArray(d.traces) ? d.traces : [];
      setTraces(items.length > 0 ? items : MOCK_TRACES);
    } catch { setTraces(MOCK_TRACES); }
    finally { setLoading(false); }
  }, []);

  const fetchDetail = useCallback(async (id: string) => {
    setDetailLoading(true);
    try {
      const res = await fetch(medicalApiUrl(`/api/traces/${id}`));
      if (!res.ok) throw new Error("fail");
      const d = await res.json();
      setSelected(d.trace || d);
    } catch { setSelected({ ...MOCK_DETAIL, trace_id: id }); }
    finally { setDetailLoading(false); }
  }, []);

  useEffect(() => { fetchList(); }, [fetchList]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Trace 审阅</h2>
          <p className="text-xs text-[var(--color-text-tertiary)] mt-0.5">查看在线服务环的完整追踪链路</p>
        </div>
        <button onClick={fetchList} className="glass-btn px-3 py-1.5 rounded-lg text-sm">{loading ? "刷新中..." : "刷新"}</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" style={{ minHeight: "60vh" }}>
        {/* List */}
        <div className="lg:col-span-1 space-y-2 max-h-[70vh] overflow-auto pr-1">
          <div className="text-xs text-[var(--color-text-tertiary)] mb-2">共 {traces.length} 条</div>
          {loading && traces.length === 0
            ? [1,2,3].map(i => <div key={i} className="h-20 animate-pulse rounded-lg bg-white/5"/>)
            : traces.map(t => {
                const sc = statusCfg(t.status);
                const isSel = selected?.trace_id === t.trace_id;
                return (
                  <button key={t.trace_id} onClick={() => fetchDetail(t.trace_id)}
                    className={`w-full text-left rounded-lg p-3 border transition-all ${isSel ? "bg-cyan-600/10 border-cyan-500/30" : "bg-white/5 border-[var(--glass-border-subtle)] hover:bg-white/10"}`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono text-[var(--color-text-tertiary)] truncate">{t.trace_id}</span>
                      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${sc.cls}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`}/>{sc.label}
                      </span>
                    </div>
                    <p className="text-sm text-[var(--color-text-primary)] line-clamp-2 mb-1">{t.query}</p>
                    <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-tertiary)]">
                      <span>{fmt(t.created_at)}</span>
                      {t.duration_ms != null && <span>{fmtMs(t.duration_ms)}</span>}
                      {t.expert_count != null && <span>{t.expert_count} 位专家</span>}
                      {t.has_safety_issues && <span className="text-amber-400">安全问题</span>}
                    </div>
                  </button>
                );
              })}
        </div>

        {/* Detail */}
        <div className="lg:col-span-2 max-h-[70vh] overflow-auto pr-1">
          {detailLoading
            ? <div className="space-y-3">{[1,2,3,4].map(i => <div key={i} className="h-24 animate-pulse rounded-lg bg-white/5"/>)}</div>
            : selected
            ? <DetailView trace={selected} card={card} onClose={() => setSelected(null)} />
            : <div className={`${card} flex flex-col items-center justify-center py-16`}>
                <div className="text-3xl mb-3">📋</div>
                <p className="text-sm text-[var(--color-text-tertiary)]">点击左侧记录查看完整 Trace</p>
              </div>
          }
        </div>
      </div>
    </div>
  );
}

/* ───── Detail ───── */

function DetailView({ trace: t, card, onClose }: { trace: TraceDetail; card: string; onClose: () => void }) {
  const sc = statusCfg(t.partial_failure ? "partial_failure" : t.errors?.length ? "failure" : "success");
  const sf = safetyCfg(t.safety_risk_level);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className={card}>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-[var(--color-text-tertiary)]">{t.trace_id}</span>
              <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${sc.cls}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`}/>{sc.label}
              </span>
              <span className="text-[10px] text-[var(--color-text-tertiary)] px-1.5 py-0.5 rounded bg-white/5">{t.mode}</span>
            </div>
            <p className="text-xs text-[var(--color-text-tertiary)]">患者: {t.patient_id} &middot; {fmt(t.timestamp_start)}</p>
          </div>
          <button onClick={onClose} className="glass-btn px-2 py-1 rounded text-xs">关闭</button>
        </div>
      </div>

      {/* Query comparison */}
      <div className={card}>
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">💬 问题</h3>
        <div className="space-y-2 mt-2">
          <div>
            <label className="text-[10px] text-[var(--color-text-tertiary)] uppercase tracking-wide">原始问题</label>
            <p className="text-sm text-[var(--color-text-primary)] mt-0.5">{t.original_query}</p>
          </div>
          {t.rewritten_query && <div>
            <label className="text-[10px] text-[var(--color-text-tertiary)] uppercase tracking-wide">Coordinator 重述</label>
            <p className="text-sm text-[var(--color-text-secondary)] mt-0.5 italic">{t.rewritten_query}</p>
          </div>}
          {t.query_type && <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] text-[var(--color-text-tertiary)]">分类:</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400">{t.query_type}</span>
          </div>}
        </div>
      </div>

      {/* Memory context */}
      {t.memory_dossier_summary && <div className={card}>
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">🏛️ 记忆上下文</h3>
        <p className="text-sm text-[var(--color-text-secondary)] mt-2 leading-relaxed">{t.memory_dossier_summary}</p>
        {t.retrieved_memory_keys?.length > 0 && <div className="mt-2 flex flex-wrap gap-1">
          {t.retrieved_memory_keys.map((k, i) => <span key={i} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-[var(--color-text-tertiary)]">{k}</span>)}
        </div>}
      </div>}

      {/* Expert routing */}
      <div className={card}>
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">🧑‍⚕️ 专家路由</h3>
        <div className="flex flex-wrap gap-2 mt-2">
          {t.routed_agents.map(name => (
            <span key={name} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-[var(--glass-border-subtle)] text-xs text-[var(--color-text-secondary)]">
              <span>{ICONS[name] || "👤"}</span>{name}
            </span>
          ))}
        </div>
      </div>

      {/* Expert outputs */}
      <div className={card}>
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">📊 专家意见</h3>
        <div className="space-y-2 mt-2">
          {Object.entries(t.expert_outputs).map(([name, output]) => <ExpertPanel key={name} name={name} output={output as Record<string, unknown>} />)}
        </div>
      </div>

      {/* Safety review */}
      <div className={`glass-card rounded-xl p-4 border ${sf.bg}`}>
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-sm font-medium text-[var(--color-text-primary)]">🛡️ 安全审查</h3>
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${sf.cls}`}>{sf.label}</span>
        </div>
        {t.safety_issues?.length > 0
          ? <ul className="space-y-1 mt-1">{t.safety_issues.map((issue, i) => <li key={i} className={`flex items-start gap-2 text-xs ${sf.cls}`}><span className="mt-0.5">•</span>{issue}</li>)}</ul>
          : <p className="text-xs text-emerald-400 mt-1">审查通过，未发现安全风险。</p>}
      </div>

      {/* Final response */}
      <div className={card}>
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">✅ 最终答复</h3>
        <div className="text-sm text-[var(--color-text-primary)] mt-2 leading-relaxed whitespace-pre-wrap">{t.final_response}</div>
      </div>

      {/* Writeback */}
      {(t.writeback_candidates?.length > 0 || t.writeback_results?.length > 0) && <div className={card}>
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">💾 记忆写回</h3>
        <div className="space-y-2 mt-2">
          {t.writeback_candidates?.map((wb: any, i: number) => (
            <div key={i} className="rounded bg-white/5 border border-[var(--glass-border-subtle)] p-2.5">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-cyan-400">{wb.category || "memory"}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-[var(--color-text-tertiary)]">confidence: {(wb.confidence ?? 0.8).toFixed(2)}</span>
              </div>
              <p className="text-xs text-[var(--color-text-secondary)]">{wb.content || JSON.stringify(wb)}</p>
            </div>
          ))}
          {t.writeback_results?.length > 0 && <div className="text-[10px] text-emerald-400 mt-1">已写入: {t.writeback_results.join(", ")}</div>}
        </div>
      </div>}

      {/* Timing */}
      <div className={card}>
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">⏱️ 耗时分解</h3>
        <TimingBar total={t.latency_total_ms} memory={t.latency_memory_ms} experts={t.latency_experts_ms} synthesis={t.latency_synthesis_ms} safety={t.latency_safety_ms} />
      </div>

      {/* Errors */}
      {t.errors?.length > 0 && <div className={card}>
        <h3 className="text-sm font-medium text-[var(--color-text-primary)]">❌ 错误</h3>
        <ul className="space-y-1 mt-2">{t.errors.map((err, i) => <li key={i} className="flex items-start gap-2 text-sm text-red-400"><span className="text-red-500 mt-0.5">•</span>{err.error || JSON.stringify(err)}</li>)}</ul>
      </div>}
    </div>
  );
}

/* ───── Sub-components ───── */

function ExpertPanel({ name, output }: { name: string; output: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const recs = (output.recommendations as string[]) || [];
  const risks = (output.risks as string[]) || [];
  const response = (output.response as string) || "";
  const conf = (output.confidence as number) ?? 0;

  return (
    <div className="rounded border border-[var(--glass-border-subtle)] overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-white/5 transition-colors">
        <div className="flex items-center gap-2">
          <span>{ICONS[name] || "👤"}</span>
          <span className="text-sm font-medium text-[var(--color-text-primary)]">{name}</span>
          {conf > 0 && <span className="text-[10px] text-[var(--color-text-tertiary)]">confidence: {conf.toFixed(2)}</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--color-text-tertiary)]">{recs.length} 建议{risks.length > 0 ? ` · ${risks.length} 风险` : ""}</span>
          <span className={`text-xs text-[var(--color-text-tertiary)] transition-transform ${open ? "rotate-180" : ""}`}>▼</span>
        </div>
      </button>
      {open && <div className="px-3 pb-3 space-y-2 border-t border-[var(--glass-border-subtle)] pt-2">
        {response && <p className="text-xs text-[var(--color-text-secondary)] whitespace-pre-line">{response}</p>}
        {recs.length > 0 && <div>
          <label className="text-[10px] text-emerald-400 uppercase tracking-wide font-medium">建议</label>
          <ul className="mt-1 space-y-0.5">{recs.map((r, i) => <li key={i} className="flex items-start gap-1.5 text-xs text-[var(--color-text-secondary)]"><span className="text-emerald-500 mt-0.5">•</span>{r}</li>)}</ul>
        </div>}
        {risks.length > 0 && <div>
          <label className="text-[10px] text-amber-400 uppercase tracking-wide font-medium">风险</label>
          <ul className="mt-1 space-y-0.5">{risks.map((r, i) => <li key={i} className="flex items-start gap-1.5 text-xs text-[var(--color-text-secondary)]"><span className="text-amber-500 mt-0.5">⚠</span>{r}</li>)}</ul>
        </div>}
      </div>}
    </div>
  );
}

function TimingBar({ total, memory, experts, synthesis, safety }: { total: number; memory: number; experts: number; synthesis: number; safety: number }) {
  const t = total || 1;
  const segs = [
    { label: "记忆检索", ms: memory, color: "bg-blue-500" },
    { label: "专家调用", ms: experts, color: "bg-purple-500" },
    { label: "汇总合成", ms: synthesis, color: "bg-cyan-500" },
    { label: "安全审查", ms: safety, color: "bg-emerald-500" },
  ];
  const other = t - segs.reduce((a, s) => a + s.ms, 0);
  return (
    <div className="mt-2">
      <div className="flex h-3 rounded-full overflow-hidden bg-white/5 mb-3">
        {segs.map(s => <div key={s.label} className={`${s.color} transition-all`} style={{ width: `${(s.ms / t) * 100}%` }} title={`${s.label}: ${fmtMs(s.ms)}`} />)}
        {other > 0 && <div className="bg-gray-600" style={{ width: `${(other / t) * 100}%` }} title={`其他: ${fmtMs(other)}`} />}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {segs.map(s => <div key={s.label} className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-tertiary)]"><span className={`w-2 h-2 rounded-sm ${s.color}`}/>{s.label}: {fmtMs(s.ms)} <span className="opacity-50">({((s.ms / t) * 100).toFixed(0)}%)</span></div>)}
        <div className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-tertiary)]"><span className="w-2 h-2 rounded-sm bg-gray-600"/>总计: {fmtMs(t)}</div>
      </div>
    </div>
  );
}

export default TraceReviewPanel;
