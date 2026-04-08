import { useState } from 'react';
import { motion } from 'framer-motion';
import { Message } from '../../stores/chatStore';
import { MarkdownContent } from './MarkdownContent';
import { ExpertOpinions } from './ExpertOpinions';

interface MessageBubbleProps {
  message: Message;
  index: number;
  onRetry?: () => void;
}

export function MessageBubble({ message, index, onRetry }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.3), duration: 0.3, ease: 'easeOut' }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} max-w-4xl mx-auto`}
    >
      {/* Agent avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-600/20 border border-primary-500/30 flex items-center justify-center mr-3 mt-1">
          <span className="text-sm">🤖</span>
        </div>
      )}

      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 shadow-lg ${
          isUser
            ? 'bg-primary-600 text-white rounded-br-md shadow-primary-600/20'
            : 'glass-panel rounded-bl-md'
        }`}
      >
        {/* Message content */}
        {isUser ? (
          <div className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</div>
        ) : (
          <MarkdownContent
            content={message.content}
            className="text-sm leading-relaxed text-gray-200"
          />
        )}

        {/* Expert opinions (agent messages only) */}
        {!isUser && message.expertOpinions && Object.keys(message.expertOpinions).length > 0 && (
          <ExpertOpinions opinions={message.expertOpinions} />
        )}

        {/* Error state with retry */}
        {message.error && (
          <div className="mt-2 flex items-center gap-2">
            <span className="text-xs text-red-400">发送失败</span>
            {onRetry && (
              <button
                onClick={onRetry}
                className="text-xs text-primary-400 hover:text-primary-300 underline"
              >
                重试
              </button>
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className={`mt-1.5 text-[10px] ${isUser ? 'text-primary-200/60' : 'text-gray-500'}`}>
          {new Date(message.timestamp).toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-500/20 border border-accent-500/30 flex items-center justify-center ml-3 mt-1">
          <span className="text-sm">👤</span>
        </div>
      )}
    </motion.div>
  );
}
