"""快速修复测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents import GlucoseManagementWorkflow

# 测试 Mock 模式
workflow = GlucoseManagementWorkflow(use_mock=True)
result = workflow.process_patient_query('PAT_001', '空腹血糖8.5正常吗？', enable_parallel=False)

print('[OK] Mock 模式测试通过')
print(f'查询: {result["query"]}')
print(f'回答长度: {len(result["primary_response"])} 字符')
print(f'处理时间: {result["processing_time"]:.2f}s')

# 测试真实 Agent 初始化（无需 API key，会降级到 Mock）
try:
    workflow2 = GlucoseManagementWorkflow(use_mock=False)
    print('[OK] 真实 Agent 初始化成功')
except Exception as e:
    print(f'[WARN] 真实 Agent 初始化: {e}')
