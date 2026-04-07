import { EvaluationCard, type EvaluationRecord } from "./EvaluationCard";

interface PendingEvaluationListProps {
  evaluations: EvaluationRecord[];
  loading: boolean;
  isDark: boolean;
  onSubmit: (
    evaluationId: string,
    data: {
      label: string;
      safety?: string;
      advice_direction?: string;
      reviewer_notes?: string;
      reviewer_id?: string;
    },
  ) => Promise<void>;
}

export function PendingEvaluationList({ evaluations, loading, isDark, onSubmit }: PendingEvaluationListProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className={`rounded-xl border p-4 animate-pulse ${
              isDark ? "bg-slate-800/50 border-slate-700" : "bg-white border-gray-200"
            }`}
          >
            <div className={`h-4 w-32 rounded ${isDark ? "bg-slate-700" : "bg-gray-200"}`} />
            <div className={`h-3 w-full rounded mt-3 ${isDark ? "bg-slate-700" : "bg-gray-200"}`} />
            <div className={`h-3 w-3/4 rounded mt-2 ${isDark ? "bg-slate-700" : "bg-gray-200"}`} />
            <div className="flex gap-2 mt-4">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className={`h-8 w-16 rounded ${isDark ? "bg-slate-700" : "bg-gray-200"}`} />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (evaluations.length === 0) {
    return (
      <div
        className={`rounded-xl border p-8 text-center ${
          isDark ? "bg-slate-800/30 border-slate-700" : "bg-white border-gray-200"
        }`}
      >
        <div className="text-4xl mb-2">✨</div>
        <p className={`text-sm ${isDark ? "text-slate-400" : "text-gray-500"}`}>
          暂无待评价记录
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {evaluations.map((evaluation) => (
        <EvaluationCard
          key={evaluation.evaluation_id}
          evaluation={evaluation}
          isDark={isDark}
          onSubmit={onSubmit}
        />
      ))}
    </div>
  );
}
