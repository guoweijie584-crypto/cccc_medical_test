import { useState } from 'react';
import { motion } from 'framer-motion';

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
  placeholder?: string;
}

export function MessageInput({ onSend, disabled, isLoading, placeholder }: MessageInputProps) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled || isLoading) return;
    onSend(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-white/5 bg-surface-900/60 backdrop-blur-sm p-4">
      <div className="flex items-end gap-3 max-w-4xl mx-auto">
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder || '输入您的健康问题...'}
            disabled={disabled || isLoading}
            rows={1}
            className="w-full resize-none rounded-xl bg-surface-800 border border-white/10 px-4 py-3
                       text-sm text-gray-200 placeholder-gray-500
                       focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/20
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200"
            style={{ minHeight: '44px', maxHeight: '120px' }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = Math.min(target.scrollHeight, 120) + 'px';
            }}
          />
        </div>
        <motion.button
          onClick={handleSend}
          disabled={disabled || isLoading || !input.trim()}
          whileTap={{ scale: 0.95 }}
          className="btn-primary flex items-center gap-2 py-3 px-5 rounded-xl"
        >
          {isLoading ? (
            <motion.div
              className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
            />
          ) : (
            <span>发送</span>
          )}
        </motion.button>
      </div>
    </div>
  );
}
