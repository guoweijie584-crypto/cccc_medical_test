import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { pingDaemon, getGroupContext, MAIN_GROUP_ID } from '../../api/ccccClient';

const REQUIRED_ACTORS = ['primary', 'memory', 'pharmacist', 'nutritionist', 'doctor'];
const ACTOR_TITLES: Record<string, string> = {
  primary: '主治医生',
  pharmacist: '药剂师',
  nutritionist: '营养师',
  doctor: '代谢病医生',
  memory: '记忆管理',
};

interface HealthStatus {
  daemonOk: boolean;
  groupReachable: boolean;
  checking: boolean;
  errors: string[];
}

export function SystemStatusBanner() {
  const [health, setHealth] = useState<HealthStatus>({
    daemonOk: true,
    groupReachable: true,
    checking: true,
    errors: [],
  });
  const [dismissed, setDismissed] = useState(false);

  const checkHealth = useCallback(async () => {
    const errors: string[] = [];

    try {
      const daemonOk = await pingDaemon();
      if (!daemonOk) {
        errors.push('CCCC 协作系统不可达');
        setHealth({ daemonOk: false, groupReachable: false, checking: false, errors });
        return;
      }

      try {
        await getGroupContext(MAIN_GROUP_ID);
      } catch {
        errors.push('医疗工作组不可用');
      }

      setHealth({
        daemonOk: true,
        groupReachable: errors.length === 0,
        checking: false,
        errors,
      });
    } catch {
      setHealth({
        daemonOk: false,
        groupReachable: false,
        checking: false,
        errors: ['无法连接到协作系统'],
      });
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const timer = setInterval(checkHealth, 30_000);
    return () => clearInterval(timer);
  }, [checkHealth]);

  // Don't show anything if checking or healthy
  if (health.checking) return null;
  if (health.daemonOk && health.groupReachable) return null;
  if (dismissed) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className={`px-4 py-2 text-sm flex items-center justify-between ${
          health.daemonOk
            ? 'bg-yellow-500/10 border-b border-yellow-500/20 text-yellow-300'
            : 'bg-red-500/10 border-b border-red-500/20 text-red-300'
        }`}
      >
        <div className="flex items-center gap-2">
          <span>{health.daemonOk ? '⚠️' : '🔴'}</span>
          <span>{health.errors.join(' · ') || '系统异常'}</span>
          <span className="text-xs opacity-60">— AI 会诊功能可能受限</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setHealth((s) => ({ ...s, checking: true }));
              checkHealth();
            }}
            className="text-xs underline hover:opacity-80"
          >
            重新检测
          </button>
          <button
            onClick={() => setDismissed(true)}
            className="text-xs opacity-60 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
