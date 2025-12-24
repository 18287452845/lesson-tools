#!/usr/bin/env python3
"""
后端环境验证脚本

检查后端配置、依赖、服务文件和 API 端点
"""
import sys
import os

def check_dependencies():
    """检查所有依赖是否已安装"""
    print("=" * 60)
    print("1. 检查 Python 依赖...")
    print("=" * 60)

    # (package_name, import_name)
    required = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('python-docx', 'docx'),
        ('docxtpl', 'docxtpl'),
        ('aiosqlite', 'aiosqlite'),
        ('mammoth', 'mammoth'),
        ('htmldocx', 'htmldocx'),
        ('beautifulsoup4', 'bs4'),
        ('lxml', 'lxml'),
        ('jinja2', 'jinja2'),
    ]

    missing = []
    for pkg_name, import_name in required:
        try:
            __import__(import_name)
            print(f"✅ {pkg_name:20s} 已安装")
        except ImportError:
            print(f"❌ {pkg_name:20s} 未安装")
            missing.append(pkg_name)

    if missing:
        print(f"\n⚠️  缺少 {len(missing)} 个依赖包")
        return False

    print("\n✅ 所有依赖包已安装")
    return True


def check_service_files():
    """检查服务文件"""
    print("\n" + "=" * 60)
    print("2. 检查服务文件...")
    print("=" * 60)

    service_files = [
        'backend/services/docx_converter.py',
        'backend/services/jinja_protector.py',
        'backend/services/template_versioning.py',
        'backend/services/template_parser.py',
        'backend/services/document_renderer.py',
    ]

    all_exist = True
    for file_path in service_files:
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        print(f"{status} {file_path}")
        if not exists:
            all_exist = False

    if all_exist:
        print("\n✅ 所有服务文件存在")
    else:
        print("\n❌ 部分服务文件缺失")

    return all_exist


def check_fastapi_app():
    """检查 FastAPI 应用"""
    print("\n" + "=" * 60)
    print("3. 检查 FastAPI 应用...")
    print("=" * 60)

    try:
        from backend.main import app
        from backend.api import templates

        print("✅ FastAPI 应用导入成功")
        print(f"✅ 模板路由数: {len(templates.router.routes)}")

        # 检查关键端点
        routes = [r.path for r in templates.router.routes if hasattr(r, 'path')]

        key_endpoints = [
            '/templates/{template_id}/html',
            '/templates/{template_id}/save-html',
            '/templates/{template_id}/versions',
            '/templates/{template_id}/export/html',
        ]

        print("\n关键端点检查:")
        for endpoint in key_endpoints:
            if endpoint in routes:
                print(f"  ✅ {endpoint}")
            else:
                print(f"  ❌ {endpoint} 缺失")

        return True

    except Exception as e:
        print(f"❌ FastAPI 应用导入失败: {e}")
        return False


def check_env_file():
    """检查环境变量文件"""
    print("\n" + "=" * 60)
    print("4. 检查环境配置...")
    print("=" * 60)

    if os.path.exists('.env'):
        print("✅ .env 文件存在")

        # 读取 .env 文件
        with open('.env', 'r') as f:
            content = f.read()

        if 'AI_PROVIDER' in content:
            print("✅ AI_PROVIDER 已配置")
        else:
            print("⚠️  AI_PROVIDER 未配置")

        if 'DEEPSEEK_API_KEY' in content or 'ANTHROPIC_API_KEY' in content:
            print("✅ API_KEY 已配置")
        else:
            print("⚠️  需要配置 API_KEY")

        return True
    else:
        print("❌ .env 文件不存在")
        print("   请创建 .env 文件并配置 API 密钥")
        return False


def main():
    """主验证流程"""
    print("\n" + "=" * 60)
    print("后端环境验证")
    print("=" * 60 + "\n")

    results = []

    # 1. 检查依赖
    results.append(check_dependencies())

    # 2. 检查服务文件
    results.append(check_service_files())

    # 3. 检查 FastAPI 应用
    results.append(check_fastapi_app())

    # 4. 检查环境配置
    results.append(check_env_file())

    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)

    if all(results):
        print("✅ 后端环境配置完成，可以启动服务")
        print("\n启动命令:")
        print("  python run_backend.py")
        print("  或")
        print("  source venv/bin/activate && uvicorn backend.main:app --reload")
        return 0
    else:
        print("❌ 后端环境配置不完整，请检查上述错误")
        return 1


if __name__ == '__main__':
    sys.exit(main())
