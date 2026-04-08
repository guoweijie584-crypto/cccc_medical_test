import { create } from 'zustand';
import { api, ApiError } from '../api/client';
import { usePatientStore } from './patientStore';

export type EvalLabel = 'GOOD' | 'BAD' | 'NEUTRAL' | 'ERROR';
export type SafetyLevel = 'safe' | 'risky' | 'dangerous';
export type AdviceDirection = 'correct' | 'partial' | 'wrong';

export interface PendingEvaluation {
  id: string;
  patient_id: string;
  query: string;
  response: string;
  expert_opinions?: Record<string, string>;
  created_at: string;
}

export interface CompletedEvaluation extends PendingEvaluation {
  label: EvalLabel;
  safety?: SafetyLevel;
  personalized?: boolean;
  advice_direction?: AdviceDirection;
  reviewer_notes?: string;
  evaluated_at: string;
}

export interface EvalStats {
  total: number;
  good: number;
  bad: number;
  neutral: number;
  error: number;
  good_rate: number;
  pending_count: number;
  attention_count: number;
}

export interface EvolutionReport {
  last_run?: string;
  bad_count: number;
  prompt_optimizations: number;
  memory_reinforcements: number;
  summary?: string;
}

interface EvaluationStore {
  pending: PendingEvaluation[];
  history: CompletedEvaluation[];
  stats: EvalStats | null;
  evolutionReport: EvolutionReport | null;
  loading: boolean;
  error: string | null;

  fetchPending: () => Promise<void>;
  fetchHistory: (label?: EvalLabel) => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchEvolutionReport: () => Promise<void>;
  submitEvaluation: (
    id: string,
    data: {
      label: EvalLabel;
      safety?: SafetyLevel;
      personalized?: boolean;
      advice_direction?: AdviceDirection;
      reviewer_notes?: string;
    },
  ) => Promise<boolean>;
  triggerEvolution: () => Promise<boolean>;
}

export const useEvaluationStore = create<EvaluationStore>((set, get) => ({
  pending: [],
  history: [],
  stats: null,
  evolutionReport: null,
  loading: false,
  error: null,

  fetchPending: async () => {
    const patientId = usePatientStore.getState().selectedPatientId;
    set({ loading: true, error: null });
    try {
      const params = patientId ? `?patient_id=${patientId}` : '';
      const data = await api.get<{ evaluations: PendingEvaluation[] }>(
        `/api/evaluations/pending${params}`,
      );
      set({ pending: data.evaluations || [], loading: false });
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : '加载待评价列表失败';
      set({ loading: false, error: msg });
    }
  },

  fetchHistory: async (label?: EvalLabel) => {
    try {
      const params = label ? `?label=${label}` : '';
      const data = await api.get<{ evaluations: CompletedEvaluation[] }>(
        `/api/evaluations/bad${params}`,
      );
      set({ history: data.evaluations || [] });
    } catch {
      // non-critical
    }
  },

  fetchStats: async () => {
    const patientId = usePatientStore.getState().selectedPatientId;
    try {
      const params = patientId ? `?patient_id=${patientId}` : '';
      const data = await api.get<EvalStats>(`/api/evaluations/stats${params}`);
      set({ stats: data });
    } catch {
      // non-critical
    }
  },

  fetchEvolutionReport: async () => {
    try {
      const data = await api.get<EvolutionReport>('/api/evolution/report');
      set({ evolutionReport: data });
    } catch {
      // non-critical
    }
  },

  submitEvaluation: async (id, data) => {
    try {
      await api.post(`/api/evaluations/${id}/submit`, data);
      // Refresh pending and stats
      await get().fetchPending();
      await get().fetchStats();
      return true;
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : '提交评价失败';
      set({ error: msg });
      return false;
    }
  },

  triggerEvolution: async () => {
    try {
      await api.post('/api/evolution/human-driven');
      await get().fetchEvolutionReport();
      return true;
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : '触发优化失败';
      set({ error: msg });
      return false;
    }
  },
}));
