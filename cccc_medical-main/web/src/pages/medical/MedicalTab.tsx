import { useEffect, useState } from "react";

import { EvolutionReport } from "./EvolutionReport";
import { EvaluationView } from "./EvaluationView";
import { LlmConfigPanel } from "./LlmConfigPanel";
import { MemoryPalaceView } from "./MemoryPalaceView";
import { NativeDashboard } from "./NativeDashboard";
import { PatientDetail } from "./PatientDetail";
import { PatientList } from "./PatientList";
import { medicalApiUrl } from "./api";
import { useGroupStore, useMedicalStore } from "../../stores";

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: string;
  diabetesType: string;
  diagnosisDate: string;
  glucoseHistory: GlucoseRecord[];
  medications: string[];
  complications: string[];
}

export interface GlucoseRecord {
  timestamp: string;
  type: "fasting" | "post_meal" | "random";
  value: number;
  note?: string;
}

export interface ConsultationResponse {
  query: string;
  primaryResponse: string;
  expertOpinions: {
    pharmacist: string;
    nutritionist: string;
    doctor: string;
  };
  evaluationScore: number;
  memories: string[];
}

interface MedicalTabProps {
  isDark: boolean;
  isVisible: boolean;
}

type MedicalView = "dashboard" | "list" | "detail" | "evolution" | "config" | "memory" | "evaluation";

export function MedicalTab({ isDark, isVisible }: MedicalTabProps) {
  const [activeView, setActiveView] = useState<MedicalView>("dashboard");
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const selectedGroupId = useGroupStore((state) => state.selectedGroupId);
  const setSelectedPatientBinding = useMedicalStore((state) => state.setSelectedPatientBinding);

  useEffect(() => {
    if (!isVisible) return;
    let cancelled = false;
    const fetchPatients = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(medicalApiUrl("/api/patients"));
        if (!response.ok) throw new Error("Failed to fetch patients");
        const data = await response.json();
        if (!cancelled) setPatients(Array.isArray(data.patients) ? data.patients : []);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setPatients([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchPatients();
    return () => {
      cancelled = true;
    };
  }, [isVisible]);

  if (!isVisible) return null;

  const subtitleMap: Record<MedicalView, string> = {
    dashboard: "CCCC-native 看板",
    list: "患者列表",
    detail: selectedPatient?.name || "患者详情",
    evolution: "评测/优化看板",
    config: "API / Actor 配置",
    memory: "记忆宫殿",
    evaluation: "人工评价",
  };

  return (
    <div className={`flex-1 flex flex-col min-h-0 ${isDark ? "bg-slate-900" : "bg-gray-50"}`}>
      <div className="glass-header flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">血糖管理</h2>
          <span className="text-sm text-[var(--color-text-tertiary)]">{subtitleMap[activeView]}</span>
        </div>

        <div className="flex items-center gap-2">
          {activeView !== "dashboard" && (
            <button
              onClick={() => {
                setSelectedPatient(null);
                setActiveView("dashboard");
              }}
              className="glass-btn px-3 py-1.5 text-sm rounded-lg"
            >
              返回看板
            </button>
          )}
          <button
            onClick={() => setActiveView("memory")}
            className={`glass-btn px-3 py-1.5 text-sm rounded-lg ${activeView === "memory" ? "glass-tab-active" : ""}`}
          >
            🏛️ 记忆
          </button>
          <button
            onClick={() => setActiveView("evaluation")}
            className={`glass-btn px-3 py-1.5 text-sm rounded-lg ${activeView === "evaluation" ? "glass-tab-active" : ""}`}
          >
            📋 评价
          </button>
          <button
            onClick={() => setActiveView("list")}
            className={`glass-btn px-3 py-1.5 text-sm rounded-lg ${activeView === "list" ? "glass-tab-active" : ""}`}
          >
            患者
          </button>
          <button
            onClick={() => setActiveView("evolution")}
            className={`glass-btn px-3 py-1.5 text-sm rounded-lg ${activeView === "evolution" ? "glass-tab-active" : ""}`}
          >
            评测
          </button>
          <button
            onClick={() => setActiveView("config")}
            className={`glass-btn px-3 py-1.5 text-sm rounded-lg ${activeView === "config" ? "glass-tab-active" : ""}`}
          >
            配置
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {loading && activeView === "list" ? (
          <div className="flex items-center justify-center h-full text-[var(--color-text-secondary)]">加载中...</div>
        ) : error && activeView === "list" ? (
          <div className="flex items-center justify-center h-full text-red-500">{error}</div>
        ) : activeView === "dashboard" ? (
          <NativeDashboard isDark={isDark} />
        ) : activeView === "list" ? (
          <PatientList
            patients={patients}
            onSelectPatient={(patient) => {
              setSelectedPatient(patient);
              if (selectedGroupId) {
                setSelectedPatientBinding(selectedGroupId, {
                  patientId: patient.id,
                  patientName: patient.name,
                  age: patient.age,
                  gender: patient.gender,
                  diabetesType: patient.diabetesType,
                  diagnosisDate: patient.diagnosisDate,
                  medications: patient.medications,
                  complications: patient.complications,
                  glucoseRecent: patient.glucoseHistory.slice(-5),
                });
              }
              setActiveView("detail");
            }}
            isDark={isDark}
          />
        ) : activeView === "detail" && selectedPatient ? (
          <PatientDetail patient={selectedPatient} isDark={isDark} />
        ) : activeView === "memory" ? (
          <MemoryPalaceView isDark={isDark} />
        ) : activeView === "evaluation" ? (
          <EvaluationView isDark={isDark} />
        ) : activeView === "evolution" ? (
          <EvolutionReport isDark={isDark} />
        ) : (
          <LlmConfigPanel isDark={isDark} />
        )}
      </div>
    </div>
  );
}

export default MedicalTab;
