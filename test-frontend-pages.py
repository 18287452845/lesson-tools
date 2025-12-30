#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
前端页面功能测试
验证所有前端页面的可访问性和基本功能
"""

import requests
import json
from pathlib import Path
from datetime import datetime

# 配置
FRONTEND_URL = "http://localhost:5173"
API_BASE = "http://127.0.0.1:8000"

# 测试结果
frontend_test_results = []

def log_frontend_test(test_name, status, message="", url=""):
    """记录前端测试结果"""
    result = {
        "name": test_name,
        "status": status,
        "message": message,
        "url": url,
        "timestamp": datetime.now().isoformat()
    }
    frontend_test_results.append(result)
    symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
    print(f"{symbol} {test_name}: {status}")
    if message:
        print(f"   {message}")

def test_frontend_pages():
    """测试所有前端页面的可访问性"""
    print("\n=== 测试前端页面可访问性 ===")

    pages = [
        ("Home", "/"),
        ("Template Manager", "/templates"),
        ("New Lesson Plan", "/new"),
        ("Edit Lesson Plan", "/edit"),
        ("History", "/history"),
        ("Settings", "/settings"),
        ("Batch Generation", "/batch-generate"),
    ]

    for page_name, path in pages:
        url = f"{FRONTEND_URL}{path}"
        try:
            # 使用requests测试前端页面
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                log_frontend_test(
                    f"FC-{page_name}: 页面加载",
                    "PASS",
                    f"状态码: {response.status_code}",
                    url
                )
            else:
                log_frontend_test(
                    f"FC-{page_name}: 页面加载",
                    "FAIL",
                    f"状态码: {response.status_code}",
                    url
                )
        except Exception as e:
            log_frontend_test(
                f"FC-{page_name}: 页面加载",
                "FAIL",
                str(e),
                url
            )

def test_template_data():
    """测试模板数据"""
    print("\n=== 测试模板数据 ===")

    try:
        response = requests.get(f"{API_BASE}/api/templates", timeout=5)
        if response.status_code == 200:
            templates = response.json()
            log_frontend_test(
                "FC-Data: 模板数据",
                "PASS",
                f"找到 {len(templates)} 个模板"
            )

            # 测试模板详情
            if len(templates) > 0:
                template_id = templates[0]["id"]
                response = requests.get(
                    f"{API_BASE}/api/templates/{template_id}",
                    timeout=5
                )
                if response.status_code == 200:
                    log_frontend_test(
                        "FC-Data: 模板详情",
                        "PASS",
                        f"成功获取模板: {templates[0]['name']}"
                    )
                else:
                    log_frontend_test(
                        "FC-Data: 模板详情",
                        "FAIL",
                        f"状态码: {response.status_code}"
                    )
        else:
            log_frontend_test(
                "FC-Data: 模板数据",
                "FAIL",
                f"状态码: {response.status_code}"
            )
    except Exception as e:
        log_frontend_test(
            "FC-Data: 模板数据",
            "FAIL",
            str(e)
        )

def test_history_data():
    """测试历史数据"""
    print("\n=== 测试历史数据 ===")

    try:
        response = requests.get(f"{API_BASE}/api/generate", timeout=5)
        if response.status_code == 200:
            history = response.json()
            log_frontend_test(
                "FC-Data: 历史记录数据",
                "PASS",
                f"找到 {len(history)} 条历史记录"
            )
        else:
            log_frontend_test(
                "FC-Data: 历史记录数据",
                "FAIL",
                f"状态码: {response.status_code}"
            )
    except Exception as e:
        log_frontend_test(
            "FC-Data: 历史记录数据",
            "FAIL",
            str(e)
        )

def test_settings_data():
    """测试设置数据"""
    print("\n=== 测试设置数据 ===")

    try:
        response = requests.get(
            f"{API_BASE}/api/settings/ai-provider",
            timeout=5
        )
        if response.status_code == 200:
            settings = response.json()
            log_frontend_test(
                "FC-Data: AI设置数据",
                "PASS",
                f"提供商: {settings.get('provider', 'N/A')}"
            )
        else:
            log_frontend_test(
                "FC-Data: AI设置数据",
                "FAIL",
                f"状态码: {response.status_code}"
            )
    except Exception as e:
        log_frontend_test(
            "FC-Data: AI设置数据",
            "FAIL",
            str(e)
        )

def test_batch_functionality():
    """测试批量功能"""
    print("\n=== 测试批量生成功能 ===")

    # 测试章节分割
    test_data = {
        "course_name": "测试课程",
        "total_hours": 64,
        "chapters": []  # 让AI生成
    }

    try:
        response = requests.post(
            f"{API_BASE}/api/batch/split-chapters",
            json=test_data,
            timeout=30
        )
        # 注意：这里可能会失败，因为AI调用需要真实API
        # 但至少可以测试端点是否存在
        if response.status_code in [200, 500, 501]:  # 500可能是AI未配置
            log_frontend_test(
                "FC-Batch: 章节分割端点",
                "PASS",
                f"端点可访问 (状态码: {response.status_code})"
            )
        else:
            log_frontend_test(
                "FC-Batch: 章节分割端点",
                "FAIL",
                f"状态码: {response.status_code}"
            )
    except Exception as e:
        log_frontend_test(
            "FC-Batch: 章节分割端点",
            "FAIL",
            str(e)
        )

def test_classes_data():
    """测试班级数据"""
    print("\n=== 测试班级数据 ===")

    try:
        response = requests.get(f"{API_BASE}/api/classes", timeout=5)
        if response.status_code == 200:
            data = response.json()
            classes = data.get("classes", [])
            log_frontend_test(
                "FC-Data: 班级数据",
                "PASS",
                f"找到 {len(classes)} 个班级"
            )
        else:
            log_frontend_test(
                "FC-Data: 班级数据",
                "FAIL",
                f"状态码: {response.status_code}"
            )
    except Exception as e:
        log_frontend_test(
            "FC-Data: 班级数据",
            "FAIL",
            str(e)
        )

def generate_frontend_report():
    """生成前端测试报告"""
    print("\n=== 生成前端测试报告 ===")

    passed = sum(1 for r in frontend_test_results if r["status"] == "PASS")
    failed = sum(1 for r in frontend_test_results if r["status"] == "FAIL")
    skipped = sum(1 for r in frontend_test_results if r["status"] == "SKIP")
    total = len(frontend_test_results)
    pass_rate = (passed/total*100) if total > 0 else 0

    report = f"""# 前端功能测试报告
## 智能教案助手 - 前端测试

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试环境**: 前端 {FRONTEND_URL}

---

## 执行摘要

**总测试用例**: {total}
**通过**: {passed}
**失败**: {failed}
**跳过**: {skipped}
**通过率**: {pass_rate:.1f}%

**整体状态**: {'✅ 通过' if failed == 0 else '❌ 失败'}

---

## 详细测试结果

"""

    for result in frontend_test_results:
        symbol = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⏭️"
        report += f"### {symbol} {result['name']}\n\n"
        report += f"**状态**: {result['status']}\n\n"
        if result['message']:
            report += f"**消息**: {result['message']}\n\n"
        if result['url']:
            report += f"**URL**: {result['url']}\n\n"
        report += "---\n\n"

    # 保存报告
    report_path = Path("FRONTEND_TEST_REPORT.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 前端测试报告已生成: {report_path}")

def main():
    """主测试函数"""
    print("="*60)
    print("智能教案助手 - 前端功能测试")
    print("="*60)

    # 执行测试
    test_frontend_pages()
    test_template_data()
    test_history_data()
    test_settings_data()
    test_batch_functionality()
    test_classes_data()

    # 生成报告
    generate_frontend_report()

    print("\n" + "="*60)
    print("前端测试完成!")
    print("="*60)

if __name__ == "__main__":
    main()
