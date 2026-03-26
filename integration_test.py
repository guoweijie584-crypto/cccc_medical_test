"""
血糖管理系统 - 完整功能测试
验证后端 API + 数据完整性
"""
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

def test_endpoint(name, method, path, expected_status=200, payload=None):
    """测试单个端点"""
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            r = httpx.get(url, timeout=10)
        elif method == "POST":
            r = httpx.post(url, json=payload, timeout=10)
        
        success = r.status_code == expected_status
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if success else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {status} {method} {path} - Status: {r.status_code}")
        return success, r.json() if success else None
    except Exception as e:
        print(f"  {Colors.RED}FAIL{Colors.RESET} {method} {path} - Error: {e}")
        return False, None

def run_integration_test():
    print("=" * 60)
    print("血糖管理系统 - 完整功能测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().isoformat()}")
    print(f"API 地址: {BASE_URL}")
    print()
    
    results = []
    
    # 1. 健康检查
    print("【测试 1】健康检查")
    success, data = test_endpoint("health", "GET", "/api/health")
    results.append(("health", success))
    if data:
        print(f"       版本: {data.get('version')}")
    
    # 2. 患者列表
    print("\n【测试 2】患者列表")
    success, patients = test_endpoint("patients", "GET", "/api/patients")
    results.append(("patients_list", success))
    if patients:
        print(f"       患者数量: {len(patients)}")
        if len(patients) > 0:
            p = patients[0]
            print(f"       样例患者: {p.get('id')}, 血糖记录: {len(p.get('glucose_history', []))}条")
    
    # 3. 患者详情
    print("\n【测试 3】患者详情")
    if patients:
        patient_id = patients[0].get('id')
        success, data = test_endpoint("patient_detail", "GET", f"/api/patients/{patient_id}")
        results.append(("patient_detail", success))
    else:
        print(f"  {Colors.YELLOW}SKIP{Colors.RESET} 无患者数据")
        results.append(("patient_detail", False))
    
    # 4. 咨询接口
    print("\n【测试 4】咨询接口")
    consult_payload = {
        "patient_id": "PAT_bjhl2nvy9f",
        "query": "我的血糖控制得怎么样？"
    }
    success, data = test_endpoint("consultation", "POST", "/api/consultation", payload=consult_payload)
    results.append(("consultation", success))
    if data:
        print(f"       评分: {data.get('evaluation_score', {}).get('overall')}/10")
        opinions = data.get('expert_opinions', {})
        print(f"       专家意见: {len(opinions)}个Agent")
    
    # 5. 自进化报告
    print("\n【测试 5】自进化报告")
    success, data = test_endpoint("evolution_report", "GET", "/api/evolution/report")
    results.append(("evolution_report", success))
    if data:
        print(f"       总体评分: {data.get('overall_score')}/10")
        print(f"       改进幅度: +{data.get('improvement')}")
        dimensions = data.get('dimension_scores', {})
        print(f"       维度评分: {len(dimensions)}个维度")
    
    # 6. 进化时间线
    print("\n【测试 6】进化时间线")
    success, data = test_endpoint("evolution_timeline", "GET", "/api/evolution/timeline")
    results.append(("evolution_timeline", success))
    if data:
        iterations = data.get('iterations', [])
        print(f"       迭代次数: {len(iterations)}")
        if iterations:
            print(f"       初始评分: {iterations[0].get('overall_score')}")
            print(f"       最终评分: {iterations[-1].get('overall_score')}")
    
    # 汇总
    print("\n" + "=" * 60)
    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ 所有测试通过！系统可正常使用。{Colors.RESET}")
    else:
        failed = [name for name, s in results if not s]
        print(f"{Colors.RED}✗ 失败项: {', '.join(failed)}{Colors.RESET}")
    
    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = run_integration_test()
    exit(0 if success else 1)
