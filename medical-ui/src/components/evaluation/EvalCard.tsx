import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { EvalLabel, SafetyLevel, AdviceDirection, PendingEvaluation } from '../../stores/evaluationStore';

interface EvalCardProps {
  evaluation: PendingEvaluation;
  onSubmit: (id: string, data: {
    label: EvalLabel;
    safety?: SafetyLevel;
    personalized?: boolean;
    advice_direction?: AdviceDirection;
    reviewer_notes?: string;
  }) => Promise<boolean>;
}

const LABEL_CONFIG: Array<{ value: EvalLabel; label: string; icon: string; cls: string }> = [
  { value: 'GOOD', label: '好', icon: '👍', cls: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/30' },
  { value: 'BAD', label: '坏', icon: '👎', cls: 'bg-red-500/20 text-red-400 border-red-500/30 hover:bg-red-500/30' },
  { value: 'NEUTRAL', label: '中立', icon: '➖', cls: 'bg-gray-500/20 text-gray-400 border-gray-500/30 hover:bg-gray-500/30' },
  { value: 'ERROR', label: '错误', icon: '⚠️', cls: 'bg-amber-500/20 text-amber-400 border-amber-500/30 hover:bg-amber-500/30' },
];

const SAFETY_OPTIONS: Array<{ value: SafetyLevel; label: string }> = [
  { value: 'safe', label: '安全' },
  { value: 'risky', label: '有风险' },
  { value: 'dangerous', label: '危险' },
];

const DIRECTION_OPTIONS: Array<{ value: AdviceDirection; label: string }> = [
  { value: 'correct', label: '正确' },
  { value: 'partial', label: '部分正确' },
  { value: 'wrong', label: '错误' },
];

export function EvalCard({ evaluation, onSubmit }: EvalCardProps) {
  const [selectedLabel, setSelectedLabel] = useState<EvalLabel | null>(null);
  const [safety, setSafety] = useState<SafetyLevel | undefined>();
  const [personalized, setPersonalized] = useState<boolean | undefined>();
  const [adviceDirection, setAdviceDirection] = useState<AdviceDirection | undefined>();
  const [notes, setNotes] = useState('');
  const [expanded, setExpanded] = useState(false);
  const [showExtras, setShowExtras] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!selectedLabel) return;
    setSubmitting(true);
    const success = await onSubmit(evaluation.id, {
      label: selectedLabel,
      safety,
      personalized,
      advice_direction: adviceDirection,
      reviewer_notes: notes || undefined,
    });
    if (!success) setSubmitting(false);
  };

  return (
    <motion.div
      layout
      className="glass-panel p-4 space-y-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <span className="text-xs text-gray-500">患者 {evaluation.patient_id}</span>
          <p className="text-sm text-gray-200 mt-1 font-medium">"{evaluation.query}"</p>
        </div>
        <span className="text-xs text-gray-600 whitespace-nowrap">
          {evaluation.created_at ? new Date(evaluation.created_at).toLocaleDateString() : ''}
        </span>
      </div>

      {/* Response preview / full */}
      <div>
        <p className={`text-sm text-gray-400 ${expanded ? '' : 'line-clamp-2'}`}>
          {evaluation.response}
        </p>
        {evaluation.response.length > 120 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-primary-400 hover:text-primary-300 mt-1"
          >
            {expanded ? '收起' : '展开查看完整回答'}
          </button>
        )}
      </div>

      {/* Expert opinions */}
      <AnimatePresence>
        {expanded && evaluation.expert_opinions && Object.keys(evaluation.expert_opinions).length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="space-y-2 p-3 rounded-lg bg-white/3 border border-white/5">
              <div className="text-xs text-gray-500 font-medium">专家意见</div>
              {Object.entries(evaluation.expert_opinions).map(([role, opinion]) => (
                <div key={role} className="text-xs text-gray-400">
                  <span className="text-gray-500">{role}:</span> {opinion}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Label buttons */}
      <div className="flex gap-2 flex-wrap">
        {LABEL_CONFIG.map((item) => (
          <button
            key={item.value}
            onClick={() => setSelectedLabel(item.value)}
            disabled={submitting}
            className={`px-3 py-1.5 text-sm rounded-btn border transition-all ${
              selectedLabel === item.value
                ? `${item.cls} ring-1 ring-current scale-105`
                : `border-white/10 text-gray-500 hover:text-gray-300 hover:border-white/20`
            }`}
          >
            {item.icon} {item.label}
          </button>
        ))}
      </div>

      {/* Extra fields toggle */}
      {selectedLabel && (
        <button
          onClick={() => setShowExtras(!showExtras)}
          className="text-xs text-gray-500 hover:text-gray-400 transition-colors"
        >
          {showExtras ? '▾ 收起扩展字段' : '▸ 扩展字段（可选）'}
        </button>
      )}

      {/* Extra fields */}
      <AnimatePresence>
        {showExtras && selectedLabel && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden space-y-3"
          >
            {/* Safety */}
            <div>
              <div className="text-xs text-gray-500 mb-1.5">安全性</div>
              <div className="flex gap-2">
                {SAFETY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setSafety(safety === opt.value ? undefined : opt.value)}
                    className={`px-2.5 py-1 text-xs rounded-btn border transition-colors ${
                      safety === opt.value
                        ? 'border-cyan-500/40 bg-cyan-500/15 text-cyan-400'
                        : 'border-white/10 text-gray-500 hover:text-gray-400'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Personalized */}
            <div>
              <div className="text-xs text-gray-500 mb-1.5">个性化</div>
              <div className="flex gap-2">
                {[
                  { value: true, label: '是' },
                  { value: false, label: '否' },
                ].map((opt) => (
                  <button
                    key={String(opt.value)}
                    onClick={() => setPersonalized(personalized === opt.value ? undefined : opt.value)}
                    className={`px-2.5 py-1 text-xs rounded-btn border transition-colors ${
                      personalized === opt.value
                        ? 'border-cyan-500/40 bg-cyan-500/15 text-cyan-400'
                        : 'border-white/10 text-gray-500 hover:text-gray-400'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Advice direction */}
            <div>
              <div className="text-xs text-gray-500 mb-1.5">建议方向</div>
              <div className="flex gap-2">
                {DIRECTION_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setAdviceDirection(adviceDirection === opt.value ? undefined : opt.value)}
                    className={`px-2.5 py-1 text-xs rounded-btn border transition-colors ${
                      adviceDirection === opt.value
                        ? 'border-cyan-500/40 bg-cyan-500/15 text-cyan-400'
                        : 'border-white/10 text-gray-500 hover:text-gray-400'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Notes */}
            <div>
              <div className="text-xs text-gray-500 mb-1.5">备注</div>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="可选备注..."
                className="w-full px-3 py-1.5 text-sm rounded-btn bg-white/5 border border-white/10 text-gray-300 placeholder:text-gray-600 focus:outline-none focus:border-primary-500/40"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit */}
      {selectedLabel && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex justify-end"
        >
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="btn-primary text-sm"
          >
            {submitting ? '提交中...' : '提交评价'}
          </button>
        </motion.div>
      )}
    </motion.div>
  );
}
