import { useCallback, useEffect, useState } from "react";

import type { EvaluationRecord } from "./EvaluationCard";
import { EvaluationHistory } from "./EvaluationHistory";
import { EvaluationStatsCards, type EvaluationStatsData } from "./EvaluationStatsCards";
import { PendingEvaluationList } from "./PendingEvaluationList";
import { medicalApiUrl } from "./api";

interface EvaluationViewProps {
  isDark: boolean;
}

export function EvaluationView({ isDark }: EvaluationViewProps) {
  const [stats, setStats] = useState<EvaluationStatsData | null>(null);
  const [pending, setPending] = useState<EvaluationRecord[]>([]);
  const [badList, setBadList] = useState<EvaluationRecord[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [pendingLoading, setPendingLoading] = useState(true);
  const [badLoading, setBadLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Fetchers ────────────────────────────────────────────────────

  const fetchStats = useCallback(async () => {
    try {
      setStatsLoading(true);
      const res = await fetch(medicalApiUrl("/api/evaluations/stats"));
      if (!res.ok) throw new Error("Failed to fetch stats");
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error("fetchStats error:", err);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const fetchPending = useCallback(async () => {
    try {
      setPendingLoading(true);
      const res = await fetch(medicalApiUrl("/api/evaluations/pending?limit=50"));
      if (!res.ok) throw new Error("Failed to fetch pending evaluations");
      const data = await res.json();
      setPending(Array.isArray(data.evaluations) ? data.evaluations : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setPendingLoading(false);
    }
  }, []);

  const fetchBad = useCallback(async () => {
    try {
      setBadLoading(true);
      const res = await fetch(medicalApiUrl("/api/evaluations/bad?limit=50"));
      if (!res.ok) throw new Error("Failed to fetch bad evaluations");
      const data = await res.json();
      setBadList(Array.isArray(data.evaluations) ? data.evaluations : []);
    } catch (err) {
      console.error("fetchBad error:", err);
    } finally {
      setBadLoading(false);
    }
  }, []);

  // ── Initial load ────────────────────────────────────────────────

  useEffect(() => {
    fetchStats();
    fetchPending();
    fetchBad();
  }, [fetchStats, fetchPending, fetchBad]);

  // ── Submit handler ──────────────────────────────────────────────

  const handleSubmit = useCallback(
    async (
      evaluationId: string,
      data: {
        label: string;
        safety?: string;
        advice_direction?: string;
        reviewer_notes?: string;
        reviewer_id?: string;
      },
    ) => {
      const res = await fetch(medicalApiUrl(`/api/evaluations/${evaluationId}/submit`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Submit failed" }));
        throw new Error(err.detail || "Submit failed");
      }
      // Refresh all data after successful submit
      await Promise.all([fetchStats(), fetchPending(), fetchBad()]);
    },
    [fetchStats, fetchPending, fetchBad],
  );

  // ── Render ──────────────────────────────────────────────────────

  const sectionTitle = (text: string, count?: number) => (
    <div className="flex items-center gap-2 mb-3 mt-6 first:mt-0">
      <h3 className={`text-sm font-semibold ${isDark ? "text-slate-200" : "text-gray-800"}`}>
        {text}
      </h3>
      {count !== undefined && (
        <span
          className={`px-2 py-0.5 rounded-full text-xs ${
            isDark ? "bg-slate-700 text-slate-300" : "bg-gray-200 text-gray-600"
          }`}
        >
          {count}
        </span>
      )}
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto space-y-1">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className={`text-lg font-bold ${isDark ? "text-slate-100" : "text-gray-900"}`}>
          评价管理
        </h2>
        <button
          onClick={() => {
            fetchStats();
            fetchPending();
            fetchBad();
          }}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            isDark
              ? "bg-slate-700/50 text-slate-300 hover:bg-slate-700"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          刷新
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400 mb-4">
          {error}
        </div>
      )}

      {/* Stats */}
      <EvaluationStatsCards stats={stats} loading={statsLoading} isDark={isDark} />

      {/* Pending evaluations */}
      {sectionTitle("待评价", pending.length)}
      <PendingEvaluationList
        evaluations={pending}
        loading={pendingLoading}
        isDark={isDark}
        onSubmit={handleSubmit}
      />

      {/* History (BAD/ERROR + all completed) */}
      {sectionTitle("历史评价 (BAD/ERROR)", badList.length)}
      <EvaluationHistory evaluations={badList} loading={badLoading} isDark={isDark} />
    </div>
  );
}
