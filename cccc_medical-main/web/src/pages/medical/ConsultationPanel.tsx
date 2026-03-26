/**
 * ConsultationPanel - 咨询面板组件
 * 
 * 功能：
 * - 输入咨询问题
 * - 显示 4 个专家 Agent 的回复
 * - 显示综合建议
 * - 显示评分
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { medicalApiUrl } from "./api";
import { Patient, ConsultationResponse } from "./MedicalTab";

interface ConsultationPanelProps {
  patient: Patient;
  isDark: boolean;
}

export function ConsultationPanel({ patient, isDark }: ConsultationPanelProps) {
  const { t } = useTranslation("medical");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ConsultationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(medicalApiUrl("/api/consultation"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_id: patient.id, query }),
      });
      
      if (!res.ok) throw new Error("Consultation failed");
      
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      // 使用模拟数据
      setResponse(getMockResponse(query));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Input Area */}
      <div className={`glass-card p-4 rounded-xl ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
        <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
          {t("输入您的问题")}
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("例如：我最近空腹血糖一直8左右，需要调整药吗？")}
          className="w-full h-24 glass-input p-3 rounded-lg text-sm resize-none"
        />
        <div className="flex justify-end mt-3">
          <button
            onClick={handleSubmit}
            disabled={loading || !query.trim()}
            className="glass-btn px-6 py-2 rounded-lg font-medium disabled:opacity-50"
          >
            {loading ? t("分析中...") : t("咨询专家")}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Response */}
      {response && (
        <div className="space-y-4">
          {/* Expert Opinions */}
          <div className="grid gap-3">
            {/* Pharmacist */}
            <ExpertCard
              title={t("药剂师")}
              icon="💊"
              color="blue"
              content={response.expertOpinions.pharmacist}
              isDark={isDark}
            />
            
            {/* Nutritionist */}
            <ExpertCard
              title={t("营养师")}
              icon="🥗"
              color="green"
              content={response.expertOpinions.nutritionist}
              isDark={isDark}
            />
            
            {/* Doctor */}
            <ExpertCard
              title={t("代谢病医生")}
              icon="👨‍⚕️"
              color="purple"
              content={response.expertOpinions.doctor}
              isDark={isDark}
            />
          </div>

          {/* Primary Response */}
          <div className={`glass-card p-4 rounded-xl border-2 border-cyan-500/30 ${
            isDark ? "bg-cyan-900/10" : "bg-cyan-50/50"
          }`}>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xl">👨‍⚕️</span>
              <h4 className="font-semibold text-[var(--color-text-primary)]">
                {t("主治医生综合建议")}
              </h4>
              <span className="ml-auto text-sm px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400">
                {t("评分")}: {response.evaluationScore.toFixed(1)}/10
              </span>
            </div>
            <div className="text-[var(--color-text-primary)] whitespace-pre-line">
              {response.primaryResponse}
            </div>
          </div>

          {/* Memories */}
          {response.memories.length > 0 && (
            <div className={`glass-card p-4 rounded-xl ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
              <h4 className="font-medium text-[var(--color-text-secondary)] mb-2">
                {t("相关记忆")}
              </h4>
              <ul className="space-y-1 text-sm text-[var(--color-text-tertiary)]">
                {response.memories.map((memory, idx) => (
                  <li key={idx}>• {memory}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// 专家卡片组件
function ExpertCard({
  title,
  icon,
  color,
  content,
  isDark,
}: {
  title: string;
  icon: string;
  color: string;
  content: string;
  isDark: boolean;
}) {
  const colorClasses: Record<string, { bg: string; border: string }> = {
    blue: { bg: "bg-blue-500/10", border: "border-blue-500/20" },
    green: { bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
    purple: { bg: "bg-purple-500/10", border: "border-purple-500/20" },
  };

  const colors = colorClasses[color] || colorClasses.blue;

  return (
    <div className={`glass-card p-4 rounded-xl ${colors.bg} border ${colors.border} ${
      isDark ? "" : "bg-white/50"
    }`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">{icon}</span>
        <h4 className="font-medium text-[var(--color-text-primary)]">{title}</h4>
      </div>
      <div className="text-sm text-[var(--color-text-secondary)] whitespace-pre-line">
        {content}
      </div>
    </div>
  );
}

// 模拟响应数据
function getMockResponse(query: string): ConsultationResponse {
  return {
    query,
    primaryResponse: `【综合建议】
- 核心建议：根据您的情况，建议继续当前治疗方案，同时注意饮食控制和规律监测。
- 详细说明：保持良好的用药依从性，定期监测血糖变化。如有异常波动请及时联系医生。
- 注意事项：避免空腹运动，随身携带糖果预防低血糖。

【特别提醒】
如血糖持续高于13.9或低于3.9 mmol/L，请及时就医。`,
    expertOpinions: {
      pharmacist: `【用药建议】
1. 二甲双胍是2型糖尿病的一线用药，主要通过减少肝脏葡萄糖输出来降低血糖。
2. 常见副作用包括胃肠道反应，通常随用药时间延长会减轻。

【注意事项】
- 药物相互作用：与某些造影剂合用需停药
- 常见副作用：恶心、腹泻、胃部不适

[⚠️] 具体剂量调整请咨询主治医生。`,
      nutritionist: `【饮食建议】
1. 控制每餐碳水化合物摄入量，建议选择低GI食物。
2. 推荐餐食：糙米饭 + 清蒸鱼 + 绿叶蔬菜 + 适量豆腐

【实用技巧】
- 进餐顺序：先吃蔬菜，再吃蛋白质，最后吃主食
- 分量控制：使用标准餐具，每餐主食约1拳头大小`,
      doctor: `【病情评估】
- 当前控制状况：需改善
- 主要关注点：餐后血糖控制

【诊疗建议】
- 建议的监测项目：每周2-3次空腹及餐后2小时血糖
- 生活方式调整：饮食控制 + 适量运动
- 就医建议：建议1-3个月内复查糖化血红蛋白

【目标设定】
- 血糖控制目标：空腹 4.4-7.0 mmol/L，餐后<10 mmol/L`,
    },
    evaluationScore: 8.2,
    memories: [
      "当前用药：二甲双胍 500mg bid",
      "近期空腹血糖控制在 7-8 mmol/L",
      "偏好低GI饮食",
    ],
  };
}

export default ConsultationPanel;
