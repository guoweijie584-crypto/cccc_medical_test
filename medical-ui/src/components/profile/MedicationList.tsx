import { usePatientStore } from '../../stores/patientStore';

export function MedicationList() {
  const patient = usePatientStore((s) => s.getSelectedPatient());

  if (!patient) return null;

  const medications = patient.medications || [];
  const currentMeds = patient.current_medications || [];

  // If structured meds are available, prefer them
  if (currentMeds.length > 0) {
    return (
      <div className="glass-panel p-4 space-y-3">
        <h3 className="text-sm font-medium text-gray-300">用药列表</h3>
        <div className="space-y-2">
          {currentMeds.map((med, i) => (
            <div
              key={i}
              className="flex items-center gap-3 p-3 rounded-btn bg-white/3 border border-white/5"
            >
              <span className="text-blue-400 text-lg">💊</span>
              <div className="flex-1">
                <p className="text-sm text-gray-200 font-medium">{med.name}</p>
                <p className="text-xs text-gray-500">
                  {med.dosage} · {med.frequency}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Fall back to simple string list
  if (medications.length === 0) {
    return (
      <div className="glass-panel p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">用药列表</h3>
        <p className="text-gray-500 text-sm">暂无用药记录</p>
      </div>
    );
  }

  return (
    <div className="glass-panel p-4 space-y-3">
      <h3 className="text-sm font-medium text-gray-300">用药列表</h3>
      <div className="space-y-2">
        {medications.map((med, i) => (
          <div
            key={i}
            className="flex items-center gap-3 p-3 rounded-btn bg-white/3 border border-white/5"
          >
            <span className="text-blue-400 text-lg">💊</span>
            <p className="text-sm text-gray-200">{med}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
