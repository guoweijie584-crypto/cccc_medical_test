import { create } from 'zustand';
import { api, ApiError } from '../api/client';
import { usePatientStore } from './patientStore';

export interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  expertOpinions?: Record<string, string>;
  synthesizedAdvice?: string;
  error?: boolean;
}

interface ChatStore {
  messages: Message[];
  isLoading: boolean;
  error: string | null;

  sendMessage: (query: string) => Promise<void>;
  clearMessages: () => void;
  loadMessages: (patientId: string) => void;
  retryLast: () => Promise<void>;
}

function getStorageKey(patientId: string) {
  return `medical-chat-${patientId}`;
}

function saveToStorage(patientId: string, messages: Message[]) {
  try {
    localStorage.setItem(getStorageKey(patientId), JSON.stringify(messages));
  } catch {
    // localStorage full or unavailable
  }
}

function loadFromStorage(patientId: string): Message[] {
  try {
    const data = localStorage.getItem(getStorageKey(patientId));
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isLoading: false,
  error: null,

  sendMessage: async (query: string) => {
    const patientId = usePatientStore.getState().selectedPatientId;
    if (!patientId) {
      set({ error: '请先选择患者' });
      return;
    }

    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    const currentMessages = [...get().messages, userMsg];
    set({ messages: currentMessages, isLoading: true, error: null });
    saveToStorage(patientId, currentMessages);

    try {
      const data = await api.post<{
        primaryResponse: string;
        expertOpinions?: Record<string, string>;
        mode?: string;
        pendingEvaluationId?: string;
      }>('/api/consultation', {
        patient_id: patientId,
        query,
      });

      const agentMsg: Message = {
        id: `msg-${Date.now()}-agent`,
        role: 'agent',
        content: data.primaryResponse || '',
        timestamp: new Date().toISOString(),
        expertOpinions: data.expertOpinions,
      };

      const updatedMessages = [...currentMessages, agentMsg];
      set({ messages: updatedMessages, isLoading: false });
      saveToStorage(patientId, updatedMessages);
    } catch (err) {
      const errorMsg = err instanceof ApiError ? err.detail : '发送失败，请重试';
      set({ isLoading: false, error: errorMsg });
    }
  },

  clearMessages: () => {
    const patientId = usePatientStore.getState().selectedPatientId;
    set({ messages: [], error: null });
    if (patientId) {
      localStorage.removeItem(getStorageKey(patientId));
    }
  },

  loadMessages: (patientId: string) => {
    const messages = loadFromStorage(patientId);
    set({ messages, error: null });
  },

  retryLast: async () => {
    const msgs = get().messages;
    // Find the last user message
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') {
        await get().sendMessage(msgs[i].content);
        return;
      }
    }
  },
}));
