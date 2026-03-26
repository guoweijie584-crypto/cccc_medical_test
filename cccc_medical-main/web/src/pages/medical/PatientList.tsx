/**
 * PatientList - 患者列表组件
 */

import { useTranslation } from "react-i18next";
import { Patient, GlucoseRecord } from "./MedicalTab";

interface PatientListProps {
  patients: Patient[];
  onSelectPatient: (patient: Patient) => void;
  isDark: boolean;
}

export function PatientList({ patients, onSelectPatient, isDark }: PatientListProps) {
  const { t } = useTranslation("medical");

  const getLatestGlucose = (history: GlucoseRecord[]) => {
    if (history.length === 0) return null;
    return history[history.length - 1];
  };

  const getAverageGlucose = (history: GlucoseRecord[]) => {
    if (history.length === 0) return 0;
    const fasting = history.filter((h) => h.type === "fasting").map((h) => h.value);
    if (fasting.length === 0) return 0;
    return fasting.reduce((a, b) => a + b, 0) / fasting.length;
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-[var(--color-text-primary)]">
          {t("患者列表")} ({patients.length})
        </h3>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder={t("搜索患者...")}
            className="glass-input px-3 py-1.5 text-sm rounded-lg w-48"
          />
          <button className="glass-btn px-3 py-1.5 text-sm rounded-lg">
            + {t("添加患者")}
          </button>
        </div>
      </div>

      <div className="grid gap-3">
        {patients.map((patient) => {
          const latestGlucose = getLatestGlucose(patient.glucoseHistory);
          const avgGlucose = getAverageGlucose(patient.glucoseHistory);
          const glucoseStatus = avgGlucose > 7 ? "high" : avgGlucose > 5.6 ? "normal" : "low";

          return (
            <div
              key={patient.id}
              onClick={() => onSelectPatient(patient)}
              className={`glass-card p-4 rounded-xl cursor-pointer transition-all hover:scale-[1.01] ${
                isDark ? "hover:bg-slate-800/50" : "hover:bg-white/50"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  {/* Avatar */}
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-semibold ${
                    patient.gender === "男"
                      ? "bg-blue-500/20 text-blue-400"
                      : "bg-pink-500/20 text-pink-400"
                  }`}>
                    {patient.name[0]}
                  </div>

                  {/* Basic Info */}
                  <div>
                    <h4 className="font-medium text-[var(--color-text-primary)]">
                      {patient.name}
                    </h4>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      {patient.age}岁 · {patient.gender} · {patient.diabetesType}糖尿病
                    </p>
                    <p className="text-xs text-[var(--color-text-tertiary)] mt-1">
                      {t("确诊时间")}: {patient.diagnosisDate}
                    </p>
                  </div>
                </div>

                {/* Glucose Stats */}
                <div className="text-right">
                  <div className="flex items-center gap-2 justify-end">
                    <span className="text-sm text-[var(--color-text-secondary)]">
                      {t("平均空腹")}:
                    </span>
                    <span className={`text-lg font-semibold ${
                      glucoseStatus === "high"
                        ? "text-red-400"
                        : glucoseStatus === "normal"
                        ? "text-emerald-400"
                        : "text-yellow-400"
                    }`}>
                      {avgGlucose.toFixed(1)}
                    </span>
                    <span className="text-xs text-[var(--color-text-tertiary)]">mmol/L</span>
                  </div>
                  
                  {latestGlucose && (
                    <p className="text-xs text-[var(--color-text-tertiary)] mt-1">
                      {t("最近")}: {latestGlucose.value.toFixed(1)} ({latestGlucose.type === "fasting" ? t("空腹") : t("餐后")})
                    </p>
                  )}
                </div>
              </div>

              {/* Medications & Complications */}
              <div className="mt-3 flex flex-wrap gap-2">
                {patient.medications.map((med, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20"
                  >
                    💊 {med}
                  </span>
                ))}
                {patient.complications.map((comp, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20"
                  >
                    ⚠️ {comp}
                  </span>
                ))}
              </div>

              {/* Action */}
              <div className="mt-3 flex justify-end">
                <button className="text-sm text-cyan-400 hover:text-cyan-300">
                  {t("查看详情")} →
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default PatientList;
