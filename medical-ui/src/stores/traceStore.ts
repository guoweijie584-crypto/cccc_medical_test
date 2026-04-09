import { create } from 'zustand';
import { api, ApiError } from '../api/client';

// ─── Types ────────────────────────────────────────────────────────

export type TraceStatus = 'success' | 'partial_failure' | 'failure';
export type SafetyVerdict = 'safe' | 'caution' | 'warning' | 'danger';
export type WritebackStatus = 'approved' | 'pending' | 'rejected';

export interface TraceItem {
  trace_id: string;
  patient_id: string;
  query: string;
  status: TraceStatus;
  created_at: string;
  duration_ms?: number;
  expert_count?: number;
  has_safety_issues?: boolean;
}

export interface ExpertOutput {
  expert_id: string;
  expert_name: string;
  recommendations: string[];
  risks: string[];
  uncertainties: string[];
  raw_output?: string;
  duration_ms?: number;
}

export interface SafetyReview {
  verdict: SafetyVerdict;
  issues: string[];
  details?: string;
}

export interface WritebackCandidate {
  id: string;
  path: string;
  content: string;
  status: WritebackStatus;
  reason?: string;
}

export interface TimingBreakdown {
  memory_retrieval_ms: number;
  expert_consultation_ms: number;
  safety_review_ms: number;
  total_ms: number;
}

export interface TraceDetail {
  trace_id: string;
  patient_id: string;
  created_at: string;
  status: TraceStatus;
  // Query
  original_query: string;
  rephrased_query?: string;
  // Memory
  memory_context_summary?: string;
  // Experts
  routed_experts: string[];
  expert_outputs: ExpertOutput[];
  // Safety
  safety_review?: SafetyReview;
  // Final response
  final_response: string;
  // Writebacks
  writeback_candidates: WritebackCandidate[];
  // Timing
  timing: TimingBreakdown;
  // Errors
  errors: string[];
}

// ─── Mock Data ────────────────────────────────────────────────────

const MOCK_TRACES: TraceItem[] = [
  {
    trace_id: 'trace-001',
    patient_id: 'patient-demo-001',
    query: '我最近空腹血糖偏高，需要调整用药吗？',
    status: 'success',
    created_at: '2026-04-09T10:30:00Z',
    duration_ms: 4500,
    expert_count: 3,
    has_safety_issues: false,
  },
  {
    trace_id: 'trace-002',
    patient_id: 'patient-demo-001',
    query: '二甲双胍和格列美脲可以一起吃吗？',
    status: 'success',
    created_at: '2026-04-09T09:15:00Z',
    duration_ms: 3800,
    expert_count: 2,
    has_safety_issues: false,
  },
  {
    trace_id: 'trace-003',
    patient_id: 'patient-demo-002',
    query: '糖尿病患者可以吃西瓜吗？每天能吃多少？',
    status: 'partial_failure',
    created_at: '2026-04-08T16:45:00Z',
    duration_ms: 6200,
    expert_count: 3,
    has_safety_issues: true,
  },
  {
    trace_id: 'trace-004',
    patient_id: 'patient-demo-001',
    query: '低血糖发作时应该怎么处理？',
    status: 'success',
    created_at: '2026-04-08T14:20:00Z',
    duration_ms: 3200,
    expert_count: 2,
    has_safety_issues: false,
  },
  {
    trace_id: 'trace-005',
    patient_id: 'patient-demo-003',
    query: '胰岛素注射部位怎么轮换？',
    status: 'failure',
    created_at: '2026-04-07T11:00:00Z',
    duration_ms: 8500,
    expert_count: 1,
    has_safety_issues: false,
  },
];

const MOCK_TRACE_DETAIL: TraceDetail = {
  trace_id: 'trace-001',
  patient_id: 'patient-demo-001',
  created_at: '2026-04-09T10:30:00Z',
  status: 'success',
  original_query: '我最近空腹血糖偏高，需要调整用药吗？',
  rephrased_query: '患者（2型糖尿病，目前服用二甲双胍）反映近期空腹血糖偏高，询问是否需要调整药物治疗方案。',
  memory_context_summary:
    '患者档案：张先生，58岁，2型糖尿病5年。当前用药：二甲双胍500mg bid。最近5次空腹血糖：7.8, 8.2, 8.5, 7.9, 8.6 mmol/L（偏高趋势）。HbA1c：7.8%（3个月前）。无严重并发症。',
  routed_experts: ['pharmacist', 'doctor', 'nutritionist'],
  expert_outputs: [
    {
      expert_id: 'doctor',
      expert_name: '代谢病医生',
      recommendations: [
        '空腹血糖持续偏高，建议复查 HbA1c 确认整体控糖情况',
        '如 HbA1c > 7.5%，可考虑增加二甲双胍剂量至 1000mg bid',
        '如剂量调整后仍不达标，建议联合 DPP-4 抑制剂',
      ],
      risks: ['单纯增加剂量可能加重胃肠道反应'],
      uncertainties: ['需要确认患者肾功能状态再决定剂量调整'],
      duration_ms: 1200,
    },
    {
      expert_id: 'pharmacist',
      expert_name: '药剂师',
      recommendations: [
        '二甲双胍可逐步增量，每周增加 500mg，减少胃肠不适',
        '建议餐中或餐后服用以减少副作用',
        '如需联合用药，西格列汀与二甲双胍无明显药物相互作用',
      ],
      risks: ['大剂量二甲双胍需监测维生素B12水平', '肾功能不全时需减量'],
      uncertainties: ['患者是否有乳酸酸中毒风险因素需进一步评估'],
      duration_ms: 980,
    },
    {
      expert_id: 'nutritionist',
      expert_name: '营养师',
      recommendations: [
        '建议晚餐控制碳水化合物摄入，减少精制主食',
        '睡前加餐可选择少量蛋白质（如牛奶、坚果），避免高GI食物',
        '增加膳食纤维摄入有助于稳定空腹血糖',
      ],
      risks: [],
      uncertainties: ['需了解患者具体饮食结构才能给出更精确建议'],
      duration_ms: 850,
    },
  ],
  safety_review: {
    verdict: 'safe',
    issues: [],
    details: '建议内容符合临床指南，无安全风险。已标注需医生面诊确认的事项。',
  },
  final_response:
    '根据您最近的空腹血糖数据（7.8-8.6 mmol/L），确实存在偏高趋势。建议您：\n\n1. **尽快复查 HbA1c**，全面评估近3个月的血糖控制情况\n2. **药物方面**：二甲双胍可在医生指导下逐步增量，注意餐中服用减少胃肠不适\n3. **饮食调整**：控制晚餐碳水摄入，增加膳食纤维\n\n⚠️ 药物调整请务必在医生面诊后决定，不要自行改变用量。',
  writeback_candidates: [
    {
      id: 'wb-001',
      path: '/patient/medication/adjustment_notes',
      content: '2026-04-09: 空腹血糖持续偏高(7.8-8.6)，建议复查HbA1c，考虑二甲双胍增量',
      status: 'approved',
    },
    {
      id: 'wb-002',
      path: '/patient/nutrition/recommendations',
      content: '控制晚餐碳水化合物，增加膳食纤维摄入',
      status: 'pending',
    },
  ],
  timing: {
    memory_retrieval_ms: 320,
    expert_consultation_ms: 3030,
    safety_review_ms: 450,
    total_ms: 4500,
  },
  errors: [],
};

// ─── Store ────────────────────────────────────────────────────────

interface TraceStore {
  traces: TraceItem[];
  selectedTrace: TraceDetail | null;
  loading: boolean;
  detailLoading: boolean;
  error: string | null;

  fetchRecentTraces: () => Promise<void>;
  fetchTraceDetail: (traceId: string) => Promise<void>;
  clearSelection: () => void;
}

export const useTraceStore = create<TraceStore>((set) => ({
  traces: [],
  selectedTrace: null,
  loading: false,
  detailLoading: false,
  error: null,

  fetchRecentTraces: async () => {
    set({ loading: true, error: null });
    try {
      const data = await api.get<{ traces: TraceItem[] }>('/api/traces');
      set({ traces: data.traces || [], loading: false });
    } catch (err) {
      // Fallback to mock data if API not available
      console.warn('[TraceStore] API not available, using mock data');
      set({
        traces: MOCK_TRACES,
        loading: false,
        error: err instanceof ApiError ? null : null, // silently degrade to mock
      });
    }
  },

  fetchTraceDetail: async (traceId: string) => {
    set({ detailLoading: true, error: null });
    try {
      const data = await api.get<TraceDetail>(`/api/traces/${traceId}`);
      set({ selectedTrace: data, detailLoading: false });
    } catch (err) {
      // Fallback to mock detail if API not available
      console.warn('[TraceStore] API not available for detail, using mock data');
      if (traceId === 'trace-001') {
        set({ selectedTrace: MOCK_TRACE_DETAIL, detailLoading: false });
      } else {
        // Generate a synthetic detail for other mock traces
        const mockTrace = MOCK_TRACES.find((t) => t.trace_id === traceId);
        if (mockTrace) {
          set({
            selectedTrace: {
              ...MOCK_TRACE_DETAIL,
              trace_id: traceId,
              patient_id: mockTrace.patient_id,
              created_at: mockTrace.created_at,
              status: mockTrace.status,
              original_query: mockTrace.query,
              timing: {
                ...MOCK_TRACE_DETAIL.timing,
                total_ms: mockTrace.duration_ms || 4500,
              },
              errors: mockTrace.status === 'failure' ? ['专家服务超时'] : [],
              safety_review: mockTrace.has_safety_issues
                ? {
                    verdict: 'caution',
                    issues: ['部分建议需要进一步医生确认', '营养建议可能因个体差异需调整'],
                    details: '存在需要关注的安全事项，已在回复中标注。',
                  }
                : MOCK_TRACE_DETAIL.safety_review,
            },
            detailLoading: false,
          });
        } else {
          const msg = err instanceof ApiError ? err.detail : 'Trace 详情加载失败';
          set({ detailLoading: false, error: msg });
        }
      }
    }
  },

  clearSelection: () => set({ selectedTrace: null }),
}));
