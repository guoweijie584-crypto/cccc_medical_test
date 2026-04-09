import { useCallback, useEffect, useState } from "react";
import { medicalApiUrl } from "./api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HealthResponse {
  status: string;
  memory_palace_status: string;
  llm_mode: string;
  version: string;
}

interface GroupSnapshot {
  group_id: string;
  state: string;
  running: boolean;
  actor_ids: string[];
}

interface NativeStatusResponse {
  main_group: GroupSnapshot | Record<string, never>;
  evaluation_group: GroupSnapshot | Record<string, never>;
}

interface ActorItem {
  id: string;
  title?: string;
  running?: boolean;
  enabled?: boolean;
  runtime?: string;
}

interface NativeActorsResponse {
  main_group_actors: ActorItem[];
  evaluation_group_actors: ActorItem[];
}

interface EvalStats {
  total: number;
  good: number;
  bad: number;
  neutral: number;
  error: number;
  good_rate: number;
  pending_count: number;
  attention_count: number;
}

interface ErrorEntry {
  trace_id: string;
  timestamp: string;
  message: string;
  severity: "error" | "warning" | "info";
  patient_id?: string;
}

interface ErrorsResponse {
  errors: ErrorEntry[];
}

// ---------------------------------------------------------------------------
// Mock / fallback data
// ---------------------------------------------------------------------------

const MOCK_HEALTH: HealthResponse = {
  status: "healthy",
  memory_palace_status: "ok",
  llm_mode: "mock",
  version: "2.0.0",
};

const MOCK_STATS: EvalStats = {
  total: 47,
  good: 32,
  bad: 5,
  neutral: 8,
  error: 2,
  good_rate: 0.68,
  pending_count: 6,
  attention_count: 3,
};

const MOCK_ERRORS: ErrorEntry[] = [
  {
    trace_id: "trc-mock-001",
    timestamp: new Date(Date.now() - 600_000).toISOString(),
    message: "LLM response timeout after 30 s (mock fallback active)",
    severity: "warning",
    patient_id: "P-demo-01",
  },
  {
    trace_id: "trc-mock-002",
    timestamp: new Date(Date.now() - 1_800_000).toISOString(),
    message: "Memory Palace write failed: connection refused",
    severity: "error",
  },
  {
    trace_id: "trc-mock-003",
    timestamp: new Date(Date.now() - 3_600_000).toISOString(),
    message: "Evaluation actor restarted due to OOM",
    severity: "warning",
    patient_id: "P-demo-03",
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isGroupSnapshot(g: GroupSnapshot | Record<string, never>): g is GroupSnapshot {
  return "group_id" in g && typeof (g as GroupSnapshot).group_id === "string";
}

function statusDotClass(level: "good" | "warn" | "bad"): string {
  if (level === "good") return "bg-emerald-500";
  if (level === "warn") return "bg-amber-500";
  return "bg-red-500";
}

function severityColor(severity: ErrorEntry["severity"]): string {
  if (severity === "error") return "text-red-400";
  if (severity === "warning") return "text-amber-400";
  return "text-sky-400";
}

function severityIcon(severity: ErrorEntry["severity"]): string {
  if (severity === "error") return "\u2718"; // ✘
  if (severity === "warning") return "\u26A0"; // ⚠
  return "\u2139"; // ℹ
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

async function safeFetch<T>(url: string, fallback: T): Promise<T> {
  try {
    const resp = await fetch(url);
    if (!resp.ok) return fallback;
    return (await resp.json()) as T;
  } catch {
    return fallback;
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusDot({ level }: { level: "good" | "warn" | "bad" }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${statusDotClass(level)}`}
      style={{ boxShadow: `0 0 6px ${level === "good" ? "#10b981" : level === "warn" ? "#f59e0b" : "#ef4444"}` }}
    />
  );
}

function SystemStatusCard({
  label,
  value,
  level,
  sublabel,
}: {
  label: string;
  value: string;
  level: "good" | "warn" | "bad";
  sublabel?: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--glass-border-subtle)] p-4">
      <div className="flex items-center gap-2">
        <StatusDot level={level} />
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-tertiary)]">{label}</span>
      </div>
      <div className="mt-2 text-base font-semibold text-[var(--color-text-primary)]">{value}</div>
      {sublabel && <div className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{sublabel}</div>}
    </div>
  );
}

function GroupCard({
  title,
  group,
  actorCount,
  busy,
  target,
  onStart,
  onStop,
}: {
  title: string;
  group: GroupSnapshot | null;
  actorCount: number;
  busy: string | null;
  target: "main" | "evaluation";
  onStart: (t: "main" | "evaluation") => void;
  onStop: (t: "main" | "evaluation") => void;
}) {
  const isRunning = group?.running ?? false;
  const isStarting = busy === `${target}:start`;
  const isStopping = busy === `${target}:stop`;

  return (
    <div className="rounded-lg border border-[var(--glass-border-subtle)] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</div>
          <div className="text-xs text-[var(--color-text-tertiary)]">
            {group ? group.group_id : "Not initialized"}
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <StatusDot level={isRunning ? "good" : "warn"} />
          <span className="text-xs text-[var(--color-text-secondary)]">{group?.state ?? "unknown"}</span>
        </div>
      </div>

      <div className="text-xs text-[var(--color-text-secondary)]">
        {actorCount} actor{actorCount !== 1 ? "s" : ""} registered
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => onStart(target)}
          disabled={isStarting || isRunning}
          className="glass-btn rounded-lg px-3 py-1.5 text-xs disabled:opacity-40"
        >
          {isStarting ? "Starting\u2026" : "Start"}
        </button>
        <button
          onClick={() => onStop(target)}
          disabled={isStopping || !isRunning}
          className="glass-btn rounded-lg px-3 py-1.5 text-xs disabled:opacity-40"
        >
          {isStopping ? "Stopping\u2026" : "Stop"}
        </button>
      </div>
    </div>
  );
}

function StatNumber({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="text-center">
      <div className={`text-xl font-bold ${color ?? "text-[var(--color-text-primary)]"}`}>{value}</div>
      <div className="text-xs text-[var(--color-text-tertiary)]">{label}</div>
    </div>
  );
}

function DistributionBar({ stats }: { stats: EvalStats }) {
  const total = stats.total || 1;
  const segments: { pct: number; color: string; label: string }[] = [
    { pct: (stats.good / total) * 100, color: "bg-emerald-500", label: "Good" },
    { pct: (stats.neutral / total) * 100, color: "bg-slate-400", label: "Neutral" },
    { pct: (stats.bad / total) * 100, color: "bg-amber-500", label: "Bad" },
    { pct: (stats.error / total) * 100, color: "bg-red-500", label: "Error" },
  ];
  return (
    <div className="space-y-1.5">
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-slate-700/30">
        {segments.map((s) =>
          s.pct > 0 ? (
            <div key={s.label} className={`${s.color} transition-all`} style={{ width: `${s.pct}%` }} title={`${s.label}: ${s.pct.toFixed(1)}%`} />
          ) : null,
        )}
      </div>
      <div className="flex justify-between text-[10px] text-[var(--color-text-tertiary)]">
        {segments.map((s) => (
          <span key={s.label} className="flex items-center gap-1">
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${s.color}`} />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function SystemAdminPanel({ isDark }: { isDark: boolean }) {
  // ----- state -----
  const [health, setHealth] = useState<HealthResponse>(MOCK_HEALTH);
  const [nativeStatus, setNativeStatus] = useState<NativeStatusResponse | null>(null);
  const [actors, setActors] = useState<NativeActorsResponse | null>(null);
  const [evalStats, setEvalStats] = useState<EvalStats>(MOCK_STATS);
  const [errors, setErrors] = useState<ErrorEntry[]>(MOCK_ERRORS);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionResult, setActionResult] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  // ----- data fetching -----
  const refresh = useCallback(async () => {
    setLoading(true);
    setRefreshError(null);
    try {
      const [h, ns, ac, es, er] = await Promise.all([
        safeFetch<HealthResponse>(medicalApiUrl("/api/health"), MOCK_HEALTH),
        safeFetch<NativeStatusResponse>(medicalApiUrl("/api/cccc-native/status"), { main_group: {}, evaluation_group: {} }),
        safeFetch<NativeActorsResponse>(medicalApiUrl("/api/cccc-native/actors"), { main_group_actors: [], evaluation_group_actors: [] }),
        safeFetch<EvalStats>(medicalApiUrl("/api/evaluations/stats"), MOCK_STATS),
        safeFetch<ErrorsResponse>(medicalApiUrl("/api/admin/errors?limit=20"), { errors: MOCK_ERRORS }),
      ]);
      setHealth(h);
      setNativeStatus(ns);
      setActors(ac);
      setEvalStats(es);
      setErrors(er.errors?.length ? er.errors : MOCK_ERRORS);
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // ----- group actions -----
  const handleStartGroup = async (target: "main" | "evaluation") => {
    try {
      setBusy(`${target}:start`);
      const resp = await fetch(medicalApiUrl("/api/cccc-native/groups/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target }),
      });
      if (!resp.ok) throw new Error("Failed to start group");
      await refresh();
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : "Start failed");
    } finally {
      setBusy(null);
    }
  };

  const handleStopGroup = async (target: "main" | "evaluation") => {
    try {
      setBusy(`${target}:stop`);
      const resp = await fetch(medicalApiUrl("/api/cccc-native/groups/stop"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target }),
      });
      if (!resp.ok) throw new Error("Failed to stop group");
      await refresh();
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : "Stop failed");
    } finally {
      setBusy(null);
    }
  };

  // ----- quick actions -----
  const handleTriggerEvolution = async () => {
    try {
      setActionResult(null);
      setActionError(null);
      setBusy("evolution");
      const resp = await fetch(medicalApiUrl("/api/evolution/human-driven"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!resp.ok) throw new Error(`Evolution trigger failed (${resp.status})`);
      const data = await resp.json();
      setActionResult(
        data.message || data.status || "Human-evaluation-driven optimization triggered successfully.",
      );
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Evolution trigger failed");
    } finally {
      setBusy(null);
    }
  };

  // ----- derived -----
  const mainGroup = nativeStatus?.main_group && isGroupSnapshot(nativeStatus.main_group)
    ? nativeStatus.main_group
    : null;
  const evalGroup = nativeStatus?.evaluation_group && isGroupSnapshot(nativeStatus.evaluation_group)
    ? nativeStatus.evaluation_group
    : null;

  const apiLevel: "good" | "warn" | "bad" =
    health.status === "healthy" ? "good" : health.status === "degraded" ? "warn" : "bad";
  const mpLevel: "good" | "warn" | "bad" =
    health.memory_palace_status === "ok" || health.memory_palace_status === "healthy"
      ? "good"
      : health.memory_palace_status === "degraded"
        ? "warn"
        : "bad";
  const llmLevel: "good" | "warn" | "bad" = health.llm_mode === "llm" ? "good" : "warn";

  const cardBg = isDark ? "bg-slate-800/30" : "bg-white/50";

  // ----- render -----
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className={`glass-card rounded-xl p-4 ${cardBg}`}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
              System Administration
            </h3>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Multi-agent medical system operations and monitoring
            </p>
          </div>
          <button
            onClick={() => void refresh()}
            disabled={loading}
            className="glass-btn rounded-lg px-4 py-2 text-sm disabled:opacity-50"
          >
            {loading ? "Refreshing\u2026" : "Refresh All"}
          </button>
        </div>
        {refreshError && (
          <div className="mt-2 text-sm text-red-400">{refreshError}</div>
        )}
      </div>

      {/* Section 1 \u2014 System Status */}
      <section className={`glass-card rounded-xl p-4 space-y-3 ${cardBg}`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
          System Status
        </h4>
        <div className="grid grid-cols-3 gap-4">
          <SystemStatusCard
            label="API Service"
            value={health.status === "healthy" ? "Healthy" : health.status}
            level={apiLevel}
            sublabel={`v${health.version}`}
          />
          <SystemStatusCard
            label="Memory Palace"
            value={
              mpLevel === "good"
                ? "Connected"
                : mpLevel === "warn"
                  ? "Degraded"
                  : "Unavailable"
            }
            level={mpLevel}
          />
          <SystemStatusCard
            label="LLM Mode"
            value={health.llm_mode === "llm" ? "Live LLM" : "Mock Mode"}
            level={llmLevel}
            sublabel={health.llm_mode}
          />
        </div>
      </section>

      {/* Section 2 \u2014 Agent Work Groups */}
      <section className={`glass-card rounded-xl p-4 space-y-3 ${cardBg}`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
          Agent Work Groups
        </h4>
        <div className="grid gap-4 lg:grid-cols-2">
          <GroupCard
            title="Main Medical Group"
            group={mainGroup}
            actorCount={actors?.main_group_actors?.length ?? 0}
            busy={busy}
            target="main"
            onStart={handleStartGroup}
            onStop={handleStopGroup}
          />
          <GroupCard
            title="Evaluation Group"
            group={evalGroup}
            actorCount={actors?.evaluation_group_actors?.length ?? 0}
            busy={busy}
            target="evaluation"
            onStart={handleStartGroup}
            onStop={handleStopGroup}
          />
        </div>
      </section>

      {/* Section 3 \u2014 Evaluation Stats */}
      <section className={`glass-card rounded-xl p-4 space-y-4 ${cardBg}`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
          Evaluation Stats Overview
        </h4>
        <div className="grid grid-cols-4 gap-4">
          <StatNumber label="Total" value={evalStats.total} />
          <StatNumber label="Good Rate" value={`${(evalStats.good_rate * 100).toFixed(0)}%`} color="text-emerald-400" />
          <StatNumber label="Pending" value={evalStats.pending_count} color="text-amber-400" />
          <StatNumber label="Attention" value={evalStats.attention_count} color="text-red-400" />
        </div>
        <DistributionBar stats={evalStats} />
      </section>

      {/* Section 4 \u2014 Recent Errors / Warnings */}
      <section className={`glass-card rounded-xl p-4 space-y-3 ${cardBg}`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
          Recent Errors &amp; Warnings
        </h4>
        {errors.length === 0 ? (
          <p className="text-sm text-[var(--color-text-tertiary)]">No recent errors.</p>
        ) : (
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {errors.map((entry) => (
              <div
                key={entry.trace_id}
                className="flex items-start gap-3 rounded-lg border border-[var(--glass-border-subtle)] px-3 py-2"
              >
                <span className={`mt-0.5 text-base leading-none ${severityColor(entry.severity)}`}>
                  {severityIcon(entry.severity)}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-[var(--color-text-primary)] break-words">{entry.message}</div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-[var(--color-text-tertiary)]">
                    <span className="font-mono">{entry.trace_id}</span>
                    <span>{relativeTime(entry.timestamp)}</span>
                    {entry.patient_id && <span>Patient: {entry.patient_id}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Section 5 \u2014 Quick Actions */}
      <section className={`glass-card rounded-xl p-4 space-y-3 ${cardBg}`}>
        <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
          Quick Actions
        </h4>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => void handleTriggerEvolution()}
            disabled={busy === "evolution"}
            className="glass-btn rounded-lg px-4 py-2 text-sm disabled:opacity-50"
          >
            {busy === "evolution"
              ? "Running\u2026"
              : "Trigger Human-Evaluation-Driven Optimization"}
          </button>
        </div>
        {actionResult && (
          <div className="text-sm text-emerald-400">{actionResult}</div>
        )}
        {actionError && (
          <div className="text-sm text-red-400">{actionError}</div>
        )}
      </section>
    </div>
  );
}

export default SystemAdminPanel;
