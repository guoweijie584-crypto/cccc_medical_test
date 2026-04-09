import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { usePatientStore } from '../../stores/patientStore';

const navItems = [
  { path: '/', icon: '💬', label: '对话', title: 'AI 对话咨询' },
  { path: '/memory', icon: '🏛️', label: '记忆', title: '记忆宫殿' },
  { path: '/evaluation', icon: '📋', label: '评价', title: '评价管理' },
  { path: '/traces', icon: '🔍', label: 'Trace 审阅', title: 'Trace 审阅' },
  { path: '/admin', icon: '⚙️', label: '系统管理', title: '系统管理' },
  { path: '/profile', icon: '👤', label: '档案', title: '患者档案' },
];

export function Sidebar() {
  const { patients, selectedPatientId, selectPatient, loading } = usePatientStore();
  const location = useLocation();

  return (
    <aside className="flex w-[220px] flex-col border-r border-white/5 bg-surface-900/60 backdrop-blur-sm">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 px-4 border-b border-white/5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600">
          <span className="text-sm">🏥</span>
        </div>
        <span className="text-sm font-semibold text-gray-200">血糖管理助手</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive =
            item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className="relative flex items-center gap-3 rounded-btn px-3 py-2.5 text-sm transition-colors duration-150"
            >
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-btn bg-primary-600/20 border border-primary-500/20"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
                />
              )}
              <span className="relative z-10 text-base">{item.icon}</span>
              <span
                className={`relative z-10 ${
                  isActive ? 'text-primary-300 font-medium' : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {item.label}
              </span>
            </NavLink>
          );
        })}
      </nav>

      {/* Patient Selector */}
      <div className="border-t border-white/5 px-3 py-3">
        <label className="mb-1.5 block text-xs text-gray-500 font-medium px-1">当前患者</label>
        {loading ? (
          <div className="h-9 animate-pulse rounded-btn bg-white/5" />
        ) : (
          <select
            value={selectedPatientId || ''}
            onChange={(e) => selectPatient(e.target.value)}
            className="w-full rounded-btn bg-surface-800 border border-white/10 px-3 py-2 text-sm text-gray-200
                       focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500/30
                       appearance-none cursor-pointer"
          >
            {patients.length === 0 && <option value="">无患者数据</option>}
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} · {p.age}岁 · {p.diabetes_type}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-white/5">
        <span className="text-[10px] text-gray-600">v0.1.0 MVP</span>
      </div>
    </aside>
  );
}
