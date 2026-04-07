import { useMemo } from "react";

export interface EvaluationStatsData {
  total: number;
  good: number;
  bad: number;
  neutral: number;
  error: number;
  pending: number;
  good_rate: number;
  needs_attention: number;
}

interface EvaluationStatsCardsProps {
  stats: EvaluationStatsData | null;
  loading: boolean;
  isDark: boolean;
}

interface StatCard {
  label: string;
  value: number | string;
  color: string;
  bg: string;
  icon: string;
}

export function EvaluationStatsCards({ stats, loading, isDark }: EvaluationStatsCardsProps) {
  const cards: StatCard[] = useMemo(() => {
    if (!stats) return [];
    return [
      {
        label: "总计",
        value: stats.total,
        color: "text-blue-400",
        bg: isDark ? "bg-blue-500/10 border-blue-500/20" : "bg-blue-50 border-blue-200",
        icon: "📊",
      },
      {
        label: "好",
        value: stats.good,
        color: "text-emerald-400",
        bg: isDark ? "bg-emerald-500/10 border-emerald-500/20" : "bg-emerald-50 border-emerald-200",
        icon: "✅",
      },
      {
        label: "坏",
        value: stats.bad,
        color: "text-red-400",
        bg: isDark ? "bg-red-500/10 border-red-500/20" : "bg-red-50 border-red-200",
        icon: "❌",
      },
      {
        label: "中立",
        value: stats.neutral,
        color: "text-gray-400",
        bg: isDark ? "bg-gray-500/10 border-gray-500/20" : "bg-gray-50 border-gray-200",
        icon: "➖",
      },
      {
        label: "错误",
        value: stats.error,
        color: "text-amber-400",
        bg: isDark ? "bg-amber-500/10 border-amber-500/20" : "bg-amber-50 border-amber-200",
        icon: "⚠️",
      },
      {
        label: "好评率",
        value: `${(stats.good_rate * 100).toFixed(1)}%`,
        color: "text-cyan-400",
        bg: isDark ? "bg-cyan-500/10 border-cyan-500/20" : "bg-cyan-50 border-cyan-200",
        icon: "📈",
      },
      {
        label: "待评价",
        value: stats.pending,
        color: "text-violet-400",
        bg: isDark ? "bg-violet-500/10 border-violet-500/20" : "bg-violet-50 border-violet-200",
        icon: "🕐",
      },
      {
        label: "需关注",
        value: stats.needs_attention,
        color: "text-rose-400",
        bg: isDark ? "bg-rose-500/10 border-rose-500/20" : "bg-rose-50 border-rose-200",
        icon: "🔔",
      },
    ];
  }, [stats, isDark]);

  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className={`rounded-xl border p-4 animate-pulse ${
              isDark ? "bg-slate-800/50 border-slate-700" : "bg-white border-gray-200"
            }`}
          >
            <div className={`h-4 w-16 rounded ${isDark ? "bg-slate-700" : "bg-gray-200"}`} />
            <div className={`h-8 w-12 rounded mt-2 ${isDark ? "bg-slate-700" : "bg-gray-200"}`} />
          </div>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`rounded-xl border p-4 transition-all hover:scale-[1.02] ${card.bg}`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-base">{card.icon}</span>
            <span className={`text-xs font-medium ${isDark ? "text-slate-400" : "text-gray-500"}`}>
              {card.label}
            </span>
          </div>
          <div className={`text-2xl font-bold ${card.color}`}>{card.value}</div>
        </div>
      ))}
    </div>
  );
}
