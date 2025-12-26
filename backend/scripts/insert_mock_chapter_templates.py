"""
Insert mock course chapter templates for testing.
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.models.database import get_db


async def insert_mock_templates():
    """Insert mock course chapter templates."""
    db = await get_db()

    # Mock template 1: 信息安全技术 (Information Security Technology)
    template1_id = str(uuid4())
    template1_chapters = [
        {
            "week": 1,
            "topic": "信息安全概述与威胁分析",
            "content_summary": "本周将介绍信息安全的基本概念、目标和重要性，分析当前网络环境面临的主要威胁类型，包括恶意软件、网络攻击、社会工程学等。学生将了解信息安全的CIA三要素（机密性、完整性、可用性）以及信息安全管理的基本框架。",
            "key_concepts": ["信息安全定义", "CIA三要素", "威胁类型分析", "安全管理框架"]
        },
        {
            "week": 2,
            "topic": "密码学基础与加密技术",
            "content_summary": "学习密码学的基本原理，包括对称加密、非对称加密和哈希函数。重点掌握常见加密算法（如AES、RSA）的工作原理和应用场景，了解数字签名和证书的作用。通过实验演示加密技术在实际中的应用。",
            "key_concepts": ["对称加密", "非对称加密", "哈希函数", "数字签名", "PKI体系"]
        },
        {
            "week": 3,
            "topic": "网络安全防护技术",
            "content_summary": "介绍防火墙、入侵检测系统(IDS)、入侵防御系统(IPS)等网络安全设备的工作原理和配置方法。学习网络隔离、访问控制列表(ACL)、VPN技术等网络安全防护措施，通过实验配置简单的防火墙规则。",
            "key_concepts": ["防火墙技术", "IDS/IPS", "ACL配置", "VPN原理", "网络隔离"]
        },
        {
            "week": 4,
            "topic": "操作系统安全加固",
            "content_summary": "学习Windows和Linux操作系统的安全配置和加固方法，包括用户权限管理、安全策略设置、系统补丁管理、日志审计等。通过实验练习账户安全配置、防病毒软件部署和系统安全审计。",
            "key_concepts": ["权限管理", "安全策略", "补丁管理", "日志审计", "系统加固"]
        }
    ]

    await db.execute(
        """
        INSERT INTO course_chapter_templates (
            id, course_name, subject, grade, start_week, end_week,
            total_weeks, chapters, use_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            template1_id,
            "信息安全技术",
            "信息安全",
            "大二",
            1,
            4,
            4,
            json.dumps(template1_chapters, ensure_ascii=False),
            0,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
        commit=True,
    )
    print(f"✓ Inserted template 1: 信息安全技术 (ID: {template1_id})")

    # Mock template 2: Python程序设计 (Python Programming)
    template2_id = str(uuid4())
    template2_chapters = [
        {
            "week": 1,
            "topic": "Python基础语法与数据类型",
            "content_summary": "介绍Python语言的特点和应用领域，学习Python的基本语法规则、变量命名、数据类型（整数、浮点数、字符串、布尔值）。掌握基本的输入输出操作和简单的数学运算，通过练习编写第一个Python程序。",
            "key_concepts": ["Python简介", "变量与数据类型", "基本运算符", "输入输出函数", "代码规范"]
        },
        {
            "week": 2,
            "topic": "控制流程：条件与循环",
            "content_summary": "学习程序的控制流程结构，包括if-elif-else条件判断、for循环和while循环。掌握循环控制语句（break、continue）的使用，通过编程练习解决实际问题，如成绩判断、数字求和等。",
            "key_concepts": ["条件判断", "for循环", "while循环", "break和continue", "逻辑运算符"]
        },
        {
            "week": 3,
            "topic": "列表、元组与字典",
            "content_summary": "深入学习Python的复合数据类型：列表（list）、元组（tuple）和字典（dict）。掌握各种数据结构的创建、访问、修改和常用方法，理解可变类型与不可变类型的区别，通过实例练习数据的存储和处理。",
            "key_concepts": ["列表操作", "元组特性", "字典应用", "数据结构选择", "列表推导式"]
        },
        {
            "week": 4,
            "topic": "函数定义与模块使用",
            "content_summary": "学习函数的定义、参数传递和返回值，理解函数的作用域和变量生命周期。掌握模块的导入和使用方法，了解Python标准库的常用模块（如math、random、datetime）。通过编写函数实现代码的模块化和复用。",
            "key_concepts": ["函数定义", "参数类型", "返回值", "作用域", "模块导入", "标准库"]
        },
        {
            "week": 5,
            "topic": "文件操作与异常处理",
            "content_summary": "学习文件的读写操作，包括文本文件和二进制文件的处理。掌握异常处理机制（try-except-finally），学会处理常见的程序错误。通过实验练习文件数据的读取、处理和保存，编写健壮的程序代码。",
            "key_concepts": ["文件读写", "上下文管理器", "异常类型", "try-except语句", "文件路径处理"]
        },
        {
            "week": 6,
            "topic": "面向对象编程基础",
            "content_summary": "介绍面向对象编程的基本概念，包括类、对象、属性和方法。学习类的定义和实例化，掌握构造函数、类方法和实例方法的使用。通过实例设计简单的类，理解封装的思想和对象的生命周期。",
            "key_concepts": ["类与对象", "属性和方法", "构造函数", "self关键字", "封装原则"]
        }
    ]

    await db.execute(
        """
        INSERT INTO course_chapter_templates (
            id, course_name, subject, grade, start_week, end_week,
            total_weeks, chapters, use_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            template2_id,
            "Python程序设计",
            "计算机",
            "大一",
            1,
            6,
            6,
            json.dumps(template2_chapters, ensure_ascii=False),
            0,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
        commit=True,
    )
    print(f"✓ Inserted template 2: Python程序设计 (ID: {template2_id})")

    # Mock template 3: 数据库原理与应用 (Database Principles)
    template3_id = str(uuid4())
    template3_chapters = [
        {
            "week": 1,
            "topic": "数据库系统概述",
            "content_summary": "介绍数据库的基本概念、发展历史和应用场景，讲解数据库系统的组成和特点。对比文件系统与数据库管理系统的区别，介绍常见的数据库产品（如MySQL、Oracle、SQL Server）及其应用领域。",
            "key_concepts": ["数据库定义", "DBMS特点", "数据模型", "数据库系统结构", "数据库产品对比"]
        },
        {
            "week": 2,
            "topic": "关系数据库与关系代数",
            "content_summary": "学习关系模型的基本概念，包括关系、元组、属性和域。掌握关系的完整性约束（实体完整性、参照完整性、用户定义完整性），理解关系代数的基本操作（选择、投影、连接）及其在查询中的应用。",
            "key_concepts": ["关系模型", "关系运算", "完整性约束", "主键外键", "关系代数操作"]
        },
        {
            "week": 3,
            "topic": "SQL语言基础：DDL与DML",
            "content_summary": "系统学习SQL语言，掌握数据定义语言(DDL)的使用，包括创建、修改和删除数据库对象。学习数据操纵语言(DML)，包括INSERT、UPDATE、DELETE和SELECT语句的语法和应用，通过实验练习各种SQL操作。",
            "key_concepts": ["DDL语句", "DML语句", "CREATE TABLE", "INSERT/UPDATE/DELETE", "SELECT查询"]
        },
        {
            "week": 4,
            "topic": "复杂查询与多表连接",
            "content_summary": "深入学习SQL查询技术，包括聚合函数、分组查询、排序和子查询。重点掌握多表连接操作（内连接、外连接、交叉连接），学习复杂查询的编写技巧。通过实例练习编写高效的多表查询语句。",
            "key_concepts": ["聚合函数", "GROUP BY", "多表连接", "子查询", "嵌套查询", "查询优化"]
        },
        {
            "week": 5,
            "topic": "数据库设计：概念设计与逻辑设计",
            "content_summary": "学习数据库设计的方法和步骤，掌握ER模型的绘制和实体关系分析。学习从ER图到关系模式的转换过程，理解范式理论（第一范式、第二范式、第三范式），掌握数据库规范化的方法和技巧。",
            "key_concepts": ["ER模型", "实体关系图", "关系模式转换", "范式理论", "规范化设计"]
        }
    ]

    await db.execute(
        """
        INSERT INTO course_chapter_templates (
            id, course_name, subject, grade, start_week, end_week,
            total_weeks, chapters, use_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            template3_id,
            "数据库原理与应用",
            "计算机",
            "大二",
            1,
            5,
            5,
            json.dumps(template3_chapters, ensure_ascii=False),
            0,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
        commit=True,
    )
    print(f"✓ Inserted template 3: 数据库原理与应用 (ID: {template3_id})")

    # Mock template 4: Web前端开发 (Web Frontend Development)
    template4_id = str(uuid4())
    template4_chapters = [
        {
            "week": 1,
            "topic": "HTML5基础与页面结构",
            "content_summary": "介绍Web前端开发的基本概念和技术栈，学习HTML5的基本语法和常用标签。掌握页面结构的构建方法，包括标题、段落、列表、链接、图片等元素的使用。通过实验创建第一个网页，理解HTML文档的结构和语义化标签。",
            "key_concepts": ["HTML5新特性", "常用标签", "语义化标签", "页面结构", "表单元素"]
        },
        {
            "week": 2,
            "topic": "CSS3样式与布局",
            "content_summary": "系统学习CSS3样式表的使用，包括选择器、盒模型、定位和浮动。掌握常用的CSS属性和布局技术，学习响应式设计的基本原理。通过实验美化网页外观，实现常见的页面布局效果（如导航栏、卡片布局等）。",
            "key_concepts": ["CSS选择器", "盒模型", "Flexbox布局", "Grid布局", "响应式设计"]
        },
        {
            "week": 3,
            "topic": "JavaScript基础与DOM操作",
            "content_summary": "学习JavaScript的基本语法、数据类型和控制结构。掌握DOM（文档对象模型）的概念和操作方法，包括元素选择、内容修改、样式控制和事件处理。通过实验实现网页的动态交互效果，如按钮点击、表单验证等。",
            "key_concepts": ["JavaScript语法", "DOM操作", "事件处理", "函数定义", "变量作用域"]
        }
    ]

    await db.execute(
        """
        INSERT INTO course_chapter_templates (
            id, course_name, subject, grade, start_week, end_week,
            total_weeks, chapters, use_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            template4_id,
            "Web前端开发",
            "计算机",
            "大一",
            1,
            3,
            3,
            json.dumps(template4_chapters, ensure_ascii=False),
            0,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ),
        commit=True,
    )
    print(f"✓ Inserted template 4: Web前端开发 (ID: {template4_id})")

    print("\n✅ All mock templates inserted successfully!")
    print(f"\nTotal templates: 4")
    print("- 信息安全技术: 4周")
    print("- Python程序设计: 6周")
    print("- 数据库原理与应用: 5周")
    print("- Web前端开发: 3周")


async def verify_templates():
    """Verify that templates were inserted correctly."""
    db = await get_db()

    rows = await db.fetch_all(
        "SELECT course_name, subject, grade, start_week, end_week, total_weeks FROM course_chapter_templates ORDER BY created_at"
    )

    print("\n📋 Verification - Templates in database:")
    print("-" * 80)
    for row in rows:
        print(f"课程: {row['course_name']:<20} | 学科: {row['subject']:<10} | 年级: {row['grade']:<8} | 周数: {row['start_week']}-{row['end_week']} (共{row['total_weeks']}周)")
    print("-" * 80)


async def main():
    """Main function."""
    print("🚀 Starting mock data insertion...\n")

    try:
        await insert_mock_templates()
        await verify_templates()
        print("\n✨ Done!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
