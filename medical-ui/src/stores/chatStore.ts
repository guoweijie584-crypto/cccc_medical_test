/**
 * Chat Store — SSE-driven async multi-agent consultation
 * Replaces the old synchronous POST /api/consultation flow
 * with CCCC work group integration via SSE streaming.
 */
import { create } from 'zustand';
import { usePatientStore } from './patientStore';
import { api } from '../api/client';
import {
  sendConsultation,
  subscribeLedger,
  getLedgerTail,
  type LedgerEvent,
  type SSESubscription,
  MAIN_GROUP_ID,
} from '../api/ccccClient';

// ─── Types ────────────────────────────────────────────────────────

export interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  actor?: string;
  actorTitle?: string;
  expertOpinions?: Record<string, string>;
  error?: boolean;
}

/** Phase of a multi-agent consultation round */
export type ConsultationPhase =
  | 'pending'
  | 'memory_lookup'
  | 'consulting_experts'
  | 'synthesizing'
  | 'complete'
  | 'error';

export interface ConsultationRound {
  userEventId: string;
  phase: ConsultationPhase;
  activeActors: string[];
  expertOpinions: Record<string, string>;  // actorId → opinion text
  startedAt: number;
  error?: string;
}

interface ChatStore {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;
  activeRound: ConsultationRound | null;
  _subscription: SSESubscription | null;
  _seenEventIds: Set<string>;
  _timeoutTimer: ReturnType<typeof setTimeout> | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  sendMessage: (query: string) => Promise<void>;
  loadHistory: () => Promise<void>;
  clearMessages: () => void;
  loadMessages: (patientId: string) => void;
  retryLast: () => Promise<void>;
}

// ─── Actor Metadata ───────────────────────────────────────────────

const ACTOR_TITLES: Record<string, string> = {
  primary: '主治医生',
  pharmacist: '药剂师',
  nutritionist: '营养师',
  doctor: '代谢病医生',
  memory: '记忆管理',
};

const SPECIALIST_ACTORS = new Set(['pharmacist', 'nutritionist', 'doctor']);

const CONSULTATION_TIMEOUT_MS = 180_000; // 3 minutes

// ─── Event Classification Helpers ─────────────────────────────────

function isChatMessage(event: LedgerEvent): boolean {
  return event.kind === 'chat.message';
}

function getEventText(event: LedgerEvent): string {
  return String(event.data?.text || '').trim();
}

function getEventTo(event: LedgerEvent): string[] {
  const to = event.data?.to;
  if (!Array.isArray(to)) return [];
  return to.map((t) => String(t || '').replace(/^@/, '').trim()).filter(Boolean);
}

function isUserMessage(event: LedgerEvent): boolean {
  return isChatMessage(event) && event.by === 'user';
}

function isPrimaryToUser(event: LedgerEvent): boolean {
  if (!isChatMessage(event) || event.by !== 'primary') return false;
  const to = getEventTo(event);
  // primary → user, or primary → @foreman (since user is foreman in this context)
  return to.includes('user') || to.includes('@foreman') || to.length === 0;
}

function isPrimaryToMemory(event: LedgerEvent): boolean {
  if (!isChatMessage(event) || event.by !== 'primary') return false;
  return getEventTo(event).includes('memory');
}

function isPrimaryToSpecialists(event: LedgerEvent): boolean {
  if (!isChatMessage(event) || event.by !== 'primary') return false;
  const to = getEventTo(event);
  return to.some((t) => SPECIALIST_ACTORS.has(t));
}

function isMemoryReply(event: LedgerEvent): boolean {
  return isChatMessage(event) && event.by === 'memory';
}

function isSpecialistReply(event: LedgerEvent): boolean {
  return isChatMessage(event) && SPECIALIST_ACTORS.has(event.by);
}

// ─── Store ────────────────────────────────────────────────────────

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isLoading: false,
  error: null,
  isConnected: false,
  activeRound: null,
  _subscription: null,
  _seenEventIds: new Set(),
  _timeoutTimer: null,

  connect: () => {
    const state = get();
    // Clean up previous subscription
    if (state._subscription) {
      state._subscription.unsubscribe();
    }

    const subscription = subscribeLedger(
      MAIN_GROUP_ID,
      (event) => {
        handleLedgerEvent(event, set, get);
      },
      (connected) => {
        set({ isConnected: connected });
        // On reconnect, catch up on missed events
        if (connected) {
          get().loadHistory();
        }
      },
    );

    set({ _subscription: subscription, isConnected: true });
  },

  disconnect: () => {
    const state = get();
    if (state._subscription) {
      state._subscription.unsubscribe();
    }
    if (state._timeoutTimer) {
      clearTimeout(state._timeoutTimer);
    }
    set({ _subscription: null, isConnected: false, _timeoutTimer: null });
  },

  loadHistory: async () => {
    try {
      const events = await getLedgerTail(MAIN_GROUP_ID, 200);
      const state = get();
      const newMessages: Message[] = [];
      const seen = new Set(state._seenEventIds);

      for (const event of events) {
        if (seen.has(event.id)) continue;
        seen.add(event.id);

        const msg = eventToMessage(event);
        if (msg) {
          newMessages.push(msg);
        }
      }

      if (newMessages.length > 0) {
        set((s) => ({
          messages: deduplicateMessages([...s.messages, ...newMessages]),
          _seenEventIds: seen,
        }));
      }
    } catch (err) {
      console.error('[ChatStore] Failed to load history:', err);
    }
  },

  sendMessage: async (query: string) => {
    const patientId = usePatientStore.getState().selectedPatientId;
    if (!patientId) {
      set({ error: '请先选择患者' });
      return;
    }

    const patient = usePatientStore.getState().getSelectedPatient();

    // Create optimistic user message
    const tempId = `user-${Date.now()}`;
    const userMsg: Message = {
      id: tempId,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    // Clear previous timeout
    const prevTimer = get()._timeoutTimer;
    if (prevTimer) clearTimeout(prevTimer);

    set((s) => ({
      messages: [...s.messages, userMsg],
      isLoading: true,
      error: null,
      activeRound: {
        userEventId: tempId,
        phase: 'pending',
        activeActors: [],
        expertOpinions: {},
        startedAt: Date.now(),
      },
    }));

    try {
      // Build patient context for the medical_context ref
      const patientContext = patient
        ? {
            patient_id: patientId,
            patient_name: patient.name || 'unknown',
            profile: {
              name: patient.name,
              age: patient.age,
              gender: patient.gender,
              diabetes_type: patient.diabetes_type,
              diagnosis_date: patient.diagnosis_date,
              medications: patient.current_medications || [],
              complications: patient.complications || [],
              glucose_recent: (patient.glucose_records || []).slice(-5),
            },
          }
        : { patient_id: patientId };

      const result = await sendConsultation(query, patientContext);

      // Update the temp ID with real event_id if available
      if (result.event_id) {
        set((s) => {
          const msgs = s.messages.map((m) =>
            m.id === tempId ? { ...m, id: result.event_id! } : m,
          );
          const seenIds = new Set(s._seenEventIds);
          seenIds.add(result.event_id!);
          return {
            messages: msgs,
            _seenEventIds: seenIds,
            activeRound: s.activeRound
              ? { ...s.activeRound, userEventId: result.event_id! }
              : null,
          };
        });
      }

      // Set consultation timeout
      const timeoutTimer = setTimeout(() => {
        const current = get();
        if (current.activeRound && current.activeRound.phase !== 'complete') {
          set({
            isLoading: false,
            error: '会诊响应超时，专家团队可能仍在处理中。',
            activeRound: {
              ...current.activeRound,
              phase: 'error',
              error: '响应超时',
            },
          });
        }
      }, CONSULTATION_TIMEOUT_MS);

      set({ _timeoutTimer: timeoutTimer });
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : '发送失败，请检查协作系统连接';
      set((s) => ({
        isLoading: false,
        error: errorMsg,
        activeRound: s.activeRound
          ? { ...s.activeRound, phase: 'error', error: errorMsg }
          : null,
      }));
    }
  },

  clearMessages: () => {
    const state = get();
    if (state._timeoutTimer) clearTimeout(state._timeoutTimer);
    set({
      messages: [],
      error: null,
      activeRound: null,
      isLoading: false,
      _seenEventIds: new Set(),
      _timeoutTimer: null,
    });
  },

  loadMessages: (_patientId: string) => {
    // Clear current state and load from ledger
    set({ messages: [], _seenEventIds: new Set() });
    get().loadHistory();
  },

  retryLast: async () => {
    const msgs = get().messages;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') {
        await get().sendMessage(msgs[i].content);
        return;
      }
    }
  },
}));

// ─── Event → Message conversion ───────────────────────────────────

function eventToMessage(event: LedgerEvent): Message | null {
  if (!isChatMessage(event)) return null;

  const text = getEventText(event);
  if (!text) return null;

  // User messages
  if (isUserMessage(event)) {
    return {
      id: event.id,
      role: 'user',
      content: text,
      timestamp: event.ts,
    };
  }

  // Primary → user (final response)
  if (isPrimaryToUser(event)) {
    return {
      id: event.id,
      role: 'agent',
      content: text,
      timestamp: event.ts,
      actor: 'primary',
      actorTitle: ACTOR_TITLES.primary,
    };
  }

  // We don't add internal messages (specialist opinions, memory queries) to the main message list.
  // They are tracked in the active round and shown in the ExpertOpinions panel.
  return null;
}

// ─── Live Event Handler ───────────────────────────────────────────

function handleLedgerEvent(
  event: LedgerEvent,
  set: (fn: ((s: ChatStore) => Partial<ChatStore>) | Partial<ChatStore>) => void,
  get: () => ChatStore,
) {
  const state = get();

  // Skip already seen events
  if (state._seenEventIds.has(event.id)) return;

  // Track seen
  const newSeen = new Set(state._seenEventIds);
  newSeen.add(event.id);

  // Only process chat.message events
  if (!isChatMessage(event)) {
    set({ _seenEventIds: newSeen });
    return;
  }

  const text = getEventText(event);
  if (!text) {
    set({ _seenEventIds: newSeen });
    return;
  }

  // --- User messages (from SSE — in case someone else sent it) ---
  if (isUserMessage(event)) {
    // Check if we already have this message (optimistic add)
    const existingIdx = state.messages.findIndex(
      (m) => m.role === 'user' && m.content === text && !state._seenEventIds.has(event.id),
    );
    if (existingIdx === -1) {
      const msg: Message = {
        id: event.id,
        role: 'user',
        content: text,
        timestamp: event.ts,
      };
      set((s) => ({
        messages: [...s.messages, msg],
        _seenEventIds: newSeen,
      }));
    } else {
      set({ _seenEventIds: newSeen });
    }
    return;
  }

  // --- Primary → user (final synthesized response) ---
  if (isPrimaryToUser(event)) {
    const round = state.activeRound;
    const expertOpinions = round?.expertOpinions || {};

    const msg: Message = {
      id: event.id,
      role: 'agent',
      content: text,
      timestamp: event.ts,
      actor: 'primary',
      actorTitle: ACTOR_TITLES.primary,
      expertOpinions: Object.keys(expertOpinions).length > 0 ? { ...expertOpinions } : undefined,
    };

    // Clear timeout
    const timer = state._timeoutTimer;
    if (timer) clearTimeout(timer);

    set((s) => ({
      messages: [...s.messages, msg],
      isLoading: false,
      activeRound: null, // Round is done — null it out to prevent post-reply events from re-activating loading
      _seenEventIds: newSeen,
      _timeoutTimer: null,
    }));

    // Auto-create pending evaluation record (线1→线3 bridge)
    // Find the user query that triggered this consultation round
    const userQuery = findLastUserQuery(state.messages);
    if (userQuery) {
      const patientId = usePatientStore.getState().selectedPatientId;
      if (patientId) {
        api.post('/api/evaluations/pending', {
          patient_id: patientId,
          query: userQuery,
          response: text,
          expert_opinions: expertOpinions,
        }).catch(() => {
          // Non-critical — don't break chat flow
          console.warn('[ChatStore] Failed to create pending evaluation (non-critical)');
        });
      }
    }

    return;
  }

  // --- Primary → memory (memory lookup phase) ---
  if (isPrimaryToMemory(event)) {
    set((s) => ({
      activeRound: s.activeRound
        ? {
            ...s.activeRound,
            phase: 'memory_lookup',
            activeActors: addUnique(s.activeRound.activeActors, 'memory'),
          }
        : null,
      _seenEventIds: newSeen,
    }));
    return;
  }

  // --- Memory → primary (memory replied, moving to specialist phase) ---
  if (isMemoryReply(event)) {
    set((s) => ({
      activeRound: s.activeRound
        ? {
            ...s.activeRound,
            phase: 'consulting_experts',
            activeActors: s.activeRound.activeActors.filter((a) => a !== 'memory'),
          }
        : null,
      _seenEventIds: newSeen,
    }));
    return;
  }

  // --- Primary → specialists (consulting phase) ---
  if (isPrimaryToSpecialists(event)) {
    const to = getEventTo(event);
    set((s) => ({
      activeRound: s.activeRound
        ? {
            ...s.activeRound,
            phase: 'consulting_experts',
            activeActors: addUniqueAll(
              s.activeRound.activeActors,
              to.filter((t) => SPECIALIST_ACTORS.has(t)),
            ),
          }
        : null,
      _seenEventIds: newSeen,
    }));
    return;
  }

  // --- Specialist replies (collect expert opinions) ---
  if (isSpecialistReply(event)) {
    const actorId = event.by;
    set((s) => ({
      activeRound: s.activeRound
        ? {
            ...s.activeRound,
            phase: 'consulting_experts',
            activeActors: s.activeRound.activeActors.filter((a) => a !== actorId),
            expertOpinions: {
              ...s.activeRound.expertOpinions,
              [actorId]: text,
            },
          }
        : null,
      _seenEventIds: newSeen,
    }));
    return;
  }

  // Other internal messages — just track as seen
  set({ _seenEventIds: newSeen });
}

// ─── Helpers ──────────────────────────────────────────────────────

function addUnique(arr: string[], item: string): string[] {
  return arr.includes(item) ? arr : [...arr, item];
}

function addUniqueAll(arr: string[], items: string[]): string[] {
  const result = [...arr];
  for (const item of items) {
    if (!result.includes(item)) result.push(item);
  }
  return result;
}

function deduplicateMessages(messages: Message[]): Message[] {
  const seen = new Set<string>();
  return messages.filter((m) => {
    if (seen.has(m.id)) return false;
    seen.add(m.id);
    return true;
  });
}

/** Find the last user message text from the messages array */
function findLastUserQuery(messages: Message[]): string | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'user') return messages[i].content;
  }
  return null;
}
