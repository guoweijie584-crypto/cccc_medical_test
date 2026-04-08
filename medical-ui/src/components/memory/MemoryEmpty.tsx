import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

interface MemoryEmptyProps {
  onCreateClick: () => void;
}

export function MemoryEmpty({ onCreateClick }: MemoryEmptyProps) {
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center h-full text-center px-6"
    >
      {/* Cosmic empty state */}
      <div className="relative mb-6">
        <motion.div
          className="text-7xl"
          animate={{ scale: [1, 1.05, 1], opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          🌌
        </motion.div>
        <motion.div
          className="absolute -top-2 -right-2 text-2xl"
          animate={{ rotate: [0, 15, -15, 0] }}
          transition={{ duration: 4, repeat: Infinity }}
        >
          ✨
        </motion.div>
      </div>

      <h2 className="text-xl font-semibold text-gray-300 mb-2">记忆宫殿尚为空白</h2>
      <p className="text-gray-500 max-w-sm mb-6 text-sm leading-relaxed">
        开始和AI助手对话后，系统将自动为您积累健康记忆。您也可以手动添加记忆。
      </p>

      <div className="flex gap-3">
        <button onClick={() => navigate('/')} className="btn-primary text-sm">
          开始对话
        </button>
        <button onClick={onCreateClick} className="btn-ghost text-sm border border-white/10">
          手动添加
        </button>
      </div>
    </motion.div>
  );
}
