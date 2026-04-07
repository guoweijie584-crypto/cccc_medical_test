import { useState } from "react";

export interface EvaluationRecord {
  evaluation_id: string;
  patient_id: string;
  query: string;
  response: string;
  expert_opinions: Record<string, string>;
  label: string;
  safety: string | null;
  personalized: boolean | null;
  advice_direction: string | null;
  reviewer_notes: string;
  reviewer_id: string;
  timestamp: string;
  consultation_timestamp: string;
  status: string;
}

interface EvaluationCardProps {
  evaluation: EvaluationRecord;
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

const LABEL_CONFIG: Record<string, { text: string; icon: string; color: string; hoverBg: string; activeBg: string }> = {
  GOOD: {
    text: "好",
    icon: "👍",
    color: "text-emerald-400",
    hoverBg: "hover:bg-emerald-500/20",
    activeBg: "bg-emerald-500/30 border-emerald-400",
  },
  BAD: {
    text: "坏",
    icon: "👎",
    color: "text-red-400",
    hoverBg: "hover:bg-red-500/20",
    activeBg: "bg-red-500/30 border-red-400",
  },
  NEUTRAL: {
    text: "中立",
    icon: "➖",
    color: "text-gray-400",
    hoverBg: "hover:bg-gray-500/20",
    activeBg: "bg-gray-500/30 border-gray-400",
  },
  ERROR: {
    text: "错误",
    icon: "⚠️",
    color: "text-amber-400",
    hoverBg: "hover:bg-amber-500/20",
    activeBg: "bg-amber-500/30 border-amber-400",
  },
};

const SAFETY_OPTIONS = [
  { value: "safe", label: "安全" },
  { value: "risky", label: "有风险" },
  { value: "dangerous", label: "危险" },
];

const ADVICE_OPTIONS = [
  { value: "correct", label: "正确" },
  { value: "partial", label: "部分正确" },
  { value: "wrong", label: "错误" },
];

export function EvaluationCard({ evaluation, isDark, onSubmit }: EvaluationCardProps) {
  const [selectedLabel, setSelectedLabel] = useState<string>("");
  const [safety, setSafety] = useState<string>("");
  const [adviceDirection, setAdviceDirection] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleSubmit = async () => {
    if (!selectedLabel) return;
    setSubmitting(true);
    try {
      await onSubmit(evaluation.evaluation_id, {
        label: selectedLabel,
        safety: safety || undefined,
        advice_direction: adviceDirection || undefined,
        reviewer_notes: notes || undefined,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const cardBg = isDark ? "bg-slate-800/60 border-slate-700" : "bg-white border-gray-200";
  const mutedText = isDark ? "text-slate-400" : "text-gray-500";

  return (
    <div className={`rounded-xl border p-4 transition-all ${cardBg}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-mono ${mutedText}`}>
          患者 {evaluation.patient_id.slice(-8)}
        </span>
        <span className={`text-xs ${mutedText}`}>
          {evaluation.consultation_timestamp
            ? new Date(evaluation.consultation_timestamp).toLocaleString("zh-CN")
            : ""}
        </span>
      </div>

      {/* Query */}
      <div className="mb-3">
        <p className={`text-sm font-medium ${isDark ? "text-slate-200" : "text-gray-800"}`}>
          {evaluation.query}
        </p>
      </div>

      {/* Response (collapsible) */}
      <div className="mb-3">
        <button
          onClick={() => setExpanded(!expanded)}
          className={`text-xs ${mutedText} hover:underline`}
        >
          {expanded ? "收起回答 ▲" : "展开回答 ▼"}
        </button>
        {expanded && (
          <div
            className={`mt-2 p-3 rounded-lg text-sm leading-relaxed ${
              isDark ? "bg-slate-900/60 text-slate-300" : "bg-gray-50 text-gray-700"
            }`}
          >
            {evaluation.response}
            {Object.keys(evaluation.expert_opinions || {}).length > 0 && (
              <div className={`mt-3 pt-3 border-t ${isDark ? "border-slate-700" : "border-gray-200"}`}>
                <span className={`text-xs font-medium ${mutedText}`}>专家意见：</span>
                {Object.entries(evaluation.expert_opinions).map(([role, opinion]) => (
                  <div key={role} className="mt-1">
                    <span className={`text-xs font-medium ${isDark ? "text-slate-400" : "text-gray-500"}`}>
                      {role}：
                    </span>
                    <span className="text-xs">{opinion}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Label buttons */}
      <div className="flex items-center gap-2 mb-3">
        {Object.entries(LABEL_CONFIG).map(([key, cfg]) => (
          <button
            key={key}
            onClick={() => setSelectedLabel(key)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm font-medium transition-all ${
              selectedLabel === key
                ? cfg.activeBg
                : `border-transparent ${cfg.hoverBg} ${isDark ? "bg-slate-700/40" : "bg-gray-100"}`
            } ${cfg.color}`}
          >
            <span>{cfg.icon}</span>
            <span>{cfg.text}</span>
          </button>
        ))}
      </div>

      {/* Optional fields (shown after label selection) */}
      {selectedLabel && (
        <div className="space-y-3 mb-3">
          {/* Safety */}
          <div className="flex items-center gap-2">
            <span className={`text-xs w-14 ${mutedText}`}>安全性</span>
            <div className="flex gap-1.5">
              {SAFETY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setSafety(safety === opt.value ? "" : opt.value)}
                  className={`px-2.5 py-1 rounded text-xs transition-all ${
                    safety === opt.value
                      ? "bg-blue-500/20 text-blue-400 border border-blue-400/40"
                      : `${isDark ? "bg-slate-700/40 text-slate-400" : "bg-gray-100 text-gray-500"} border border-transparent`
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Advice direction */}
          <div className="flex items-center gap-2">
            <span className={`text-xs w-14 ${mutedText}`}>建议方向</span>
            <div className="flex gap-1.5">
              {ADVICE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setAdviceDirection(adviceDirection === opt.value ? "" : opt.value)}
                  className={`px-2.5 py-1 rounded text-xs transition-all ${
                    adviceDirection === opt.value
                      ? "bg-blue-500/20 text-blue-400 border border-blue-400/40"
                      : `${isDark ? "bg-slate-700/40 text-slate-400" : "bg-gray-100 text-gray-500"} border border-transparent`
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div className="flex items-start gap-2">
            <span className={`text-xs w-14 pt-2 ${mutedText}`}>备注</span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="可选：说明为什么打这个标签..."
              rows={2}
              className={`flex-1 px-3 py-2 rounded-lg text-sm resize-none border outline-none transition-colors ${
                isDark
                  ? "bg-slate-900/60 border-slate-600 text-slate-200 placeholder:text-slate-500 focus:border-blue-500/50"
                  : "bg-gray-50 border-gray-300 text-gray-800 placeholder:text-gray-400 focus:border-blue-400"
              }`}
            />
          </div>
        </div>
      )}

      {/* Submit */}
      <div className="flex justify-end">
        <button
          disabled={!selectedLabel || submitting}
          onClick={handleSubmit}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            selectedLabel && !submitting
              ? "bg-blue-500 text-white hover:bg-blue-600 active:scale-95"
              : `cursor-not-allowed ${isDark ? "bg-slate-700 text-slate-500" : "bg-gray-200 text-gray-400"}`
          }`}
        >
          {submitting ? "提交中..." : "提交评价"}
        </button>
      </div>
    </div>
  );
}
