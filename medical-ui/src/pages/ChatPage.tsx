import { useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChatStore } from '../stores/chatStore';
import { usePatientStore } from '../stores/patientStore';
import { MessageBubble } from '../components/chat/MessageBubble';
import { MessageInput } from '../components/chat/MessageInput';
import { AgentTyping } from '../components/chat/AgentTyping';
import { ErrorToast } from '../components/common/ErrorToast';

export function ChatPage() {
  const { messages, isLoading, error, sendMessage, loadMessages, clearMessages } = useChatStore();
  const selectedPatientId = usePatientStore((s) => s.selectedPatientId);
  const patient = usePatientStore((s) => s.getSelectedPatient());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedPatientId) {
      loadMessages(selectedPatientId);
    }
  }, [selectedPatientId, loadMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = useCallback(
    async (query: string) => {
      await sendMessage(query);
    },
    [sendMessage],
  );

  return (
    <div className="flex h-full flex-col">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          {patient && (
            <>
              <span className="text-primary-400">●</span>
              <span>{patient.name}</span>
              <span className="text-gray-600">·</span>
              <span>{patient.age}岁</span>
              <span className="text-gray-600">·</span>
              <span>{patient.diabetes_type}</span>
            </>
          )}
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="text-xs text-gray-500 hover:text-gray-400 transition-colors"
          >
            清空对话
          </button>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && !isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col items-center justify-center h-full text-center"
          >
            <motion.div
              className="text-6xl mb-6"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            >
              🏥
            </motion.div>
            <h2 className="text-xl font-semibold text-gray-200 mb-3">
              血糖管理智能助手
            </h2>
            <p className="text-gray-500 max-w-md leading-relaxed">
              {patient
                ? `${patient.name}，您好！我是您的专属血糖管理助手。您可以问我关于血糖控制、用药、饮食、运动等问题。`
                : '请先在左侧选择患者，然后开始对话咨询。'}
            </p>
            {patient && (
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {['我的血糖控制得怎么样？', '饮食方面有什么建议？', '需要调整用药吗？'].map(
                  (suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => handleSend(suggestion)}
                      className="px-3 py-1.5 rounded-full text-xs text-primary-400 border border-primary-500/30
                                 hover:bg-primary-500/10 transition-all duration-200"
                    >
                      {suggestion}
                    </button>
                  ),
                )}
              </div>
            )}
          </motion.div>
        )}

        <AnimatePresence>
          {messages.map((msg, i) => (
            <MessageBubble key={msg.id} message={msg} index={i} />
          ))}
        </AnimatePresence>

        <AnimatePresence>{isLoading && <AgentTyping />}</AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <MessageInput
        onSend={handleSend}
        disabled={!selectedPatientId}
        isLoading={isLoading}
        placeholder={selectedPatientId ? '输入您的健康问题...' : '请先选择患者'}
      />

      <ErrorToast message={error} />
    </div>
  );
}
