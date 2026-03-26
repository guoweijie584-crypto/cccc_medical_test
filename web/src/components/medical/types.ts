/**
 * 血糖管理模块类型定义
 */

// 患者数据
export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'male' | 'female';
  diabetes_type: 'type1' | 'type2';
  diagnosis_date: string;
  glucose_history: GlucoseRecord[];
  medications: Medication[];
  memories: Memory[];
}

export interface GlucoseRecord {
  timestamp: string;
  value: number;  // mmol/L
  type: 'fasting' | 'post_meal' | 'random';
  notes?: string;
}

export interface Medication {
  name: string;
  dosage: string;
  frequency: string;
}

export interface Memory {
  id: string;
  content: string;
  category: string;
  timestamp: string;
}

// 咨询数据
export interface ConsultationRequest {
  patient_id: string;
  query: string;
}

export interface ConsultationResponse {
  query: string;
  primary_response: string;
  expert_opinions: {
    pharmacist: string;
    nutritionist: string;
    doctor: string;
  };
  memories_retrieved: Memory[];
  evaluation_score?: number;
}

// 自进化数据
export interface EvolutionReport {
  iterations: IterationResult[];
  improvement: number;
  summary: {
    initial_score: number;
    final_score: number;
    best_iteration: number;
  };
}

export interface IterationResult {
  iteration: number;
  timestamp: string;
  overall_score: number;
  dimensions: {
    medical_accuracy: number;
    safety: number;
    completeness: number;
    personalization: number;
    consistency: number;
  };
  prompt_changes: PromptChange[];
  memory_changes: MemoryChange[];
}

export interface PromptChange {
  agent_id: string;
  agent_name: string;
  change_type: 'added' | 'modified' | 'removed';
  description: string;
  diff?: string;
  before_score: number;
  after_score: number;
}

export interface MemoryChange {
  type: 'added' | 'updated' | 'deleted';
  memory_id: string;
  description: string;
}

// Agent 表现
export interface AgentPerformance {
  agent_id: string;
  name: string;
  avg_score: number;
  test_count: number;
  strengths: string[];
  weaknesses: string[];
  category_scores: Record<string, number>;
}

// 评测数据
export interface EvaluationResult {
  test_id: string;
  category: string;
  question: string;
  agent_response: string;
  expected_points: string[];
  scores: {
    medical_accuracy: number;
    safety: number;
    completeness: number;
    personalization: number;
    consistency: number;
    total: number;
  };
  safety_critical: boolean;
}

export interface EvaluationSummary {
  overall_score: number;
  medical_accuracy: number;
  safety: number;
  completeness: number;
  personalization: number;
  consistency: number;
  category_scores: Record<string, number>;
  safety_critical_cases: number;
  safety_pass_rate: number;
}
