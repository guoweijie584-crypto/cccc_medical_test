import { useState } from "react";

import type { EvaluationRecord } from "./EvaluationCard";

interface EvaluationHistoryProps {
  evaluations: EvaluationRecord[];
  loading: boolean;
  isDark: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

type FilterLabel = "ALL" | "GOOD" | "BAD" | "NEUTRAL" | "ERROR";

const FILTER_OPTIONS: { value: FilterLabel; label: string; icon: string }[] = [
  { value: "ALL", label: "全部", icon: "📋" },
  { value: "GOOD", label: "好", icon: "✅" },
  { value: "BAD", label: "坏", icon: "❌" },
  { value: "NEUTRAL", label: "中立", icon: "➖" },
  { value: "ERROR", label: "错误", icon: "⚠️" },
];

const LABEL_BADGE: Record<string, { text: string; className: string }> = {
  GOOD: { text: "好", className: "bg-emerald-500/20 text-emerald-400" },
  BAD: { text: "坏", className: "bg-red-500/20 text-red-400" },
  NEUTRAL: { text: "中立", className: "bg-gray-500/20 text-gray-400" },
  ERROR: { text: "错误", className: "bg-amber-500/20 text-amber-400" },
};

export function EvaluationHistory({ evaluations, loading, isDark, onLoadMore, hasMore }: EvaluationHistoryProps) {
  const [filter, setFilter] = useState<FilterLabel>("ALL");

  const filtered = filter === "ALL" ? evaluations : evaluations.filter((e) => e.label === filter);

  const mutedText = isDark ? "text-slate-400" : "text-gray-500";

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className={`rounded-lg border p-3 animate-pulse ${
              isDark ? "bg-slate-800/50 border-slate-700" : "bg-white border-gray-200"
            }`}
          >
            <div className={`h-3 w-full rounded ${isDark ? "bg-slate-700" : "bg-gray-200"}`} />
            <div className={`h-3 w-2/3 rounded mt-2 ${isDark ? "bg-slate-700" : "bg-gray-200"}`} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Filter tabs */}
      <div className="flex items-center gap-1.5 mb-3 flex-wrap">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setFilter(opt.value)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              filter === opt.value
                ? "bg-blue-500/20 text-blue-400 border border-blue-400/40"
                : `${isDark ? "bg-slate-700/40 text-slate-400" : "bg-gray-100 text-gray-500"} border border-transparent`
            }`}
          >
            <span>{opt.icon}</span>
            <span>{opt.label}</span>
          </button>
        ))}
      </div>

      {/* List */}
      {filtered.length === 0 ? (
        <div
          className={`rounded-lg border p-6 text-center ${
            isDark ? "bg-slate-800/30 border-slate-700" : "bg-white border-gray-200"
          }`}
        >
          <p className={`text-sm ${mutedText}`}>
            {filter === "ALL" ? "暂无历史评价" : `暂无标签为「${filter}」的评价`}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((evaluation) => {
            const badge = LABEL_BADGE[evaluation.label] || LABEL_BADGE.NEUTRAL;
            return (
              <div
                key={evaluation.evaluation_id}
                className={`rounded-lg border p-3 transition-all hover:scale-[1.005] ${
                  isDark ? "bg-slate-800/40 border-slate-700" : "bg-white border-gray-200"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${badge.className}`}>
                      {badge.text}
                    </span>
                    <span className={`text-xs font-mono ${mutedText}`}>
                      {evaluation.patient_id.slice(-8)}
                    </span>
                  </div>
                  <span className={`text-xs ${mutedText}`}>
                    {evaluation.timestamp
                      ? new Date(evaluation.timestamp).toLocaleString("zh-CN")
                      : ""}
                  </span>
                </div>

                <p className={`text-sm ${isDark ? "text-slate-300" : "text-gray-700"} line-clamp-2`}>
                  {evaluation.query}
                </p>

                {/* Optional metadata */}
                <div className="flex items-center gap-3 mt-1.5">
                  {evaluation.safety && (
                    <span className={`text-xs ${mutedText}`}>
                      安全性: {evaluation.safety === "safe" ? "安全" : evaluation.safety === "risky" ? "有风险" : "危险"}
                    </span>
                  )}
                  {evaluation.advice_direction && (
                    <span className={`text-xs ${mutedText}`}>
                      建议: {evaluation.advice_direction === "correct" ? "正确" : evaluation.advice_direction === "partial" ? "部分正确" : "错误"}
                    </span>
                  )}
                  {evaluation.reviewer_id && (
                    <span className={`text-xs ${mutedText}`}>
                      评价人: {evaluation.reviewer_id}
                    </span>
                  )}
                </div>

                {evaluation.reviewer_notes && (
                  <p className={`text-xs mt-1.5 italic ${mutedText}`}>
                    "{evaluation.reviewer_notes}"
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Load more */}
      {hasMore && onLoadMore && (
        <div className="flex justify-center mt-3">
          <button
            onClick={onLoadMore}
            className={`px-4 py-2 rounded-lg text-sm transition-all ${
              isDark
                ? "bg-slate-700/50 text-slate-300 hover:bg-slate-700"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            加载更多
          </button>
        </div>
      )}
    </div>
  );
}
