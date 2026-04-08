import { motion } from 'framer-motion';

export function AgentTyping() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex justify-start max-w-4xl mx-auto"
    >
      <div className="glass-panel rounded-2xl rounded-bl-md px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <motion.span
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              🧠
            </motion.span>
            <span>正在思考</span>
          </div>
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
        </div>
        <motion.div
          className="mt-2 text-xs text-gray-500"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2 }}
        >
          多位专家正在协作分析您的问题...
        </motion.div>
      </div>
    </motion.div>
  );
}
