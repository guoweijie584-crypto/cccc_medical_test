import { motion } from 'framer-motion';
import { usePatientStore } from '../stores/patientStore';
import { PatientInfo } from '../components/profile/PatientInfo';
import { GlucoseChart } from '../components/profile/GlucoseChart';
import { MedicationList } from '../components/profile/MedicationList';

export function ProfilePage() {
  const patient = usePatientStore((s) => s.getSelectedPatient());

  if (!patient) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex h-full items-center justify-center"
      >
        <div className="text-center">
          <div className="text-5xl mb-3">👤</div>
          <p className="text-gray-500 text-sm">请先选择一位患者</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full overflow-auto p-4 space-y-4"
    >
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-100">患者档案</h1>
        <p className="text-xs text-gray-500 mt-0.5">{patient.name} · {patient.id}</p>
      </div>

      {/* Patient info card */}
      <PatientInfo />

      {/* Glucose chart */}
      <GlucoseChart />

      {/* Medication list */}
      <MedicationList />

      {/* Glucose records table */}
      {patient.glucose_records && patient.glucose_records.length > 0 && (
        <div className="glass-panel overflow-hidden">
          <div className="px-4 py-3 border-b border-white/5">
            <h3 className="text-sm font-medium text-gray-300">血糖记录</h3>
          </div>
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-white/3 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-xs text-gray-500 font-medium">时间</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-500 font-medium">类型</th>
                  <th className="px-4 py-2 text-right text-xs text-gray-500 font-medium">数值</th>
                  <th className="px-4 py-2 text-center text-xs text-gray-500 font-medium">状态</th>
                </tr>
              </thead>
              <tbody>
                {[...patient.glucose_records].reverse().map((record, i) => {
                  const status = getGlucoseStatus(record);
                  return (
                    <tr key={i} className="border-b border-white/3 last:border-0 hover:bg-white/2">
                      <td className="px-4 py-2 text-gray-400 text-xs">{record.timestamp}</td>
                      <td className="px-4 py-2 text-gray-400 text-xs">
                        {record.type === 'fasting' ? '空腹' : record.type === 'post_meal' ? '餐后' : '随机'}
                      </td>
                      <td className="px-4 py-2 text-right text-gray-200 font-medium">
                        {record.value.toFixed(1)}
                      </td>
                      <td className="px-4 py-2 text-center">
                        <span className={
                          status === 'high' ? 'badge-bad' :
                          status === 'low' ? 'badge-error' :
                          'badge-good'
                        }>
                          {status === 'high' ? '偏高' : status === 'low' ? '偏低' : '正常'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </motion.div>
  );
}

function getGlucoseStatus(record: { type: string; value: number }): 'high' | 'low' | 'normal' {
  if (record.type === 'fasting') {
    if (record.value > 7) return 'high';
    if (record.value < 3.9) return 'low';
    return 'normal';
  }
  if (record.value > 10) return 'high';
  if (record.value < 3.9) return 'low';
  return 'normal';
}
