import { useEffect, useState } from "react";

import { ConsultationPanel } from "./ConsultationPanel";
import { EvaluationView } from "./EvaluationView";
import { MemoryPalaceView } from "./MemoryPalaceView";
import { PatientDetail } from "./PatientDetail";
import { PatientList } from "./PatientList";
import { SystemAdminPanel } from "./SystemAdminPanel";
import { TraceReviewPanel } from "./TraceReviewPanel";
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

type MedicalView = "consultation" | "trace" | "memory" | "evaluation" | "admin";

const NAV_ITEMS: { key: MedicalView; icon: string; label: string }[] = [
  { key: "consultation", icon: "\uD83D\uDCAC", label: "\u5BF9\u8BDD\u54A8\u8BE2" },
  { key: "trace",        icon: "\uD83D\uDD0D", label: "Trace \u5BA1\u9605" },
  { key: "memory",       icon: "\uD83C\uDFDB\uFE0F", label: "\u8BB0\u5FC6\u6CBB\u7406" },
  { key: "evaluation",   icon: "\uD83D\uDCCB", label: "\u4EBA\u5DE5\u8BC4\u4EF7" },
  { key: "admin",        icon: "\u2699\uFE0F", label: "\u7CFB\u7EDF\u7BA1\u7406" },
];

const SUBTITLE_MAP: Record<MedicalView, string> = {
  consultation: "\u5BF9\u8BDD\u54A8\u8BE2",
  trace: "Trace \u5BA1\u9605",
  memory: "\u8BB0\u5FC6\u5BAB\u6BBF",
  evaluation: "\u4EBA\u5DE5\u8BC4\u4EF7",
  admin: "\u7CFB\u7EDF\u7BA1\u7406",
};

export function MedicalTab({ isDark, isVisible }: MedicalTabProps) {
  const [activeView, setActiveView] = useState<MedicalView>("consultation");
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
    return () => { cancelled = true; };
  }, [isVisible]);

  if (!isVisible) return null;

  const handleSelectPatient = (patient: Patient) => {
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
  };

  return (
    <div className={`flex-1 flex flex-col min-h-0 ${isDark ? "bg-slate-900" : "bg-gray-50"}`}>
      {/* Header + Navigation */}
      <div className="glass-header px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
              {"\u8840\u7CD6\u7BA1\u7406\u591A\u667A\u80FD\u4F53\u7CFB\u7EDF"}
            </h2>
            <span className="text-sm text-[var(--color-text-tertiary)]">
              {SUBTITLE_MAP[activeView]}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => {
                if (item.key === "consultation") setSelectedPatient(null);
                setActiveView(item.key);
              }}
              className={`glass-btn px-3 py-1.5 text-sm rounded-lg transition-all ${
                activeView === item.key ? "glass-tab-active" : ""
              }`}
            >
              {item.icon} {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeView === "consultation" ? (
          loading ? (
            <div className="flex items-center justify-center h-full text-[var(--color-text-secondary)]">{"\u52A0\u8F7D\u4E2D..."}</div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-500">{error}</div>
          ) : !selectedPatient ? (
            <PatientList
              patients={patients}
              onSelectPatient={handleSelectPatient}
              isDark={isDark}
            />
          ) : (
            <div className="space-y-4">
              <button
                onClick={() => setSelectedPatient(null)}
                className="glass-btn px-3 py-1.5 text-sm rounded-lg"
              >
                {"\u2190 \u8FD4\u56DE\u60A3\u8005\u5217\u8868"}
              </button>
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                <div className="xl:col-span-2">
                  <ConsultationPanel patient={selectedPatient} isDark={isDark} />
                </div>
                <div className="xl:col-span-1">
                  <PatientDetail patient={selectedPatient} isDark={isDark} />
                </div>
              </div>
            </div>
          )
        ) : activeView === "trace" ? (
          <TraceReviewPanel isDark={isDark} />
        ) : activeView === "memory" ? (
          <MemoryPalaceView isDark={isDark} />
        ) : activeView === "evaluation" ? (
          <EvaluationView isDark={isDark} />
        ) : activeView === "admin" ? (
          <SystemAdminPanel isDark={isDark} />
        ) : null}
      </div>
    </div>
  );
}

export default MedicalTab;
