import { useMemo } from "react";

type GroupMeta = {
  title: string;
  state: string;
  running: boolean;
  actor_ids?: string[];
};

type ActorItem = {
  id: string;
  title?: string;
  running?: boolean;
  enabled?: boolean;
  runtime?: string;
};

interface ActorGroupPanelProps {
  title: string;
  groupKey: "main" | "evaluation";
  group: GroupMeta | null;
  actors: ActorItem[];
  busy: string | null;
  isDark: boolean;
  onStartGroup: (target: "main" | "evaluation") => Promise<void>;
  onStopGroup: (target: "main" | "evaluation") => Promise<void>;
}

export function ActorGroupPanel({
  title,
  groupKey,
  group,
  actors,
  busy,
  isDark,
  onStartGroup,
  onStopGroup,
}: ActorGroupPanelProps) {
  const actorCount = group?.actor_ids?.length || actors.length || 0;
  const runningCount = useMemo(
    () => actors.filter((actor) => !!actor.running || (!!group?.running && actor.enabled !== false)).length,
    [actors, group?.running]
  );

  return (
    <div className={`glass-card rounded-xl p-4 ${isDark ? "bg-slate-800/30" : "bg-white/50"}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-base font-semibold text-[var(--color-text-primary)]">{title}</div>
          <div className="mt-1 text-xs text-[var(--color-text-tertiary)]">
            {group?.title || "未初始化"} · state={group?.state || "unknown"} · actors={actorCount}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => void onStartGroup(groupKey)}
            disabled={busy === `${groupKey}:start`}
            className="glass-btn px-3 py-1.5 rounded-lg text-xs disabled:opacity-50"
          >
            {busy === `${groupKey}:start` ? "启动中..." : "启动"}
          </button>
          <button
            onClick={() => void onStopGroup(groupKey)}
            disabled={busy === `${groupKey}:stop`}
            className="glass-btn px-3 py-1.5 rounded-lg text-xs disabled:opacity-50"
          >
            {busy === `${groupKey}:stop` ? "停止中..." : "停止"}
          </button>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-3 text-xs">
        <span className={`px-2 py-1 rounded-full ${group?.running ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-500/20 text-slate-400"}`}>
          {group?.running ? "运行中" : "未运行"}
        </span>
        <span className="text-[var(--color-text-tertiary)]">活跃 actor: {runningCount}/{actorCount}</span>
      </div>

      <div className="mt-4 space-y-2">
        {actors.length === 0 ? (
          <div className="text-sm text-[var(--color-text-tertiary)]">暂无 actor 信息</div>
        ) : (
          actors.map((actor) => (
            <div
              key={actor.id}
              className="flex items-center justify-between rounded-lg border border-[var(--glass-border-subtle)] px-3 py-2"
            >
              <div>
                <div className="text-sm font-medium text-[var(--color-text-primary)]">
                  {actor.title || actor.id}
                </div>
                <div className="text-xs text-[var(--color-text-tertiary)]">
                  {actor.id} · {actor.runtime || "runtime?"}
                </div>
              </div>
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  actor.running
                    ? "bg-emerald-500/20 text-emerald-400"
                    : actor.enabled === false
                      ? "bg-red-500/20 text-red-400"
                      : "bg-slate-500/20 text-slate-400"
                }`}
              >
                {actor.running ? "运行中" : actor.enabled === false ? "禁用" : "待启动"}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default ActorGroupPanel;
