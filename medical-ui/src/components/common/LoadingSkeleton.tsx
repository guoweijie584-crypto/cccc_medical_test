import { motion } from 'framer-motion';

interface LoadingSkeletonProps {
  lines?: number;
  className?: string;
}

export function LoadingSkeleton({ lines = 3, className = '' }: LoadingSkeletonProps) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <motion.div
          key={i}
          className="h-4 rounded-full bg-white/5"
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            delay: i * 0.15,
          }}
          style={{ width: `${85 - i * 15}%` }}
        />
      ))}
    </div>
  );
}

export function CardSkeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`glass-panel p-4 space-y-3 ${className}`}>
      <motion.div
        className="h-5 w-24 rounded bg-white/5"
        animate={{ opacity: [0.3, 0.6, 0.3] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      />
      <motion.div
        className="h-8 w-16 rounded bg-white/5"
        animate={{ opacity: [0.3, 0.6, 0.3] }}
        transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
      />
    </div>
  );
}
