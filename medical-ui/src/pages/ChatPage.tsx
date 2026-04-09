import { useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChatStore } from '../stores/chatStore';
import { usePatientStore } from '../stores/patientStore';
import { MessageBubble } from '../components/chat/MessageBubble';
import { MessageInput } from '../components/chat/MessageInput';
import { ConsultationStatus } from '../components/chat/ConsultationStatus';
import { SystemStatusBanner } from '../components/common/SystemStatusBanner';
import { ErrorToast } from '../components/common/ErrorToast';

export function ChatPage() {
  const messages = useChatStore((s) => s.messages);
  const isLoading = useChatStore((s) => s.isLoading);
  const error = useChatStore((s) => s.error);
  const activeRound = useChatStore((s) => s.activeRound);
  const isConnected = useChatStore((s) => s.isConnected);
  const { sendMessage, clearMessages, connect, disconnect, loadHistory } = useChatStore();

  const selectedPatientId = usePatientStore((s) => s.selectedPatientId);
  const patient = usePatientStore((s) => s.getSelectedPatient());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Connect to CCCC SSE on mount
  useEffect(() => {
    connect();
    loadHistory();
    return () => disconnect();
  }, [connect, disconnect, loadHistory]);

  // Reload history when patient changes
  useEffect(() => {
    if (selectedPatientId) {
      // For now, we show all messages from the group ledger.
      // Future: filter by patient_id binding
      loadHistory();
    }
  }, [selectedPatientId, loadHistory]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, activeRound]);

  const handleSend = useCallback(
    async (query: string) => {
      await sendMessage(query);
    },
    [sendMessage],
  );

  const isConsulting = activeRound != null
    && activeRound.phase !== 'complete'
    && activeRound.phase !== 'error';

  return (
    <div className="flex h-full flex-col">
      {/* System health banner */}
      <SystemStatusBanner />

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
          {/* Connection indicator */}
          <span className="ml-auto flex items-center gap-1 text-xs">
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${
                isConnected ? 'bg-green-400' : 'bg-red-400'
              }`}
            />
            <span className={isConnected ? 'text-green-500' : 'text-red-400'}>
              {isConnected ? '已连接' : '未连接'}
            </span>
          </span>
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
                ? `${patient.name}，您好！我是您的专属血糖管理助手。多位AI专家将协作为您提供专业建议。`
                : '请先在左侧选择患者，然后开始对话咨询。'}
            </p>
            <p className="text-xs text-gray-600 mt-2">
              由 Claude Code 多 Agent 协作驱动
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

        {/* Multi-agent consultation progress */}
        <AnimatePresence>
          {isConsulting && <ConsultationStatus />}
        </AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <MessageInput
        onSend={handleSend}
        disabled={!selectedPatientId || isConsulting}
        isLoading={isConsulting}
        placeholder={
          !selectedPatientId
            ? '请先选择患者'
            : isConsulting
              ? '专家团队正在协作中...'
              : '输入您的健康问题...'
        }
      />

      <ErrorToast message={error} />
    </div>
  );
}
