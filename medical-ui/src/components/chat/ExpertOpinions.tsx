import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ExpertOpinionsProps {
  opinions: Record<string, string>;
}

const EXPERT_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  pharmacist: { icon: '💊', label: '药剂师', color: 'text-blue-400' },
  nutritionist: { icon: '🥗', label: '营养师', color: 'text-green-400' },
  doctor: { icon: '🏥', label: '代谢医生', color: 'text-purple-400' },
};

function getExpertConfig(key: string) {
  // Try exact match first
  if (EXPERT_CONFIG[key]) return EXPERT_CONFIG[key];
  // Fuzzy match
  if (key.includes('药') || key.includes('pharmacist')) return EXPERT_CONFIG.pharmacist;
  if (key.includes('营养') || key.includes('nutrition')) return EXPERT_CONFIG.nutritionist;
  if (key.includes('代谢') || key.includes('doctor') || key.includes('医')) return EXPERT_CONFIG.doctor;
  return { icon: '👨‍⚕️', label: key, color: 'text-gray-400' };
}

export function ExpertOpinions({ opinions }: ExpertOpinionsProps) {
  const [expanded, setExpanded] = useState(false);
  const entries = Object.entries(opinions).filter(([, v]) => v.trim());

  if (entries.length === 0) return null;

  return (
    <div className="mt-3 border-t border-white/10 pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-primary-400 hover:text-primary-300 transition-colors group"
      >
        <motion.span
          animate={{ rotate: expanded ? 90 : 0 }}
          transition={{ duration: 0.2 }}
          className="inline-block"
        >
          ▸
        </motion.span>
        <span>{expanded ? '收起专家意见' : '查看专家详细意见'}</span>
        <span className="text-gray-600 group-hover:text-gray-500">({entries.length})</span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-2">
              {entries.map(([expert, opinion]) => {
                const config = getExpertConfig(expert);
                return (
                  <motion.div
                    key={expert}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2 }}
                    className="rounded-lg bg-white/5 px-3 py-2.5"
                  >
                    <div className={`text-xs font-medium mb-1 ${config.color}`}>
                      {config.icon} {config.label}
                    </div>
                    <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                      {opinion}
                    </p>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
