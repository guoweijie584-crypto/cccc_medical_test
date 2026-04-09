import { create } from 'zustand';
import { api, ApiError } from '../api/client';
import { sendEvaluation, triggerEvalEvolution, CcccApiError } from '../api/ccccClient';
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
  summary?: string | Record<string, unknown>;
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
      // Backend returns evaluation_id, frontend interface uses id — normalize
      const normalized = (data.evaluations || []).map((e: any) => ({
        ...e,
        id: e.id || e.evaluation_id || '',
        created_at: e.created_at || e.consultation_timestamp || '',
      }));
      set({ pending: normalized, loading: false });
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
      const data = await api.get<Record<string, unknown>>(`/api/evaluations/stats${params}`);
      // Backend returns: { total, good, bad, neutral, error, pending, good_rate, needs_attention }
      // Frontend expects: { total, good, bad, neutral, error, good_rate, pending_count, attention_count }
      const stats: EvalStats = {
        total: (data.total as number) || 0,
        good: (data.good as number) || 0,
        bad: (data.bad as number) || 0,
        neutral: (data.neutral as number) || 0,
        error: (data.error as number) || 0,
        good_rate: (data.good_rate as number) || 0,
        pending_count: (data.pending_count as number) ?? (data.pending as number) ?? 0,
        attention_count: (data.attention_count as number) ?? (data.needs_attention as number) ?? 0,
      };
      set({ stats });
    } catch {
      // non-critical
    }
  },

  fetchEvolutionReport: async () => {
    try {
      const data = await api.get<Record<string, unknown>>('/api/evolution/report');
      // Backend returns { summary: { initialScore, ... }, iterations, exportDir }
      // Normalize to EvolutionReport shape
      const summary = data.summary;
      const summaryObj = (typeof summary === 'object' && summary !== null) ? summary as Record<string, unknown> : {};
      const iterations = Array.isArray(data.iterations) ? data.iterations : [];
      const lastIteration = iterations.length > 0 ? iterations[iterations.length - 1] : null;
      const report: EvolutionReport = {
        last_run: lastIteration?.timestamp as string | undefined,
        bad_count: 0,
        prompt_optimizations: (summaryObj.promptVersions as Record<string, number>)?.primary || 0,
        memory_reinforcements: (summaryObj.memoryOperations as Record<string, number>)?.add || 0,
        summary: typeof summary === 'string' ? summary : `评分: ${summaryObj.initialScore ?? '?'} → ${summaryObj.finalScore ?? '?'} (${summaryObj.mode || 'unknown'})`,
      };
      set({ evolutionReport: report });
    } catch {
      // non-critical
    }
  },

  submitEvaluation: async (id, data) => {
    try {
      await api.post(`/api/evaluations/${id}/submit`, data);

      // Also notify CCCC eval work group (fire-and-forget for the CCCC part)
      const patientId = usePatientStore.getState().selectedPatientId;
      // Find the evaluation to get query text
      const evaluation = get().pending.find((e) => e.id === id);
      try {
        await sendEvaluation(id, {
          label: data.label,
          patient_id: patientId || '',
          query: evaluation?.query || '',
          safety: data.safety,
          personalized: data.personalized,
          advice_direction: data.advice_direction,
          reviewer_notes: data.reviewer_notes,
        });
      } catch {
        // CCCC notification is non-critical — don't block the UI
        console.warn('[eval] CCCC eval group notification failed (non-critical)');
      }

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
      // 1. Call the REST API for immediate optimization
      await api.post('/api/evolution/human-driven');

      // 2. Also notify CCCC eval work group to trigger its own cycle
      try {
        await triggerEvalEvolution();
      } catch {
        // CCCC notification is non-critical
        console.warn('[eval] CCCC eval group evolution trigger failed (non-critical)');
      }

      await get().fetchEvolutionReport();
      return true;
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : '触发优化失败';
      set({ error: msg });
      return false;
    }
  },
}));
