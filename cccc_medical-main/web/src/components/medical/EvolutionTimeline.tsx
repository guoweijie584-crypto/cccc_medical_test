/**
 * EvolutionTimeline - 自进化时间线组件
 * 
 * Props:
 * - iterations: IterationData[] - 迭代数据
 * - height?: number - 高度（默认 400）
 */

import React from 'react';

export interface IterationData {
  iteration: number;
  timestamp: string;
  overall_score: number;
  medical_accuracy: number;
  safety: number;
  completeness: number;
  personalization: number;
  consistency: number;
  changes?: ChangeRecord[];
}

export interface ChangeRecord {
  type: 'prompt' | 'memory';
  agent?: string;
  description: string;
  before_score?: number;
  after_score?: number;
}

export interface EvolutionTimelineProps {
  iterations: IterationData[];
  height?: number;
}

export const EvolutionTimeline: React.FC<EvolutionTimelineProps> = ({
  iterations,
  height = 400
}) => {
  if (!iterations || iterations.length === 0) {
    return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
      暂无进化数据
    </div>;
  }

  const width = 700;
  const padding = { top: 40, right: 30, bottom: 60, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // 计算数值范围
  const allScores = iterations.flatMap(i => [
    i.overall_score,
    i.medical_accuracy,
    i.safety
  ]);
  const minScore = Math.min(...allScores, 5);
  const maxScore = Math.max(...allScores, 10);

  // 比例尺
  const xScale = (index: number) => padding.left + (index / (iterations.length - 1 || 1)) * chartWidth;
  const yScale = (score: number) => padding.top + chartHeight - ((score - minScore) / (maxScore - minScore)) * chartHeight;

  // 生成折线路径
  const createPath = (getter: (i: IterationData) => number) => {
    return iterations.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(getter(d))}`).join(' ');
  };

  const colors = {
    overall: '#1890ff',
    medical: '#52c41a',
    safety: '#faad14',
    completeness: '#722ed1',
    personalization: '#eb2f96',
    consistency: '#13c2c2'
  };

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* 图表 */}
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ background: '#fafafa' }}>
        {/* 网格 */}
        {[0, 0.2, 0.4, 0.6, 0.8, 1].map(t => (
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

        {/* 总体得分线 */}
        <path d={createPath(d => d.overall_score)} fill="none" stroke={colors.overall} strokeWidth={3} />
        
        {/* 各维度线 */}
        <path d={createPath(d => d.medical_accuracy)} fill="none" stroke={colors.medical} strokeWidth={2} strokeDasharray="5,5" />
        <path d={createPath(d => d.safety)} fill="none" stroke={colors.safety} strokeWidth={2} strokeDasharray="5,5" />

        {/* 数据点 */}
        {iterations.map((d, i) => (
          <g key={i}>
            <circle cx={xScale(i)} cy={yScale(d.overall_score)} r={6} fill={colors.overall} stroke="#fff" strokeWidth={2} />
            <text x={xScale(i)} y={yScale(d.overall_score) - 10} textAnchor="middle" fontSize={11} fontWeight="bold" fill={colors.overall}>
              {d.overall_score.toFixed(2)}
            </text>
          </g>
        ))}

        {/* 坐标轴 */}
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={padding.top + chartHeight} stroke="#333" />
        <line x1={padding.left} y1={padding.top + chartHeight} x2={padding.left + chartWidth} y2={padding.top + chartHeight} stroke="#333" />

        {/* Y轴标签 */}
        {[0, 0.2, 0.4, 0.6, 0.8, 1].map(t => {
          const value = minScore + (1 - t) * (maxScore - minScore);
          return (
            <text key={`y-${t}`} x={padding.left - 10} y={padding.top + t * chartHeight + 5} textAnchor="end" fontSize={11} fill="#666">
              {value.toFixed(1)}
            </text>
          );
        })}

        {/* X轴标签 */}
        {iterations.map((d, i) => (
          <text key={`x-${i}`} x={xScale(i)} y={padding.top + chartHeight + 20} textAnchor="middle" fontSize={12} fill="#666">
            迭代 {d.iteration}
          </text>
        ))}

        {/* 标题 */}
        <text x={width / 2} y={20} textAnchor="middle" fontSize={16} fontWeight="bold" fill="#333">
          自进化迭代趋势
        </text>

        {/* 图例 */}
        <g transform={`translate(${width - 150}, 30)`}>
          <rect x={0} y={0} width={140} height={80} fill="#fff" stroke="#e0e0e0" rx={4} />
          <line x1={10} y1={15} x2={30} y2={15} stroke={colors.overall} strokeWidth={3} />
          <text x={35} y={19} fontSize={11} fill="#333">总体得分</text>
          <line x1={10} y1={35} x2={30} y2={35} stroke={colors.medical} strokeWidth={2} strokeDasharray="5,5" />
          <text x={35} y={39} fontSize={11} fill="#333">医学准确性</text>
          <line x1={10} y1={55} x2={30} y2={55} stroke={colors.safety} strokeWidth={2} strokeDasharray="5,5" />
          <text x={35} y={59} fontSize={11} fill="#333">安全性</text>
        </g>
      </svg>

      {/* 变更记录表 */}
      <div style={{ marginTop: 20, padding: 15, background: '#f5f5f5', borderRadius: 8 }}>
        <h4 style={{ margin: '0 0 10px 0', fontSize: 14 }}>优化变更记录</h4>
        {iterations.filter(i => i.changes && i.changes.length > 0).map(iter => (
          <div key={iter.iteration} style={{ marginBottom: 10 }}>
            <div style={{ fontWeight: 'bold', fontSize: 13, color: '#1890ff', marginBottom: 5 }}>
              迭代 {iter.iteration} ({new Date(iter.timestamp).toLocaleDateString('zh-CN')})
            </div>
            <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12 }}>
              {iter.changes?.map((change, idx) => (
                <li key={idx} style={{ marginBottom: 3 }}>
                  {change.type === 'prompt' ? '提示词' : '记忆'}优化
                  {change.agent && ` [${change.agent}]`}: 
                  {change.description}
                  {change.before_score && change.after_score && (
                    <span style={{ color: '#52c41a', marginLeft: 8 }}>
                      {change.before_score.toFixed(1)} → {change.after_score.toFixed(1)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
        {iterations.filter(i => i.changes && i.changes.length > 0).length === 0 && (
          <div style={{ fontSize: 12, color: '#999' }}>暂无变更记录</div>
        )}
      </div>
    </div>
  );
};

export default EvolutionTimeline;
