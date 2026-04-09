import { motion, AnimatePresence } from 'framer-motion';
import { useChatStore, type ConsultationPhase } from '../../stores/chatStore';

const PHASE_CONFIG: Record<ConsultationPhase, { icon: string; label: string }> = {
  pending:             { icon: '📤', label: '正在发送消息...' },
  memory_lookup:       { icon: '🧠', label: '正在查阅患者历史记录...' },
  consulting_experts:  { icon: '👥', label: '正在咨询专家团队...' },
  synthesizing:        { icon: '📝', label: '正在综合专家意见...' },
  complete:            { icon: '✅', label: '会诊完成' },
  error:               { icon: '❌', label: '出现错误' },
};

const ACTOR_TITLES: Record<string, string> = {
  primary: '主治医生',
  pharmacist: '药剂师',
  nutritionist: '营养师',
  doctor: '代谢病医生',
  memory: '记忆管理',
};

const ACTOR_ICONS: Record<string, string> = {
  pharmacist: '💊',
  nutritionist: '🥗',
  doctor: '🏥',
  memory: '🧠',
};

export function ConsultationStatus() {
  const round = useChatStore((s) => s.activeRound);

  if (!round) return null;
  const currentPhase: ConsultationPhase = round.phase;
  if (currentPhase === 'complete') return null;

  const phase = PHASE_CONFIG[currentPhase] || PHASE_CONFIG.pending;
  const isActive = currentPhase !== 'error';
  const expertCount = Object.keys(round.expertOpinions).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex justify-start max-w-4xl mx-auto"
    >
      <div className="glass-panel rounded-2xl rounded-bl-md px-5 py-4 max-w-[75%]">
        {/* Phase indicator */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm text-gray-300">
            <motion.span
              animate={isActive ? { opacity: [0.5, 1, 0.5] } : {}}
              transition={{ duration: 2, repeat: Infinity }}
            >
              {phase.icon}
            </motion.span>
            <span>{phase.label}</span>
          </div>
          {isActive && (
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-primary-400"
                  animate={{
                    scale: [1, 1.5, 1],
                    opacity: [0.4, 1, 0.4],
                  }}
                  transition={{
                    duration: 1.2,
                    repeat: Infinity,
                    delay: i * 0.25,
                    ease: 'easeInOut',
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Active actors */}
        {round.activeActors.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {round.activeActors.map((actorId) => (
              <span
                key={actorId}
                className="inline-flex items-center gap-1 rounded-full bg-primary-500/10
                           border border-primary-500/20 px-2.5 py-0.5 text-xs text-primary-300"
              >
                <motion.span
                  className="inline-block h-1.5 w-1.5 rounded-full bg-primary-400"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                {ACTOR_ICONS[actorId] || '👤'} {ACTOR_TITLES[actorId] || actorId}
              </span>
            ))}
          </div>
        )}

        {/* Expert opinions arriving */}
        <AnimatePresence>
          {expertCount > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-3 space-y-1.5"
            >
              <div className="text-xs text-gray-500">
                已收到 {expertCount} 位专家意见
              </div>
              {Object.entries(round.expertOpinions).map(([actorId, opinion]) => (
                <motion.div
                  key={actorId}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="rounded-lg bg-white/5 px-3 py-2"
                >
                  <div className="text-[11px] text-gray-400 mb-0.5">
                    {ACTOR_ICONS[actorId] || '👤'} {ACTOR_TITLES[actorId] || actorId}
                  </div>
                  <p className="text-xs text-gray-400 line-clamp-2">
                    {opinion.slice(0, 150)}{opinion.length > 150 ? '...' : ''}
                  </p>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error */}
        {round.phase === 'error' && round.error && (
          <p className="mt-2 text-xs text-red-400">{round.error}</p>
        )}
      </div>
    </motion.div>
  );
}
