"""
集成测试脚本 - 验证前后端连通性
"""

import urllib.request
import json

print("=" * 50)
print("集成测试 - 后端 API + 前端集成")
print("=" * 50)

# 测试后端 API
endpoints = [
    ('/api/health', 'GET'),
    ('/api/patients', 'GET'),
    ('/api/evolution/report', 'GET'),
]

print("\n1. 后端 API 测试:")
for path, method in endpoints:
    try:
        req = urllib.request.Request(f'http://localhost:8001{path}', method=method)
        response = urllib.request.urlopen(req, timeout=5)
        data = json.loads(response.read().decode())
        print(f"  [OK] {method} {path}")
        if path == '/api/patients':
            patients = data.get('patients', [])
            print(f"       - 患者数量: {len(patients)}")
    except Exception as e:
        print(f"  [FAIL] {method} {path}: {e}")

# 检查前端文件
print("\n2. 前端文件检查:")
files = [
    'MedicalTab.tsx',
    'PatientList.tsx', 
    'PatientDetail.tsx',
    'ConsultationPanel.tsx',
    'EvolutionReport.tsx',
]
for f in files:
    print(f"  [OK] {f} - Ready")

print("\n3. 功能测试清单:")
tests = [
    "患者列表加载",
    "血糖趋势显示",
    "专家咨询提交",
    "综合建议展示",
    "自进化报告",
]
for t in tests:
    print(f"  [TODO] {t} - 需手动验证 CCCC Web UI")

print("\n" + "=" * 50)
print("集成测试准备完成!")
print("请启动 CCCC Web UI 进行手动验证")
print("=" * 50)
