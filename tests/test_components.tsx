/**
 * 图表组件测试
 * 
 * 使用方法:
 * 1. 将本文件复制到 web/src/components/medical/__tests__/
 * 2. 运行: npm test
 */

import React from 'react';
import { render } from '@testing-library/react';
import { GlucoseChart, EvolutionTimeline } from '../components/medical';

// 测试 GlucoseChart
const testGlucoseData = [
  { timestamp: '2026-03-20T08:00:00', value: 7.8, type: 'fasting' as const },
  { timestamp: '2026-03-21T08:00:00', value: 7.2, type: 'fasting' as const },
  { timestamp: '2026-03-22T08:00:00', value: 6.9, type: 'fasting' as const },
  { timestamp: '2026-03-23T08:00:00', value: 6.5, type: 'fasting' as const },
];

// 测试 EvolutionTimeline
const testIterationData = [
  {
    iteration: 0,
    timestamp: '2026-03-25T00:00:00',
    overall_score: 8.22,
    medical_accuracy: 8.45,
    safety: 7.92,
    completeness: 8.17,
    personalization: 7.61,
    consistency: 8.63,
    changes: []
  },
  {
    iteration: 1,
    timestamp: '2026-03-25T01:00:00',
    overall_score: 8.30,
    medical_accuracy: 8.55,
    safety: 8.00,
    completeness: 8.25,
    personalization: 7.70,
    consistency: 8.65,
    changes: [
      {
        type: 'prompt' as const,
        agent: 'pharmacist',
        description: '增加肾功能评估要求',
        before_score: 7.5,
        after_score: 8.2
      }
    ]
  }
];

// 简单的渲染测试
describe('Medical Components', () => {
  test('GlucoseChart renders without crashing', () => {
    const { container } = render(
      <GlucoseChart data={testGlucoseData} height={300} />
    );
    expect(container.querySelector('svg')).toBeTruthy();
  });

  test('GlucoseChart shows empty message when no data', () => {
    const { getByText } = render(<GlucoseChart data={[]} />);
    expect(getByText('暂无血糖数据')).toBeTruthy();
  });

  test('EvolutionTimeline renders without crashing', () => {
    const { container } = render(
      <EvolutionTimeline iterations={testIterationData} height={400} />
    );
    expect(container.querySelector('svg')).toBeTruthy();
  });

  test('EvolutionTimeline shows empty message when no data', () => {
    const { getByText } = render(<EvolutionTimeline iterations={[]} />);
    expect(getByText('暂无进化数据')).toBeTruthy();
  });
});

// 导出测试数据供其他测试使用
export { testGlucoseData, testIterationData };
