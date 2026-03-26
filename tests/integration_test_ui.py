"""
UI 组件集成测试

测试图表组件与后端 API 的集成
"""

import json
import urllib.request
from pathlib import Path


def test_patient_api():
    """测试患者详情 API"""
    print("\n[测试] 患者详情 API")
    try:
        req = urllib.request.Request('http://localhost:8001/api/patients/PAT_bjhl2nvy9f')
        data = json.loads(urllib.request.urlopen(req, timeout=5).read())
        
        glucose_history = data.get('glucose_history', [])
        print(f"  ✓ 血糖记录数: {len(glucose_history)}")
        
        if glucose_history:
            # 转换为 GlucoseChart 组件需要的格式
            chart_data = [
                {
                    'timestamp': f"2026-03-{20+i:02d}T08:00:00",
                    'value': record.get('value', 0),
                    'type': 'fasting'
                }
                for i, record in enumerate(glucose_history[:5])
            ]
            print(f"  ✓ 图表数据格式: {len(chart_data)} 条")
            return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False


def test_evolution_api():
    """测试自进化报告 API"""
    print("\n[测试] 自进化报告 API")
    try:
        req = urllib.request.Request('http://localhost:8001/api/evolution/report')
        data = json.loads(urllib.request.urlopen(req, timeout=5).read())
        
        iterations = data.get('iterations', [])
        print(f"  ✓ 迭代次数: {len(iterations)}")
        print(f"  ✓ 总体提升: {data.get('improvement', 0)}")
        
        # 转换为 EvolutionTimeline 组件需要的格式
        if iterations:
            timeline_data = [
                {
                    'iteration': i,
                    'timestamp': iter_data.get('timestamp', ''),
                    'overall_score': iter_data.get('overall_score', 0),
                    'medical_accuracy': iter_data.get('dimensions', {}).get('medical_accuracy', 0),
                    'safety': iter_data.get('dimensions', {}).get('safety', 0),
                    'completeness': iter_data.get('dimensions', {}).get('completeness', 0),
                    'personalization': iter_data.get('dimensions', {}).get('personalization', 0),
                    'consistency': iter_data.get('dimensions', {}).get('consistency', 0),
                    'changes': iter_data.get('prompt_changes', [])
                }
                for i, iter_data in enumerate(iterations)
            ]
            print(f"  ✓ 时间线数据格式: {len(timeline_data)} 条")
            return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False


def test_consultation_api():
    """测试咨询 API"""
    print("\n[测试] 咨询 API")
    try:
        req = urllib.request.Request(
            'http://localhost:8001/api/consultation',
            data=json.dumps({
                'patient_id': 'PAT_bjhl2nvy9f',
                'query': '我的血糖有点高，需要调整药物吗？'
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        
        print(f"  ✓ 咨询响应: {data.get('primary_response', '')[:50]}...")
        print(f"  ✓ 专家意见数: {len(data.get('expert_opinions', {}))}")
        return True
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("UI 组件集成测试")
    print("=" * 60)
    
    results = []
    results.append(("患者详情 API", test_patient_api()))
    results.append(("自进化报告 API", test_evolution_api()))
    results.append(("咨询 API", test_consultation_api()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")
    
    passed_count = sum(1 for _, p in results if p)
    print(f"\n总计: {passed_count}/{len(results)} 通过")
    
    return all(p for _, p in results)


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
