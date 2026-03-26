import { create } from "zustand";

const MEDICAL_BINDING_STORAGE_KEY = "cccc-medical-bindings";

export interface SelectedPatientBinding {
  patientId: string;
  patientName: string;
  age?: number;
  gender?: string;
  diabetesType?: string;
  diagnosisDate?: string;
  medications?: string[];
  complications?: string[];
  glucoseRecent?: Array<{
    timestamp: string;
    type: string;
    value: number;
    note?: string;
  }>;
}

interface MedicalState {
  bindingsByGroup: Record<string, SelectedPatientBinding>;
  setSelectedPatientBinding: (groupId: string, binding: SelectedPatientBinding) => void;
  clearSelectedPatientBinding: (groupId: string) => void;
}

function loadBindings(): Record<string, SelectedPatientBinding> {
  try {
    const raw = localStorage.getItem(MEDICAL_BINDING_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return {};
    const next: Record<string, SelectedPatientBinding> = {};
    for (const [groupId, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (!value || typeof value !== "object") continue;
      const patientId = String((value as SelectedPatientBinding).patientId || "").trim();
      const patientName = String((value as SelectedPatientBinding).patientName || "").trim();
      if (!groupId || !patientId) continue;
      next[groupId] = {
        patientId,
        patientName,
        age: Number((value as SelectedPatientBinding).age || 0) || undefined,
        gender: String((value as SelectedPatientBinding).gender || "").trim() || undefined,
        diabetesType: String((value as SelectedPatientBinding).diabetesType || "").trim() || undefined,
        diagnosisDate: String((value as SelectedPatientBinding).diagnosisDate || "").trim() || undefined,
        medications: Array.isArray((value as SelectedPatientBinding).medications)
          ? (value as SelectedPatientBinding).medications?.map((item) => String(item || "").trim()).filter(Boolean)
          : [],
        complications: Array.isArray((value as SelectedPatientBinding).complications)
          ? (value as SelectedPatientBinding).complications?.map((item) => String(item || "").trim()).filter(Boolean)
          : [],
        glucoseRecent: Array.isArray((value as SelectedPatientBinding).glucoseRecent)
          ? (value as SelectedPatientBinding).glucoseRecent?.filter(Boolean)
          : [],
      };
    }
    return next;
  } catch {
    return {};
  }
}

function saveBindings(bindingsByGroup: Record<string, SelectedPatientBinding>) {
  try {
    localStorage.setItem(MEDICAL_BINDING_STORAGE_KEY, JSON.stringify(bindingsByGroup));
  } catch {
    // ignore persistence failures
  }
}

export const useMedicalStore = create<MedicalState>((set) => ({
  bindingsByGroup: loadBindings(),

  setSelectedPatientBinding: (groupId, binding) =>
    set((state) => {
      const gid = String(groupId || "").trim();
      const patientId = String(binding?.patientId || "").trim();
      const patientName = String(binding?.patientName || "").trim();
      if (!gid || !patientId) return state;
      const next = {
        ...state.bindingsByGroup,
        [gid]: {
          patientId,
          patientName,
          age: binding?.age,
          gender: String(binding?.gender || "").trim() || undefined,
          diabetesType: String(binding?.diabetesType || "").trim() || undefined,
          diagnosisDate: String(binding?.diagnosisDate || "").trim() || undefined,
          medications: Array.isArray(binding?.medications) ? binding.medications.slice(0, 10) : [],
          complications: Array.isArray(binding?.complications) ? binding.complications.slice(0, 10) : [],
          glucoseRecent: Array.isArray(binding?.glucoseRecent) ? binding.glucoseRecent.slice(-5) : [],
        },
      };
      saveBindings(next);
      return { bindingsByGroup: next };
    }),

  clearSelectedPatientBinding: (groupId) =>
    set((state) => {
      const gid = String(groupId || "").trim();
      if (!gid || !state.bindingsByGroup[gid]) return state;
      const next = { ...state.bindingsByGroup };
      delete next[gid];
      saveBindings(next);
      return { bindingsByGroup: next };
    }),
}));
