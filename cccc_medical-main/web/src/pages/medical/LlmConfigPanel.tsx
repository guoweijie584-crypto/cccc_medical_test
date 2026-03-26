import { useEffect, useMemo, useState } from "react";
import { medicalApiUrl } from "./api";

type ActorConfigView = {
  configured: boolean;
  apiKeyPreview: string;
  apiBase: string;
  model: string;
};

type NativeLlmConfigResponse = {
  default: ActorConfigView;
  actors: Record<string, ActorConfigView>;
};

type ActorEditorState = {
  api_key: string;
  api_base: string;
  model: string;
  clear_api_key: boolean;
};

interface LlmConfigPanelProps {
  isDark: boolean;
}

const IMPORTANT_ACTORS = [
  "primary",
  "pharmacist",
  "nutritionist",
  "doctor",
  "memory",
  "evaluator",
  "analyzer",
  "prompt_optimizer",
  "memory_optimizer",
];

export function LlmConfigPanel({ isDark }: LlmConfigPanelProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [config, setConfig] = useState<NativeLlmConfigResponse | null>(null);
  const [defaultApiKey, setDefaultApiKey] = useState("");
  const [defaultApiBase, setDefaultApiBase] = useState("https://api.deepseek.com/v1");
  const [defaultModel, setDefaultModel] = useState("deepseek-chat");
  const [defaultClearApiKey, setDefaultClearApiKey] = useState(false);
  const [actorEditors, setActorEditors] = useState<Record<string, ActorEditorState>>({});

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(medicalApiUrl("/api/cccc-native/llm"));
      if (!response.ok) throw new Error("Failed to load CCCC-native LLM config");
      const data = await response.json();
      setConfig(data);
      setDefaultApiBase(data.default?.apiBase || "https://api.deepseek.com/v1");
      setDefaultModel(data.default?.model || "deepseek-chat");
      const nextEditors: Record<string, ActorEditorState> = {};
      for (const actorId of IMPORTANT_ACTORS) {
        const actorCfg = data.actors?.[actorId] || {};
        nextEditors[actorId] = {
          api_key: "",
          api_base: actorCfg.apiBase || "",
          model: actorCfg.model || "",
          clear_api_key: false,
        };
      }
      setActorEditors(nextEditors);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load config");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const actorList = useMemo(() => IMPORTANT_ACTORS, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setNotice(null);
      const payload = {
        default: {
          api_key: defaultApiKey,
          api_base: defaultApiBase,
          model: defaultModel,
          clear_api_key: defaultClearApiKey,
        },
        actors: actorEditors,
      };
      const response = await fetch(medicalApiUrl("/api/cccc-native/llm"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Failed to save config");
      const data = await response.json();
      setConfig(data);
      setDefaultApiKey("");
      setDefaultClearApiKey(false);
      setNotice("配置已保存，新的设置会在后续 actor 会话中生效。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save config");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-[var(--color-text-tertiary)]">加载 CCCC-native LLM 配置中...</div>;
  }

  return (
    <div className={`glass-card rounded-xl p-5 space-y-5 ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
      <div>
        <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">CCCC-native Agent LLM 配置</h3>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          这里配置的是未来 9 个 CCCC-native actor 的组级默认模型和 actor 级覆盖。
        </p>
      </div>

      <section className="space-y-3">
        <div className="text-sm font-medium text-[var(--color-text-primary)]">组级默认配置</div>
        <div className="grid grid-cols-2 gap-4">
          <InfoCard label="默认 API Key 状态" value={config?.default?.configured ? `已配置 (${config?.default?.apiKeyPreview || "已隐藏"})` : "未配置"} />
          <InfoCard label="默认模型" value={config?.default?.model || defaultModel} />
        </div>

        <input
          value={defaultApiKey}
          onChange={(e) => setDefaultApiKey(e.target.value)}
          type="password"
          placeholder="新的默认 API Key（留空则保持不变）"
          className="w-full glass-input px-3 py-2 rounded-lg"
        />
        <input
          value={defaultApiBase}
          onChange={(e) => setDefaultApiBase(e.target.value)}
          placeholder="默认 API Base"
          className="w-full glass-input px-3 py-2 rounded-lg"
        />
        <input
          value={defaultModel}
          onChange={(e) => setDefaultModel(e.target.value)}
          placeholder="默认模型名"
          className="w-full glass-input px-3 py-2 rounded-lg"
        />
        <label className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
          <input type="checkbox" checked={defaultClearApiKey} onChange={(e) => setDefaultClearApiKey(e.target.checked)} />
          清空默认 API Key
        </label>
      </section>

      <section className="space-y-3">
        <div className="text-sm font-medium text-[var(--color-text-primary)]">Actor 级覆盖（可选）</div>
        <div className="space-y-4">
          {actorList.map((actorId) => {
            const actorCfg = config?.actors?.[actorId];
            const editor = actorEditors[actorId] || { api_key: "", api_base: "", model: "", clear_api_key: false };
            return (
              <div key={actorId} className="rounded-lg border border-[var(--glass-border-subtle)] p-3 space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium text-[var(--color-text-primary)]">{actorId}</div>
                  <div className="text-xs text-[var(--color-text-tertiary)]">
                    {actorCfg?.configured ? `已配置 (${actorCfg.apiKeyPreview || "已隐藏"})` : "继承默认"}
                  </div>
                </div>
                <input
                  value={editor.api_key}
                  onChange={(e) =>
                    setActorEditors((current) => ({
                      ...current,
                      [actorId]: { ...current[actorId], api_key: e.target.value },
                    }))
                  }
                  type="password"
                  placeholder={`${actorId} 的覆盖 API Key（留空则不改）`}
                  className="w-full glass-input px-3 py-2 rounded-lg"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={editor.api_base}
                    onChange={(e) =>
                      setActorEditors((current) => ({
                        ...current,
                        [actorId]: { ...current[actorId], api_base: e.target.value },
                      }))
                    }
                    placeholder="覆盖 API Base"
                    className="w-full glass-input px-3 py-2 rounded-lg"
                  />
                  <input
                    value={editor.model}
                    onChange={(e) =>
                      setActorEditors((current) => ({
                        ...current,
                        [actorId]: { ...current[actorId], model: e.target.value },
                      }))
                    }
                    placeholder="覆盖模型名"
                    className="w-full glass-input px-3 py-2 rounded-lg"
                  />
                </div>
                <label className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
                  <input
                    type="checkbox"
                    checked={editor.clear_api_key}
                    onChange={(e) =>
                      setActorEditors((current) => ({
                        ...current,
                        [actorId]: { ...current[actorId], clear_api_key: e.target.checked },
                      }))
                    }
                  />
                  清空该 actor 的 API Key 覆盖
                </label>
              </div>
            );
          })}
        </div>
      </section>

      {error ? <div className="text-sm text-red-400">{error}</div> : null}
      {notice ? <div className="text-sm text-emerald-400">{notice}</div> : null}

      <div className="flex justify-end gap-2">
        <button onClick={() => void load()} className="glass-btn px-4 py-2 rounded-lg">
          刷新
        </button>
        <button onClick={() => void handleSave()} disabled={saving} className="glass-btn px-4 py-2 rounded-lg disabled:opacity-50">
          {saving ? "保存中..." : "保存配置"}
        </button>
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--glass-border-subtle)] p-3">
      <div className="text-xs text-[var(--color-text-tertiary)]">{label}</div>
      <div className="mt-1 text-sm font-medium text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

export default LlmConfigPanel;
