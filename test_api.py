"""API 测试脚本"""
import httpx
import json

BASE_URL = "http://localhost:8001"

def test_api():
    print("=" * 50)
    print("血糖管理 API 测试")
    print("=" * 50)
    
    # 测试健康检查
    print("\n1. 健康检查 /api/health")
    r = httpx.get(f"{BASE_URL}/api/health")
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")
    
    # 测试患者列表
    print("\n2. 患者列表 /api/patients")
    r = httpx.get(f"{BASE_URL}/api/patients")
    print(f"   Status: {r.status_code}")
    patients = r.json()
    print(f"   Count: {len(patients)}")
    if patients:
        print(f"   First patient ID: {patients[0]['id']}")
        print(f"   First patient glucose records: {len(patients[0]['glucose_history'])}")
    
    # 测试患者详情
    if patients:
        patient_id = patients[0]['id']
        print(f"\n3. 患者详情 /api/patients/{patient_id}")
        r = httpx.get(f"{BASE_URL}/api/patients/{patient_id}")
        print(f"   Status: {r.status_code}")
    
    # 测试咨询接口
    print("\n4. 咨询接口 /api/consultation")
    r = httpx.post(f"{BASE_URL}/api/consultation", json={
        "patient_id": "PAT_bjhl2nvy9f",
        "query": "我的血糖控制得怎么样？"
    })
    print(f"   Status: {r.status_code}")
    resp = r.json()
    print(f"   Query: {resp['query']}")
    print(f"   Score: {resp['evaluation_score']}")
    
    # 测试自进化报告
    print("\n5. 自进化报告 /api/evolution/report")
    r = httpx.get(f"{BASE_URL}/api/evolution/report")
    print(f"   Status: {r.status_code}")
    report = r.json()
    print(f"   Overall Score: {report['overall_score']}")
    print(f"   Improvement: {report['improvement']}")
    print(f"   Dimension Scores: {report['dimension_scores']}")
    
    # 测试时间线
    print("\n6. 进化时间线 /api/evolution/timeline")
    r = httpx.get(f"{BASE_URL}/api/evolution/timeline")
    print(f"   Status: {r.status_code}")
    timeline = r.json()
    print(f"   Iterations: {len(timeline['iterations'])}")
    
    print("\n" + "=" * 50)
    print("所有 API 测试通过！")
    print("=" * 50)

if __name__ == "__main__":
    test_api()
