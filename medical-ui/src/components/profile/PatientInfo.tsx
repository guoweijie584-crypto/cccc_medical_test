import { usePatientStore, type Patient } from '../../stores/patientStore';

export function PatientInfo() {
  const patient = usePatientStore((s) => s.getSelectedPatient());

  if (!patient) {
    return (
      <div className="glass-panel p-6 text-center">
        <p className="text-gray-500 text-sm">请先选择一位患者</p>
      </div>
    );
  }

  return (
    <div className="glass-panel p-5 space-y-4">
      {/* Avatar + name */}
      <div className="flex items-center gap-4">
        <div
          className={`w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold ${
            patient.gender === '男'
              ? 'bg-primary-500/20 text-primary-400'
              : 'bg-pink-500/20 text-pink-400'
          }`}
        >
          {patient.name[0]}
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-100">{patient.name}</h3>
          <p className="text-sm text-gray-500">
            {patient.age}岁 · {patient.gender} · {patient.diabetes_type}糖尿病
          </p>
        </div>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-2 gap-3">
        <InfoItem label="患者ID" value={patient.id} />
        <InfoItem label="确诊时间" value={patient.diagnosis_date || '—'} />
        <InfoItem label="糖尿病类型" value={patient.diabetes_type} />
        <InfoItem label="并发症" value={
          patient.complications?.length ? patient.complications.join('、') : '无'
        } />
      </div>
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-2.5 rounded-btn bg-white/3 border border-white/5">
      <div className="text-xs text-gray-500 mb-0.5">{label}</div>
      <div className="text-sm text-gray-300">{value}</div>
    </div>
  );
}
