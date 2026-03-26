import { useEffect, useState } from "react";

import { ActorGroupPanel } from "./ActorGroupPanel";
import { medicalApiUrl } from "./api";

type GroupSnapshot = {
  group_id: string;
  title: string;
  state: string;
  running: boolean;
  actor_ids: string[];
};

type ActorItem = {
  id: string;
  title?: string;
  running?: boolean;
  enabled?: boolean;
  runtime?: string;
};

interface NativeStatusResponse {
  main_group: GroupSnapshot | Record<string, never>;
  evaluation_group: GroupSnapshot | Record<string, never>;
}

interface NativeActorsResponse {
  main_group_actors: ActorItem[];
  evaluation_group_actors: ActorItem[];
}

interface NativeDashboardProps {
  isDark: boolean;
}

interface ApiHealthResponse {
  memory_palace_status?: string;
}

export function NativeDashboard({ isDark }: NativeDashboardProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [status, setStatus] = useState<NativeStatusResponse | null>(null);
  const [actors, setActors] = useState<NativeActorsResponse | null>(null);
  const [memoryPalaceHealthy, setMemoryPalaceHealthy] = useState<boolean | null>(null);

  const refresh = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statusResp, actorResp, healthResp] = await Promise.all([
        fetch(medicalApiUrl("/api/cccc-native/status")),
        fetch(medicalApiUrl("/api/cccc-native/actors")),
        fetch(medicalApiUrl("/api/health")),
      ]);
      if (!statusResp.ok || !actorResp.ok || !healthResp.ok) throw new Error("Failed to load CCCC-native status");
      const statusPayload = await statusResp.json();
      const actorPayload = await actorResp.json();
      const healthPayload: ApiHealthResponse = await healthResp.json();
      setStatus(statusPayload);
      setActors(actorPayload);
      setMemoryPalaceHealthy(String(healthPayload.memory_palace_status || "").trim() === "ok");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const handleStartGroup = async (target: "main" | "evaluation") => {
    try {
      setBusy(`${target}:start`);
      const response = await fetch(medicalApiUrl("/api/cccc-native/groups/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target }),
      });
      if (!response.ok) throw new Error("Failed to start group");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start group");
    } finally {
      setBusy(null);
    }
  };

  const handleStopGroup = async (target: "main" | "evaluation") => {
    try {
      setBusy(`${target}:stop`);
      const response = await fetch(medicalApiUrl("/api/cccc-native/groups/stop"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target }),
      });
      if (!response.ok) throw new Error("Failed to stop group");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop group");
    } finally {
      setBusy(null);
    }
  };

  const mainGroup = status?.main_group && "group_id" in status.main_group ? (status.main_group as GroupSnapshot) : null;
  const evalGroup = status?.evaluation_group && "group_id" in status.evaluation_group ? (status.evaluation_group as GroupSnapshot) : null;

  return (
    <div className="space-y-4">
      <div className={`glass-card rounded-xl p-4 ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">CCCC-native 医疗多智能体状态</h3>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              这里显示真正的 CCCC 医疗主组、评测组和 Memory Palace 连通状态。
            </p>
          </div>
          <button onClick={() => void refresh()} className="glass-btn px-3 py-2 rounded-lg text-sm">
            刷新状态
          </button>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-4">
          <StatusCard label="医疗主组" value={mainGroup?.group_id ? "已初始化" : "未初始化"} tone={mainGroup?.group_id ? "good" : "warn"} />
          <StatusCard label="评测组" value={evalGroup?.group_id ? "已初始化" : "未初始化"} tone={evalGroup?.group_id ? "good" : "warn"} />
          <StatusCard
            label="Memory Palace"
            value={memoryPalaceHealthy === null ? "检测中" : memoryPalaceHealthy ? "已连接" : "不可用"}
            tone={memoryPalaceHealthy ? "good" : "warn"}
          />
        </div>
      </div>

      {loading ? <div className="text-sm text-[var(--color-text-tertiary)]">加载中...</div> : null}
      {error ? <div className="text-sm text-red-400">{error}</div> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <ActorGroupPanel
          title="医疗主组"
          groupKey="main"
          group={mainGroup}
          actors={actors?.main_group_actors || []}
          busy={busy}
          isDark={isDark}
          onStartGroup={handleStartGroup}
          onStopGroup={handleStopGroup}
        />
        <ActorGroupPanel
          title="评测组"
          groupKey="evaluation"
          group={evalGroup}
          actors={actors?.evaluation_group_actors || []}
          busy={busy}
          isDark={isDark}
          onStartGroup={handleStartGroup}
          onStopGroup={handleStopGroup}
        />
      </div>
    </div>
  );
}

function StatusCard({ label, value, tone }: { label: string; value: string; tone: "good" | "warn" }) {
  return (
    <div className="rounded-lg border border-[var(--glass-border-subtle)] p-3">
      <div className="text-xs text-[var(--color-text-tertiary)]">{label}</div>
      <div className={`mt-1 text-sm font-semibold ${tone === "good" ? "text-emerald-400" : "text-amber-400"}`}>{value}</div>
    </div>
  );
}

export default NativeDashboard;
