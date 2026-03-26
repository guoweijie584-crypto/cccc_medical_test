import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { EvolutionTimeline } from "../../components/medical/EvolutionTimeline";
import { medicalApiUrl } from "./api";

interface EvolutionReportProps {
  isDark: boolean;
}

interface PromptDetail {
  agent_id: string;
  changes?: string[];
}

interface MemoryDetail {
  operation: string;
  reason: string;
}

interface IterationData {
  iteration: number;
  timestamp: string;
  avgScore: number;
  medicalAccuracy: number;
  safety: number;
  completeness: number;
  personalization: number;
  consistency: number;
  promptChanges: number;
  memoryChanges: number;
  promptDetails?: PromptDetail[];
  memoryDetails?: MemoryDetail[];
}

interface ReportData {
  summary?: {
    initialScore?: number;
    finalScore?: number;
    improvement?: number;
    bestIteration?: number;
    mode?: string;
  };
  iterations?: IterationData[];
}

export function EvolutionReport({ isDark }: EvolutionReportProps) {
  const { t } = useTranslation("medical");
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        setLoading(true);
        const response = await fetch(medicalApiUrl("/api/evolution/report"));
        if (!response.ok) throw new Error("Failed to fetch report");
        const data = await response.json();
        setReport(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        setReport({ summary: {}, iterations: [] });
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-[var(--color-text-secondary)]">{t("加载报告中...")}</div>;
  }

  if (!report) return null;

  const iterations = report.iterations || [];
  const summary = report.summary || {};

  return (
    <div className="space-y-6">
      {error && <div className="text-sm text-red-400">{error}</div>}

      <div className="grid grid-cols-5 gap-4">
        <SummaryCard title={t("初始得分")} value={(summary.initialScore ?? 0).toFixed(2)} color="gray" />
        <SummaryCard title={t("最终得分")} value={(summary.finalScore ?? 0).toFixed(2)} color="cyan" />
        <SummaryCard title={t("提升幅度")} value={`${(summary.improvement ?? 0) >= 0 ? "+" : ""}${(summary.improvement ?? 0).toFixed(2)}`} color="emerald" />
        <SummaryCard title={t("最佳轮次")} value={String(summary.bestIteration ?? 0)} color="blue" />
        <SummaryCard title={t("模式")} value={String(summary.mode || "mock").toUpperCase()} color="purple" />
      </div>

      <div className={`glass-card rounded-xl overflow-hidden ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
        <div className="px-4 py-3 border-b border-[var(--glass-border-subtle)]">
          <h3 className="font-medium text-[var(--color-text-primary)]">{t("迭代评分趋势")}</h3>
        </div>
        <div className="p-4">
          <EvolutionTimeline iterations={convertToTimelineData(iterations)} height={350} />
        </div>
      </div>

      <div className={`glass-card rounded-xl overflow-hidden ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
        <div className="px-4 py-3 border-b border-[var(--glass-border-subtle)]">
          <h3 className="font-medium text-[var(--color-text-primary)]">{t("迭代评分详情")}</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-[var(--glass-bg-subtle)]">
              <tr>
                <th className="px-4 py-2 text-left text-[var(--color-text-secondary)]">{t("轮次")}</th>
                <th className="px-4 py-2 text-right text-[var(--color-text-secondary)]">{t("平均分")}</th>
                <th className="px-4 py-2 text-right text-[var(--color-text-secondary)]">{t("医学准确性")}</th>
                <th className="px-4 py-2 text-right text-[var(--color-text-secondary)]">{t("安全性")}</th>
                <th className="px-4 py-2 text-right text-[var(--color-text-secondary)]">{t("完整性")}</th>
                <th className="px-4 py-2 text-right text-[var(--color-text-secondary)]">{t("个性化")}</th>
                <th className="px-4 py-2 text-right text-[var(--color-text-secondary)]">{t("一致性")}</th>
                <th className="px-4 py-2 text-center text-[var(--color-text-secondary)]">{t("优化")}</th>
              </tr>
            </thead>
            <tbody>
              {iterations.map((iter) => (
                <tr key={iter.iteration} className="border-b border-[var(--glass-border-subtle)] last:border-0">
                  <td className="px-4 py-3 font-medium text-[var(--color-text-primary)]">
                    {t("第")}{iter.iteration}{t("轮")}
                  </td>
                  <td className="px-4 py-3 text-right text-cyan-400 font-semibold">{iter.avgScore.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right text-[var(--color-text-secondary)]">{iter.medicalAccuracy.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right text-[var(--color-text-secondary)]">{iter.safety.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right text-[var(--color-text-secondary)]">{iter.completeness.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right text-[var(--color-text-secondary)]">{iter.personalization.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right text-[var(--color-text-secondary)]">{iter.consistency.toFixed(2)}</td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400">
                      P{iter.promptChanges} / M{iter.memoryChanges}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <ChangePanel
          title={t("提示词优化记录")}
          icon="P"
          iterations={iterations}
          kind="prompt"
          isDark={isDark}
        />
        <ChangePanel
          title={t("记忆优化记录")}
          icon="M"
          iterations={iterations}
          kind="memory"
          isDark={isDark}
        />
      </div>
    </div>
  );
}

function SummaryCard({ title, value, color }: { title: string; value: string; color: string }) {
  const colorClasses: Record<string, string> = {
    gray: "text-slate-400",
    cyan: "text-cyan-400",
    emerald: "text-emerald-400",
    purple: "text-purple-400",
    blue: "text-blue-400",
  };

  return (
    <div className="glass-card p-4 rounded-xl text-center">
      <div className={`text-2xl font-bold ${colorClasses[color] || colorClasses.gray}`}>{value}</div>
      <div className="text-xs text-[var(--color-text-tertiary)] mt-1">{title}</div>
    </div>
  );
}

function ChangePanel({
  title,
  icon,
  iterations,
  kind,
  isDark,
}: {
  title: string;
  icon: string;
  iterations: IterationData[];
  kind: "prompt" | "memory";
  isDark: boolean;
}) {
  const entries = iterations.flatMap((iter) =>
    kind === "prompt"
      ? (iter.promptDetails || []).flatMap((detail) =>
          (detail.changes || []).map((change) => ({
            iteration: iter.iteration,
            label: detail.agent_id || "agent",
            text: change,
          }))
        )
      : (iter.memoryDetails || []).map((detail) => ({
          iteration: iter.iteration,
          label: detail.operation || "memory",
          text: detail.reason || "memory update",
        }))
  );

  return (
    <div className={`glass-card rounded-xl p-4 ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
      <h4 className="font-medium text-[var(--color-text-primary)] mb-3">
        {icon} {title}
      </h4>
      {entries.length === 0 ? (
        <div className="text-sm text-[var(--color-text-tertiary)]">No changes recorded yet.</div>
      ) : (
        <div className="space-y-2 text-sm">
          {entries.map((entry, idx) => (
            <div key={`${kind}-${idx}`} className="flex items-center gap-2 py-1 border-b border-[var(--glass-border-subtle)] last:border-0">
              <span className="text-xs px-1.5 py-0.5 rounded bg-[var(--glass-bg-subtle)] text-[var(--color-text-tertiary)]">
                {entry.iteration}
              </span>
              <span className="text-xs text-[var(--color-text-secondary)]">{entry.label}</span>
              <span className="text-[var(--color-text-primary)] flex-1">{entry.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function convertToTimelineData(iterations: IterationData[]) {
  return iterations.map((iter) => ({
    iteration: iter.iteration,
    timestamp: iter.timestamp,
    overall_score: iter.avgScore,
    medical_accuracy: iter.medicalAccuracy,
    safety: iter.safety,
    completeness: iter.completeness,
    personalization: iter.personalization,
    consistency: iter.consistency,
    changes: [
      ...(iter.promptChanges
        ? [{ type: "prompt" as const, description: `Optimized ${iter.promptChanges} prompt(s)` }]
        : []),
      ...(iter.memoryChanges
        ? [{ type: "memory" as const, description: `Changed ${iter.memoryChanges} memory item(s)` }]
        : []),
    ],
  }));
}

export default EvolutionReport;
