import { usePatientStore } from '../../stores/patientStore';

export function Header() {
  const patient = usePatientStore((s) => s.getSelectedPatient());

  return (
    <header className="flex h-14 items-center justify-between border-b border-white/5 bg-surface-900/40 px-6 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-gray-200">
          {getPageTitle()}
        </h1>
      </div>
      <div className="flex items-center gap-3">
        {patient && (
          <div className="flex items-center gap-2 rounded-full bg-primary-600/10 border border-primary-500/20 px-3 py-1">
            <div className="h-2 w-2 rounded-full bg-primary-400 animate-pulse" />
            <span className="text-xs text-primary-300">
              {patient.name} · {patient.age}岁 · {patient.diabetes_type}
            </span>
          </div>
        )}
      </div>
    </header>
  );
}

function getPageTitle(): string {
  const path = window.location.pathname.replace('/medical', '');
  switch (path) {
    case '/':
    case '':
      return '🏥 血糖管理智能助手';
    case '/memory':
      return '🏛️ 记忆宫殿';
    case '/evaluation':
      return '📋 评价管理';
    case '/profile':
      return '👤 患者档案';
    default:
      return '🏥 血糖管理智能助手';
  }
}
