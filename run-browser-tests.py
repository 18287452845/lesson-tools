#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
浏览器自动化测试脚本
测试智能教案助手的所有功能
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

# 配置
BASE_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"

# 测试结果
test_results = []

def log_test(test_name, status, message="", details=""):
    """记录测试结果"""
    result = {
        "name": test_name,
        "status": status,  # "PASS", "FAIL", "SKIP"
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results.append(result)
    symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
    print(f"{symbol} {test_name}: {status}")
    if message:
        print(f"   {message}")

def test_backend_health():
    """测试后端健康检查"""
    print("\n=== 测试后端健康检查 ===")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            log_test("TC-001: 后端根路径", "PASS", f"状态码: {response.status_code}")
        else:
            log_test("TC-001: 后端根路径", "FAIL", f"状态码: {response.status_code}")
    except Exception as e:
        log_test("TC-001: 后端根路径", "FAIL", str(e))

    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            log_test("TC-002: Swagger文档", "PASS", "API文档可访问")
        else:
            log_test("TC-002: Swagger文档", "FAIL", f"状态码: {response.status_code}")
    except Exception as e:
        log_test("TC-002: Swagger文档", "FAIL", str(e))

def test_templates_api():
    """测试模板API"""
    print("\n=== 测试Templates API ===")

    # TC-003: 获取模板列表
    try:
        response = requests.get(f"{BASE_URL}/api/templates", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("TC-003: GET /api/templates", "PASS",
                    f"返回 {len(data)} 个模板", json.dumps(data, ensure_ascii=False)[:200])
        else:
            log_test("TC-003: GET /api/templates", "FAIL", f"状态码: {response.status_code}")
    except Exception as e:
        log_test("TC-003: GET /api/templates", "FAIL", str(e))

    # TC-004: 获取标准字段
    try:
        response = requests.get(f"{BASE_URL}/api/templates/standard-fields", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("TC-004: GET /standard-fields", "PASS",
                    f"标准字段: {len(data)} 个", str(data)[:200])
        else:
            log_test("TC-004: GET /standard-fields", "FAIL", f"状态码: {response.status_code}")
    except Exception as e:
        log_test("TC-004: GET /standard-fields", "FAIL", str(e))

def test_generate_api():
    """测试生成API"""
    print("\n=== 测试Generate API ===")

    # TC-005: 获取生成历史
    try:
        response = requests.get(f"{BASE_URL}/api/generate", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("TC-005: GET /api/generate (历史)", "PASS",
                    f"历史记录: {len(data)} 条")
        else:
            log_test("TC-005: GET /api/generate (历史)", "FAIL", f"状态码: {response.status_code}")
    except Exception as e:
        log_test("TC-005: GET /api/generate (历史)", "FAIL", str(e))

def test_settings_api():
    """测试设置API"""
    print("\n=== 测试Settings API ===")

    # TC-006: 获取AI提供商
    try:
        response = requests.get(f"{BASE_URL}/api/settings/ai-provider", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("TC-006: GET /ai-provider", "PASS",
                    f"当前提供商: {data.get('provider', 'N/A')}")
        else:
            log_test("TC-006: GET /ai-provider", "FAIL", f"状态码: {response.status_code}")
    except Exception as e:
        log_test("TC-006: GET /ai-provider", "FAIL", str(e))

    # TC-007: 获取应用信息
    try:
        response = requests.get(f"{BASE_URL}/api/settings/app-info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("TC-007: GET /app-info", "PASS",
                    f"应用名称: {data.get('name', 'N/A')}")
        else:
            log_test("TC-007: GET /app-info", "FAIL", f"状态码: {response.status_code}")
    except Exception as e:
        log_test("TC-007: GET /app-info", "FAIL", str(e))

def test_batch_api():
    """测试批量生成API"""
    print("\n=== 测试Batch API ===")

    # TC-008: 获取批量任务列表
    try:
        response = requests.get(f"{BASE_URL}/api/batch/tasks", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("TC-008: GET /batch/tasks", "PASS",
                    f"任务列表: {len(data.get('tasks', []))} 个")
        else:
            log_test("TC-008: GET /batch/tasks", "FAIL", f"状态码: {response.status_code}")
    except Exception as e:
        log_test("TC-008: GET /batch/tasks", "FAIL", str(e))

def test_classes_api():
    """测试班级API"""
    print("\n=== 测试Classes API ===")

    # TC-009: 获取班级列表
    try:
        response = requests.get(f"{BASE_URL}/api/classes", timeout=5)
        if response.status_code == 200:
            data = response.json()
            log_test("TC-009: GET /api/classes", "PASS",
                    f"班级列表: {len(data.get('classes', []))} 个")
        else:
            log_test("TC-009: GET /api/classes", "FAIL", f"状态码: {response.status_code}")
    except Exception as e:
        log_test("TC-009: GET /api/classes", "FAIL", str(e))

def generate_report():
    """生成测试报告"""
    print("\n=== 生成测试报告 ===")

    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")
    skipped = sum(1 for r in test_results if r["status"] == "SKIP")
    total = len(test_results)

    report = f"""# API功能测试报告
## 智能教案助手 - 后端API测试

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试环境**: 后端 {BASE_URL}

---

## 执行摘要

**总测试用例**: {total}
**通过**: {passed}
**失败**: {failed}
**跳过**: {skipped}
**通过率**: {passed/total*100:.1f}% （如果total > 0）

**整体状态**: {'✅ 通过' if failed == 0 else '❌ 失败'}

---

## 详细测试结果

"""

    for result in test_results:
        symbol = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⏭️"
        report += f"### {symbol} {result['name']}\n\n"
        report += f"**状态**: {result['status']}\n\n"
        if result['message']:
            report += f"**消息**: {result['message']}\n\n"
        if result['details']:
            report += f"**详情**: `{result['details'][:200]}...`\n\n"
        report += "---\n\n"

    # 保存报告
    report_path = Path("API_TEST_REPORT.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 测试报告已生成: {report_path}")

def main():
    """主测试函数"""
    print("="*60)
    print("智能教案助手 - API功能测试")
    print("="*60)

    # 执行测试
    test_backend_health()
    test_templates_api()
    test_generate_api()
    test_settings_api()
    test_batch_api()
    test_classes_api()

    # 生成报告
    generate_report()

    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)

if __name__ == "__main__":
    main()
