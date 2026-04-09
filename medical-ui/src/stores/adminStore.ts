import { create } from 'zustand';
import { api, ApiError } from '../api/client';
import type { EvalStats } from './evaluationStore';

// ─── Types ────────────────────────────────────────────────────────

export type ServiceStatus = 'healthy' | 'degraded' | 'down' | 'unknown';

export interface HealthCheck {
  api: ServiceStatus;
  memory_palace: ServiceStatus;
  llm_mode: string; // 'mock' | 'llm' | ...
  version?: string;
  uptime?: string;
}

export interface ErrorEntry {
  trace_id: string;
  timestamp: string;
  message: string;
  severity: 'error' | 'warning';
  patient_id?: string;
}

export interface EvolutionResult {
  success: boolean;
  message: string;
  timestamp?: string;
}

// ─── Mock Data ────────────────────────────────────────────────────

const MOCK_HEALTH: HealthCheck = {
  api: 'healthy',
  memory_palace: 'healthy',
  llm_mode: 'mock',
  version: '0.1.0',
  uptime: '2d 14h 32m',
};

const MOCK_ERRORS: ErrorEntry[] = [
  {
    trace_id: 'trace-003',
    timestamp: '2026-04-08T16:45:00Z',
    message: '营养师专家超时未响应（>30s）',
    severity: 'warning',
    patient_id: 'patient-demo-002',
  },
  {
    trace_id: 'trace-005',
    timestamp: '2026-04-07T11:00:00Z',
    message: 'LLM 服务返回空响应，已触发 mock 兜底',
    severity: 'error',
    patient_id: 'patient-demo-003',
  },
  {
    trace_id: 'trace-007',
    timestamp: '2026-04-06T09:20:00Z',
    message: '安全审查模块加载超时，使用默认规则',
    severity: 'warning',
  },
];

// ─── Store ────────────────────────────────────────────────────────

interface AdminStore {
  health: HealthCheck | null;
  evalStats: EvalStats | null;
  recentErrors: ErrorEntry[];
  loading: boolean;
  error: string | null;
  evolutionResult: EvolutionResult | null;
  evolutionLoading: boolean;

  fetchHealth: () => Promise<void>;
  fetchEvalStats: () => Promise<void>;
  fetchRecentErrors: () => Promise<void>;
  triggerEvolution: () => Promise<void>;
  clearEvolutionResult: () => void;
}

export const useAdminStore = create<AdminStore>((set) => ({
  health: null,
  evalStats: null,
  recentErrors: [],
  loading: false,
  error: null,
  evolutionResult: null,
  evolutionLoading: false,

  fetchHealth: async () => {
    try {
      const data = await api.get<Record<string, unknown>>('/api/health');
      const health: HealthCheck = {
        api: 'healthy',
        memory_palace: (data.memory_status as ServiceStatus) || 'unknown',
        llm_mode: (data.llm_mode as string) || (data.mode as string) || 'unknown',
        version: (data.version as string) || undefined,
        uptime: (data.uptime as string) || undefined,
      };
      set({ health });
    } catch {
      // Fallback to mock
      console.warn('[AdminStore] Health API not available, using mock data');
      set({ health: MOCK_HEALTH });
    }
  },

  fetchEvalStats: async () => {
    try {
      const data = await api.get<Record<string, unknown>>('/api/evaluations/stats');
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
      set({ evalStats: stats });
    } catch {
      // Fallback to mock
      set({
        evalStats: {
          total: 47,
          good: 32,
          bad: 5,
          neutral: 8,
          error: 2,
          good_rate: 0.68,
          pending_count: 6,
          attention_count: 3,
        },
      });
    }
  },

  fetchRecentErrors: async () => {
    try {
      const data = await api.get<{ errors: ErrorEntry[] }>('/api/admin/errors');
      set({ recentErrors: data.errors || [] });
    } catch {
      // Fallback to mock
      set({ recentErrors: MOCK_ERRORS });
    }
  },

  triggerEvolution: async () => {
    set({ evolutionLoading: true, error: null });
    try {
      const data = await api.post<Record<string, unknown>>('/api/evolution/human-driven');
      set({
        evolutionLoading: false,
        evolutionResult: {
          success: true,
          message: (data.message as string) || '优化流程已触发',
          timestamp: new Date().toISOString(),
        },
      });
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : '触发优化失败';
      set({
        evolutionLoading: false,
        evolutionResult: {
          success: false,
          message: msg,
        },
      });
    }
  },

  clearEvolutionResult: () => set({ evolutionResult: null }),
}));
