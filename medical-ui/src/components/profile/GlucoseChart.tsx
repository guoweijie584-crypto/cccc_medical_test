import { useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { usePatientStore } from '../../stores/patientStore';

type GlucoseType = 'all' | 'fasting' | 'post_meal' | 'random';

const TYPE_LABELS: Record<string, string> = {
  fasting: '空腹',
  post_meal: '餐后',
  random: '随机',
};

const TYPE_COLORS: Record<string, string> = {
  fasting: '#06b6d4',    // cyan
  post_meal: '#f59e0b',  // amber
  random: '#a78bfa',     // purple
};

export function GlucoseChart() {
  const patient = usePatientStore((s) => s.getSelectedPatient());
  const [filter, setFilter] = useState<GlucoseType>('all');

  const records = useMemo(() => {
    if (!patient?.glucose_records) return [];
    const filtered = filter === 'all'
      ? patient.glucose_records
      : patient.glucose_records.filter((r) => r.type === filter);
    return filtered.map((r) => ({
      ...r,
      date: r.timestamp ? new Date(r.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) : '',
      typeLabel: TYPE_LABELS[r.type] || r.type,
    }));
  }, [patient, filter]);

  if (!patient?.glucose_records?.length) {
    return (
      <div className="glass-panel p-6 text-center">
        <p className="text-gray-500 text-sm">暂无血糖记录</p>
      </div>
    );
  }

  return (
    <div className="glass-panel p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-300">血糖趋势图</h3>
        <div className="flex gap-1 p-0.5 rounded-btn bg-white/5">
          {(['all', 'fasting', 'post_meal', 'random'] as GlucoseType[]).map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`px-2.5 py-1 text-xs rounded-btn transition-colors ${
                filter === t
                  ? 'bg-white/10 text-gray-200'
                  : 'text-gray-500 hover:text-gray-400'
              }`}
            >
              {t === 'all' ? '全部' : TYPE_LABELS[t]}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={records} margin={{ top: 10, right: 10, bottom: 5, left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#6b7280', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
          />
          <YAxis
            domain={[2, 18]}
            tick={{ fill: '#6b7280', fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            unit=" mmol/L"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: '#9ca3af' }}
            formatter={(value: number, name: string) => [`${value.toFixed(1)} mmol/L`, name]}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: '#9ca3af' }}
          />

          {/* Target lines */}
          <ReferenceLine
            y={7.0}
            stroke="#22d3ee"
            strokeDasharray="6 3"
            label={{ value: '空腹上限 7.0', fill: '#22d3ee', fontSize: 10, position: 'right' }}
          />
          <ReferenceLine
            y={10.0}
            stroke="#f59e0b"
            strokeDasharray="6 3"
            label={{ value: '餐后上限 10.0', fill: '#f59e0b', fontSize: 10, position: 'right' }}
          />
          <ReferenceLine
            y={3.9}
            stroke="#ef4444"
            strokeDasharray="6 3"
            label={{ value: '低血糖 3.9', fill: '#ef4444', fontSize: 10, position: 'right' }}
          />

          {/* Data lines */}
          {filter === 'all' ? (
            <>
              <Line
                type="monotone"
                dataKey="value"
                name="血糖值"
                stroke="#06b6d4"
                strokeWidth={2}
                dot={{ r: 3, fill: '#06b6d4' }}
                activeDot={{ r: 5, stroke: '#06b6d4', strokeWidth: 2 }}
              />
            </>
          ) : (
            <Line
              type="monotone"
              dataKey="value"
              name={TYPE_LABELS[filter] || filter}
              stroke={TYPE_COLORS[filter] || '#06b6d4'}
              strokeWidth={2}
              dot={{ r: 3, fill: TYPE_COLORS[filter] || '#06b6d4' }}
              activeDot={{ r: 5 }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
