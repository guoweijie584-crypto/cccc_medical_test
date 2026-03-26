/**
 * GlucoseChart - 血糖趋势折线图组件
 * 
 * Props:
 * - data: GlucoseRecord[] - 血糖历史数据
 * - height?: number - 图表高度（默认 300）
 */

import React from 'react';

export interface GlucoseRecord {
  timestamp: string;
  value: number;  // 血糖值 (mmol/L)
  type: 'fasting' | 'post_meal' | 'random';
}

export interface GlucoseChartProps {
  data: GlucoseRecord[];
  height?: number;
  showTarget?: boolean;
}

export const GlucoseChart: React.FC<GlucoseChartProps> = ({
  data,
  height = 300,
  showTarget = true
}) => {
  // 血糖目标范围
  const TARGET_MIN = 4.4;
  const TARGET_MAX = 7.0;
  const TARGET_POST_MAX = 10.0;

  if (!data || data.length === 0) {
    return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
      暂无血糖数据
    </div>;
  }

  // 计算图表尺寸
  const width = 600;
  const padding = { top: 20, right: 30, bottom: 40, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // 计算数值范围
  const values = data.map(d => d.value);
  const minValue = Math.min(...values, TARGET_MIN) - 1;
  const maxValue = Math.max(...values, TARGET_POST_MAX) + 1;

  // 比例尺
  const xScale = (index: number) => padding.left + (index / (data.length - 1 || 1)) * chartWidth;
  const yScale = (value: number) => padding.top + chartHeight - ((value - minValue) / (maxValue - minValue)) * chartHeight;

  // 生成路径
  const pathData = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.value)}`).join(' ');

  // 目标区域
  const targetY1 = yScale(TARGET_MAX);
  const targetY2 = yScale(TARGET_MIN);
  const targetHeight = targetY2 - targetY1;

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ background: '#fafafa' }}>
      {/* 目标范围背景 */}
      {showTarget && (
        <rect
          x={padding.left}
          y={targetY1}
          width={chartWidth}
          height={targetHeight}
          fill="#e6f7e6"
          opacity={0.5}
        />
      )}

      {/* 网格线 */}
      {[0, 0.25, 0.5, 0.75, 1].map(t => (
        <line
          key={`grid-${t}`}
          x1={padding.left}
          y1={padding.top + t * chartHeight}
          x2={padding.left + chartWidth}
          y2={padding.top + t * chartHeight}
          stroke="#e0e0e0"
          strokeDasharray="2,2"
        />
      ))}

      {/* 折线 */}
      <path
        d={pathData}
        fill="none"
        stroke="#1890ff"
        strokeWidth={2}
      />

      {/* 数据点 */}
      {data.map((d, i) => (
        <circle
          key={i}
          cx={xScale(i)}
          cy={yScale(d.value)}
          r={4}
          fill="#1890ff"
          stroke="#fff"
          strokeWidth={2}
        />
      ))}

      {/* Y轴 */}
      <line
        x1={padding.left}
        y1={padding.top}
        x2={padding.left}
        y2={padding.top + chartHeight}
        stroke="#333"
      />
      {[0, 0.25, 0.5, 0.75, 1].map(t => {
        const value = minValue + t * (maxValue - minValue);
        return (
          <text
            key={`y-label-${t}`}
            x={padding.left - 10}
            y={padding.top + (1 - t) * chartHeight + 5}
            textAnchor="end"
            fontSize={12}
            fill="#666"
          >
            {value.toFixed(1)}
          </text>
        );
      })}

      {/* X轴 */}
      <line
        x1={padding.left}
        y1={padding.top + chartHeight}
        x2={padding.left + chartWidth}
        y2={padding.top + chartHeight}
        stroke="#333"
      />
      {data.filter((_, i) => i % Math.ceil(data.length / 5) === 0).map((d, i) => (
        <text
          key={`x-label-${i}`}
          x={xScale(i * Math.ceil(data.length / 5))}
          y={padding.top + chartHeight + 20}
          textAnchor="middle"
          fontSize={10}
          fill="#666"
        >
          {new Date(d.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
        </text>
      ))}

      {/* 目标线标注 */}
      {showTarget && (
        <>
          <text x={width - 5} y={targetY1 + 12} textAnchor="end" fontSize={10} fill="#52c41a">
            目标上限 ({TARGET_MAX})
          </text>
          <text x={width - 5} y={targetY2 + 12} textAnchor="end" fontSize={10} fill="#52c41a">
            目标下限 ({TARGET_MIN})
          </text>
        </>
      )}

      {/* 标题 */}
      <text x={width / 2} y={15} textAnchor="middle" fontSize={14} fontWeight="bold" fill="#333">
        血糖趋势 (mmol/L)
      </text>
    </svg>
  );
};

export default GlucoseChart;
