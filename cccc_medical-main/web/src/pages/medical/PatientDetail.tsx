import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { GlucoseChart } from "../../components/medical/GlucoseChart";
import { ConsultationPanel } from "./ConsultationPanel";
import { medicalApiUrl } from "./api";
import { Patient } from "./MedicalTab";

interface PatientDetailProps {
  patient: Patient;
  isDark: boolean;
}

interface MemoryRecord {
  id: string;
  category: string;
  content: string;
  timestamp: string;
}

export function PatientDetail({ patient, isDark }: PatientDetailProps) {
  const { t } = useTranslation("medical");
  const [activeTab, setActiveTab] = useState<"overview" | "consultation" | "memories">("overview");

  return (
    <div className="space-y-4">
      <div className={`glass-card p-4 rounded-xl ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
        <div className="flex items-center gap-4">
          <div
            className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl font-semibold ${
              patient.gender === "男" ? "bg-blue-500/20 text-blue-400" : "bg-pink-500/20 text-pink-400"
            }`}
          >
            {patient.name[0]}
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-[var(--color-text-primary)]">{patient.name}</h3>
            <p className="text-sm text-[var(--color-text-secondary)]">
              {patient.age}岁 · {patient.gender} · {patient.diabetesType}糖尿病 · {t("确诊")}
              {patient.diagnosisDate}
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-emerald-400">{getAverageGlucose(patient.glucoseHistory).toFixed(1)}</div>
            <div className="text-xs text-[var(--color-text-tertiary)]">{t("平均空腹血糖")} mmol/L</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {patient.medications.map((med, idx) => (
            <span
              key={idx}
              className="text-sm px-3 py-1.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20"
            >
              药 {med}
            </span>
          ))}
        </div>
      </div>

      <div className="flex gap-2 border-b border-[var(--glass-border-subtle)]">
        {[
          { key: "overview", label: t("血糖概览") },
          { key: "consultation", label: t("专家咨询") },
          { key: "memories", label: t("患者记忆") },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as "overview" | "consultation" | "memories")}
            className={`px-4 py-2 text-sm font-medium transition-all ${
              activeTab === tab.key
                ? "text-cyan-400 border-b-2 border-cyan-400"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="min-h-[400px]">
        {activeTab === "overview" && <GlucoseOverview patient={patient} isDark={isDark} />}
        {activeTab === "consultation" && <ConsultationPanel patient={patient} isDark={isDark} />}
        {activeTab === "memories" && <PatientMemories patient={patient} isDark={isDark} />}
      </div>
    </div>
  );
}

function GlucoseOverview({ patient, isDark }: { patient: Patient; isDark: boolean }) {
  const { t } = useTranslation("medical");
  const fastingGlucose = patient.glucoseHistory.filter((h) => h.type === "fasting");
  const postMealGlucose = patient.glucoseHistory.filter((h) => h.type === "post_meal");
  const avgFasting = fastingGlucose.reduce((a, b) => a + b.value, 0) / fastingGlucose.length || 0;
  const avgPostMeal = postMealGlucose.reduce((a, b) => a + b.value, 0) / postMealGlucose.length || 0;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <div className={`glass-card p-4 rounded-xl text-center ${avgFasting > 7 ? "border-red-500/30" : "border-emerald-500/30"}`}>
          <div className={`text-2xl font-bold ${avgFasting > 7 ? "text-red-400" : "text-emerald-400"}`}>{avgFasting.toFixed(1)}</div>
          <div className="text-xs text-[var(--color-text-tertiary)] mt-1">{t("平均空腹血糖")}</div>
          <div className="text-xs text-[var(--color-text-tertiary)]">{t("目标")}: 4.4-7.0 mmol/L</div>
        </div>

        <div className={`glass-card p-4 rounded-xl text-center ${avgPostMeal > 10 ? "border-red-500/30" : "border-emerald-500/30"}`}>
          <div className={`text-2xl font-bold ${avgPostMeal > 10 ? "text-red-400" : "text-emerald-400"}`}>{avgPostMeal.toFixed(1)}</div>
          <div className="text-xs text-[var(--color-text-tertiary)] mt-1">{t("平均餐后血糖")}</div>
          <div className="text-xs text-[var(--color-text-tertiary)]">{t("目标")}: &lt;10 mmol/L</div>
        </div>

        <div className="glass-card p-4 rounded-xl text-center border-cyan-500/30">
          <div className="text-2xl font-bold text-cyan-400">{patient.glucoseHistory.length}</div>
          <div className="text-xs text-[var(--color-text-tertiary)] mt-1">{t("记录次数")}</div>
          <div className="text-xs text-[var(--color-text-tertiary)]">{t("近30天")}</div>
        </div>
      </div>

      <div className={`glass-card rounded-xl overflow-hidden ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
        <div className="px-4 py-3 border-b border-[var(--glass-border-subtle)]">
          <h4 className="font-medium text-[var(--color-text-primary)]">{t("血糖趋势图")}</h4>
        </div>
        <div className="p-4">
          <GlucoseChart data={patient.glucoseHistory} height={280} showTarget={true} />
        </div>
      </div>

      <div className={`glass-card rounded-xl overflow-hidden ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
        <div className="px-4 py-3 border-b border-[var(--glass-border-subtle)]">
          <h4 className="font-medium text-[var(--color-text-primary)]">{t("血糖记录")}</h4>
        </div>
        <div className="max-h-64 overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-[var(--glass-bg-subtle)] sticky top-0">
              <tr>
                <th className="px-4 py-2 text-left text-[var(--color-text-secondary)]">{t("时间")}</th>
                <th className="px-4 py-2 text-left text-[var(--color-text-secondary)]">{t("类型")}</th>
                <th className="px-4 py-2 text-right text-[var(--color-text-secondary)]">{t("数值")}</th>
                <th className="px-4 py-2 text-center text-[var(--color-text-secondary)]">{t("状态")}</th>
              </tr>
            </thead>
            <tbody>
              {[...patient.glucoseHistory].reverse().map((record, idx) => {
                const status = getGlucoseStatus(record);
                return (
                  <tr key={idx} className="border-b border-[var(--glass-border-subtle)] last:border-0">
                    <td className="px-4 py-2 text-[var(--color-text-secondary)]">{record.timestamp}</td>
                    <td className="px-4 py-2 text-[var(--color-text-secondary)]">
                      {record.type === "fasting" ? t("空腹") : record.type === "post_meal" ? t("餐后") : t("随机")}
                    </td>
                    <td className="px-4 py-2 text-right font-medium text-[var(--color-text-primary)]">{record.value.toFixed(1)}</td>
                    <td className="px-4 py-2 text-center">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          status === "high"
                            ? "bg-red-500/20 text-red-400"
                            : status === "low"
                              ? "bg-yellow-500/20 text-yellow-400"
                              : "bg-emerald-500/20 text-emerald-400"
                        }`}
                      >
                        {status === "high" ? t("偏高") : status === "low" ? t("偏低") : t("正常")}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function PatientMemories({ patient, isDark }: { patient: Patient; isDark: boolean }) {
  const { t } = useTranslation("medical");
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const loadMemories = async () => {
      try {
        setLoading(true);
        const response = await fetch(medicalApiUrl(`/api/patients/${patient.id}/memories`));
        if (!response.ok) throw new Error("Failed to fetch memories");
        const data = await response.json();
        if (!cancelled) {
          setMemories(Array.isArray(data.memories) ? data.memories : []);
        }
      } catch {
        if (!cancelled) setMemories([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadMemories();
    return () => {
      cancelled = true;
    };
  }, [patient.id]);

  if (loading) {
    return <div className="text-sm text-[var(--color-text-tertiary)]">{t("加载中...")}</div>;
  }

  if (!memories.length) {
    return <div className="text-sm text-[var(--color-text-tertiary)]">{t("暂无记忆数据")}</div>;
  }

  return (
    <div className="space-y-3">
      {memories.map((memory, idx) => (
        <div
          key={memory.id || idx}
          className={`glass-card p-4 rounded-xl ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}
        >
          <div className="flex items-start gap-3">
            <span className="text-lg">
              {memory.category === "medication"
                ? "药"
                : memory.category === "glucose"
                  ? "糖"
                  : memory.category === "diet"
                    ? "食"
                    : memory.category === "exercise"
                      ? "动"
                      : "记"}
            </span>
            <div className="flex-1">
              <p className="text-[var(--color-text-primary)]">{memory.content}</p>
              <p className="text-xs text-[var(--color-text-tertiary)] mt-1">
                {t("记录时间")}: {memory.timestamp || "-"}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function getAverageGlucose(history: Array<{ type: string; value: number }>) {
  if (!history.length) return 0;
  const fasting = history.filter((h) => h.type === "fasting").map((h) => h.value);
  if (!fasting.length) return 0;
  return fasting.reduce((a, b) => a + b, 0) / fasting.length;
}

function getGlucoseStatus(record: { type: string; value: number }) {
  if (record.type === "fasting") {
    if (record.value > 7) return "high";
    if (record.value < 3.9) return "low";
    return "normal";
  }
  if (record.value > 10) return "high";
  if (record.value < 3.9) return "low";
  return "normal";
}

export default PatientDetail;
