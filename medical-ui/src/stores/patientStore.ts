import { create } from 'zustand';
import { api } from '../api/client';

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: string;
  diabetesType?: string;
  diabetes_type?: string;
  diagnosisDate?: string;
  diagnosis_date?: string;
  medications?: string[];
  complications?: string[];
  glucoseHistory?: Array<{
    timestamp: string;
    type: string;
    value: number;
    note?: string;
  }>;
  // Computed aliases for frontend components
  current_medications?: Array<{
    name: string;
    dosage: string;
    frequency: string;
  }>;
  glucose_records?: Array<{
    timestamp: string;
    type: string;
    value: number;
    status?: string;
  }>;
}

interface PatientStore {
  patients: Patient[];
  selectedPatientId: string | null;
  loading: boolean;
  error: string | null;

  fetchPatients: () => Promise<void>;
  selectPatient: (id: string) => void;
  getSelectedPatient: () => Patient | null;
}

export const usePatientStore = create<PatientStore>((set, get) => ({
  patients: [],
  selectedPatientId: null,
  loading: false,
  error: null,

  fetchPatients: async () => {
    set({ loading: true, error: null });
    try {
      const data = await api.get<{ patients: Patient[] }>('/api/patients');
      const patients = (data.patients || []).map(normalizePatient);
      set({
        patients,
        selectedPatientId: patients.length > 0 ? patients[0].id : null,
        loading: false,
      });
    } catch (err) {
      // Fallback demo data for development
      const demoPatients: Patient[] = [
        {
          id: 'P001',
          name: '张三',
          age: 58,
          gender: '男',
          diabetes_type: '2型',
          diagnosis_date: '2020-03-15',
          medications: ['二甲双胍 500mg bid', '格列齐特 30mg qd'],
          complications: ['视网膜病变(轻度)'],
        },
        {
          id: 'P002',
          name: '李四',
          age: 45,
          gender: '女',
          diabetes_type: '2型',
          diagnosis_date: '2022-07-20',
          medications: ['阿卡波糖 50mg tid'],
          complications: [],
        },
      ];
      set({
        patients: demoPatients,
        selectedPatientId: 'P001',
        loading: false,
        error: 'API暂不可用，使用演示数据',
      });
    }
  },

  selectPatient: (id: string) => {
    set({ selectedPatientId: id });
  },

  getSelectedPatient: () => {
    const { patients, selectedPatientId } = get();
    return patients.find((p) => p.id === selectedPatientId) || null;
  },
}));

/** Normalize backend camelCase fields to frontend-friendly aliases */
function normalizePatient(p: Patient): Patient {
  // diabetes_type alias
  p.diabetes_type = p.diabetesType || p.diabetes_type || '2型';
  // diagnosis_date alias
  p.diagnosis_date = p.diagnosisDate || p.diagnosis_date || '';
  // glucose_records from glucoseHistory
  if (p.glucoseHistory && p.glucoseHistory.length > 0 && (!p.glucose_records || p.glucose_records.length === 0)) {
    p.glucose_records = p.glucoseHistory.map((g) => ({
      timestamp: g.timestamp,
      type: g.type,
      value: g.value,
      status: g.note || '',
    }));
  }
  // current_medications from medications (string[])
  if (p.medications && p.medications.length > 0 && (!p.current_medications || p.current_medications.length === 0)) {
    p.current_medications = p.medications.map((med) => {
      // Parse "二甲双胍 500mg bid" format
      const parts = med.split(/\s+/);
      return {
        name: parts[0] || med,
        dosage: parts[1] || '',
        frequency: parts[2] || '',
      };
    });
  }
  return p;
}
