import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ErrorToastProps {
  message: string | null;
  onDismiss?: () => void;
  duration?: number;
}

export function ErrorToast({ message, onDismiss, duration = 3000 }: ErrorToastProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (message) {
      setVisible(true);
      const timer = setTimeout(() => {
        setVisible(false);
        onDismiss?.();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [message, duration, onDismiss]);

  return (
    <AnimatePresence>
      {visible && message && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ type: 'spring', bounce: 0.3, duration: 0.4 }}
          className="fixed bottom-6 right-6 z-50 max-w-md"
        >
          <div className="flex items-center gap-3 rounded-card bg-red-500/20 border border-red-500/30 px-4 py-3 backdrop-blur-xl shadow-2xl">
            <span className="text-red-400">⚠️</span>
            <p className="text-sm text-red-200 flex-1">{message}</p>
            <button
              onClick={() => {
                setVisible(false);
                onDismiss?.();
              }}
              className="text-red-400 hover:text-red-300 text-sm"
            >
              ✕
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
