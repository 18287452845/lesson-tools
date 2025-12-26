"""
Add more mock course chapter templates for testing.
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


async def add_more_templates():
    """Add more mock course chapter templates."""
    db = await get_db()

    templates = []

    # Template 5: 计算机网络 (Computer Networks)
    template5 = {
        "id": str(uuid4()),
        "course_name": "计算机网络",
        "subject": "计算机",
        "grade": "大三",
        "start_week": 1,
        "end_week": 8,
        "total_weeks": 8,
        "chapters": [
            {
                "week": 1,
                "topic": "计算机网络概述与体系结构",
                "content_summary": "介绍计算机网络的基本概念、发展历程和应用领域。讲解网络的分类方法（按覆盖范围、拓扑结构等）。重点学习OSI七层模型和TCP/IP四层模型的结构、各层功能及协议。理解协议、服务和接口的关系，掌握数据封装与解封装过程。",
                "key_concepts": ["网络体系结构", "OSI模型", "TCP/IP模型", "协议层次", "数据封装"]
            },
            {
                "week": 2,
                "topic": "物理层：传输介质与编码技术",
                "content_summary": "学习物理层的基本功能和传输介质特性（双绞线、光纤、无线介质）。掌握数据通信的基本概念（带宽、波特率、比特率）。学习常用的编码技术（如曼彻斯特编码、差分曼彻斯特编码）和调制技术。了解多路复用技术（FDM、TDM、WDM）的原理和应用。",
                "key_concepts": ["传输介质", "信道编码", "数字调制", "多路复用", "带宽利用"]
            },
            {
                "week": 3,
                "topic": "数据链路层：差错控制与流量控制",
                "content_summary": "学习数据链路层的功能和服务，包括组帧、差错检测与纠正。重点掌握CRC校验原理和计算方法。学习流量控制机制（停等协议、滑动窗口协议）和ARQ协议（停等ARQ、回退N帧、选择重传）。理解介质访问控制（MAC）的基本概念。",
                "key_concepts": ["组帧", "CRC校验", "流量控制", "ARQ协议", "差错控制"]
            },
            {
                "week": 4,
                "topic": "局域网技术与以太网",
                "content_summary": "学习局域网的特点和分类，重点掌握以太网技术。学习CSMA/CD协议的工作原理和冲突检测机制。理解MAC地址的作用和格式，学习以太网帧结构。了解交换式以太网和虚拟局域网（VLAN）的概念，掌握交换机的工作原理。",
                "key_concepts": ["以太网", "CSMA/CD", "MAC地址", "交换机", "VLAN"]
            },
            {
                "week": 5,
                "topic": "网络层：IP协议与地址",
                "content_summary": "深入学习IPv4协议的数据报格式和分片机制。重点掌握IP地址的分类、子网划分和子网掩码的计算。学习CIDR（无类域间路由）和地址聚合。了解IPv6的主要特点和地址表示方法。掌握ARP和ICMP协议的工作原理及应用。",
                "key_concepts": ["IPv4协议", "IP地址", "子网划分", "CIDR", "ARP", "ICMP"]
            },
            {
                "week": 6,
                "topic": "路由算法与路由协议",
                "content_summary": "学习路由的基本概念和路由算法分类（静态路由、动态路由）。掌握距离向量路由算法（如RIP）和链路状态路由算法（如OSPF）的原理和区别。学习BGP协议的基本概念和自治系统的划分。通过实验配置简单的路由器路由表。",
                "key_concepts": ["路由算法", "RIP协议", "OSPF协议", "BGP", "路由表"]
            },
            {
                "week": 7,
                "topic": "传输层：TCP与UDP协议",
                "content_summary": "学习传输层的功能和端口号的概念。深入掌握TCP协议的特点：面向连接、可靠传输、流量控制和拥塞控制。理解TCP的三次握手建立连接和四次挥手释放连接过程。对比UDP协议的特点和应用场景。学习TCP的滑动窗口和拥塞控制算法。",
                "key_concepts": ["TCP协议", "UDP协议", "三次握手", "流量控制", "拥塞控制"]
            },
            {
                "week": 8,
                "topic": "应用层协议：HTTP、DNS与FTP",
                "content_summary": "学习应用层的功能和常见协议。重点掌握HTTP协议的请求/响应报文格式、方法（GET、POST等）和状态码。学习DNS域名解析系统的层次结构和查询过程。了解FTP协议的工作原理和主动/被动模式。介绍其他应用层协议（如SMTP、POP3、Telnet）。",
                "key_concepts": ["HTTP协议", "DNS解析", "FTP协议", "应用层服务", "URL与域名"]
            }
        ]
    }
    templates.append(template5)

    # Template 6: 机器学习基础 (Machine Learning Basics)
    template6 = {
        "id": str(uuid4()),
        "course_name": "机器学习基础",
        "subject": "人工智能",
        "grade": "大三",
        "start_week": 1,
        "end_week": 10,
        "total_weeks": 10,
        "chapters": [
            {
                "week": 1,
                "topic": "机器学习概述与基本概念",
                "content_summary": "介绍机器学习的定义、发展历史和应用场景。讲解机器学习的分类：监督学习、无监督学习、强化学习。理解训练集、验证集、测试集的划分和作用。学习机器学习的基本术语（特征、标签、模型、损失函数等）。了解过拟合和欠拟合的概念。",
                "key_concepts": ["机器学习定义", "监督学习", "特征工程", "过拟合", "模型评估"]
            },
            {
                "week": 2,
                "topic": "线性回归与最小二乘法",
                "content_summary": "学习线性回归模型的原理和假设。掌握最小二乘法求解线性回归参数。理解损失函数（均方误差）和梯度下降算法。学习多元线性回归和特征标准化。通过Python实现简单的线性回归模型，并进行预测和可视化。",
                "key_concepts": ["线性回归", "最小二乘法", "梯度下降", "损失函数", "特征标准化"]
            },
            {
                "week": 3,
                "topic": "逻辑回归与分类问题",
                "content_summary": "学习逻辑回归模型及其在二分类问题中的应用。掌握Sigmoid函数和决策边界的概念。理解交叉熵损失函数和最大似然估计。学习多分类问题的处理方法（一对多、Softmax回归）。通过实验使用逻辑回归解决分类任务。",
                "key_concepts": ["逻辑回归", "Sigmoid函数", "交叉熵", "二分类", "决策边界"]
            },
            {
                "week": 4,
                "topic": "决策树与集成学习",
                "content_summary": "学习决策树的构建方法和分裂准则（信息增益、基尼系数）。理解决策树的剪枝策略防止过拟合。学习集成学习的基本思想：Bagging、Boosting和Stacking。重点掌握随机森林和AdaBoost算法的原理。通过scikit-learn实现决策树和随机森林。",
                "key_concepts": ["决策树", "信息增益", "随机森林", "Boosting", "集成学习"]
            },
            {
                "week": 5,
                "topic": "支持向量机SVM",
                "content_summary": "学习支持向量机的基本原理和几何意义。理解最大间隔分类器和支持向量的概念。掌握软间隔和正则化参数C的作用。学习核函数（线性核、多项式核、RBF核）解决非线性分类问题。通过实验使用SVM进行分类任务。",
                "key_concepts": ["支持向量机", "最大间隔", "核函数", "软间隔", "非线性分类"]
            },
            {
                "week": 6,
                "topic": "神经网络基础",
                "content_summary": "介绍神经网络的基本结构：输入层、隐藏层、输出层。学习感知机模型和激活函数（Sigmoid、ReLU、Tanh）。掌握前向传播和反向传播算法的原理。理解权重初始化和学习率的选择。使用TensorFlow或PyTorch实现简单的多层感知机。",
                "key_concepts": ["神经网络", "感知机", "激活函数", "反向传播", "梯度下降"]
            },
            {
                "week": 7,
                "topic": "卷积神经网络CNN",
                "content_summary": "学习卷积神经网络的基本结构和工作原理。掌握卷积层、池化层和全连接层的作用。理解卷积核、步长、填充等参数。学习经典的CNN架构（如LeNet、AlexNet、VGG）。通过实验使用CNN进行图像分类任务（如MNIST、CIFAR-10）。",
                "key_concepts": ["卷积神经网络", "卷积层", "池化层", "特征提取", "图像分类"]
            },
            {
                "week": 8,
                "topic": "聚类算法",
                "content_summary": "学习无监督学习中的聚类问题。掌握K-Means算法的原理、步骤和收敛性。学习层次聚类和DBSCAN算法。理解聚类评价指标（轮廓系数、DB指数）。通过实验对不同类型的数据集进行聚类分析，并可视化聚类结果。",
                "key_concepts": ["K-Means", "层次聚类", "DBSCAN", "聚类评价", "无监督学习"]
            },
            {
                "week": 9,
                "topic": "降维技术：PCA与LDA",
                "content_summary": "学习降维的意义和应用场景。掌握主成分分析（PCA）的原理和计算步骤。理解特征值分解和主成分的选择。学习线性判别分析（LDA）在监督降维中的应用。通过实验使用PCA对高维数据进行降维和可视化。",
                "key_concepts": ["降维", "PCA", "特征值分解", "LDA", "数据可视化"]
            },
            {
                "week": 10,
                "topic": "模型评估与优化",
                "content_summary": "系统学习模型评估指标：准确率、精确率、召回率、F1分数、ROC曲线和AUC。掌握交叉验证方法（k折交叉验证、留一法）。学习超参数调优技术（网格搜索、随机搜索）。理解正则化（L1、L2）防止过拟合。综合实验：完成一个完整的机器学习项目。",
                "key_concepts": ["模型评估", "交叉验证", "超参数调优", "正则化", "ROC曲线"]
            }
        ]
    }
    templates.append(template6)

    # Template 7: 软件工程 (Software Engineering)
    template7 = {
        "id": str(uuid4()),
        "course_name": "软件工程",
        "subject": "计算机",
        "grade": "大二",
        "start_week": 1,
        "end_week": 6,
        "total_weeks": 6,
        "chapters": [
            {
                "week": 1,
                "topic": "软件工程概述与软件过程",
                "content_summary": "介绍软件工程的基本概念、目标和原则。讲解软件危机的产生背景和软件工程的解决思路。学习软件过程模型：瀑布模型、增量模型、螺旋模型和敏捷开发。理解软件生命周期各阶段的主要活动。讨论传统方法与敏捷方法的区别和适用场景。",
                "key_concepts": ["软件工程定义", "软件过程模型", "瀑布模型", "敏捷开发", "软件生命周期"]
            },
            {
                "week": 2,
                "topic": "需求工程与需求分析",
                "content_summary": "学习需求工程的基本概念和活动（需求获取、需求分析、需求规约、需求验证）。掌握需求获取的常用方法（访谈、问卷、原型等）。学习用例图、活动图等UML建模工具。理解功能需求和非功能需求的区别。通过案例练习编写需求规格说明书（SRS）。",
                "key_concepts": ["需求工程", "需求获取", "用例图", "需求分析", "SRS文档"]
            },
            {
                "week": 3,
                "topic": "系统设计：架构设计与详细设计",
                "content_summary": "学习软件设计的原则（高内聚、低耦合、模块化）。掌握软件架构设计的概念和常见架构模式（分层架构、MVC、微服务）。学习类图、序列图、组件图等UML图。理解接口设计和数据库设计的方法。通过项目案例进行架构设计和详细设计练习。",
                "key_concepts": ["软件架构", "设计原则", "类图", "MVC模式", "模块化设计"]
            },
            {
                "week": 4,
                "topic": "软件测试技术",
                "content_summary": "学习软件测试的目的、原则和分类（单元测试、集成测试、系统测试、验收测试）。掌握黑盒测试方法（等价类划分、边界值分析）和白盒测试方法（语句覆盖、分支覆盖）。学习测试用例的设计和测试计划的编写。了解自动化测试工具和持续集成。",
                "key_concepts": ["软件测试", "黑盒测试", "白盒测试", "测试用例", "自动化测试"]
            },
            {
                "week": 5,
                "topic": "版本控制与配置管理",
                "content_summary": "学习版本控制的基本概念和重要性。重点掌握Git的基本操作（克隆、提交、推送、拉取、分支、合并）。理解集中式和分布式版本控制系统的区别。学习配置管理的概念和软件配置项。通过实验练习Git的分支管理和冲突解决，了解GitHub/GitLab的协作流程。",
                "key_concepts": ["版本控制", "Git操作", "分支管理", "配置管理", "协作开发"]
            },
            {
                "week": 6,
                "topic": "软件项目管理与敏捷实践",
                "content_summary": "学习软件项目管理的基本概念：范围、时间、成本、质量管理。掌握项目进度估算方法和甘特图的使用。深入学习敏捷开发方法（Scrum、看板）和敏捷实践（迭代开发、每日站会、回顾会议）。了解软件度量和质量保证。通过小组项目体验完整的软件开发流程。",
                "key_concepts": ["项目管理", "Scrum方法", "迭代开发", "进度估算", "团队协作"]
            }
        ]
    }
    templates.append(template7)

    # Insert all templates
    for tmpl in templates:
        await db.execute(
            """
            INSERT INTO course_chapter_templates (
                id, course_name, subject, grade, start_week, end_week,
                total_weeks, chapters, use_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tmpl["id"],
                tmpl["course_name"],
                tmpl["subject"],
                tmpl["grade"],
                tmpl["start_week"],
                tmpl["end_week"],
                tmpl["total_weeks"],
                json.dumps(tmpl["chapters"], ensure_ascii=False),
                0,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
            commit=True,
        )
        print(f"✓ Inserted: {tmpl['course_name']} ({tmpl['total_weeks']}周)")

    print(f"\n✅ Successfully added {len(templates)} more templates!")


async def verify_all_templates():
    """Verify all templates in database."""
    db = await get_db()

    rows = await db.fetch_all(
        "SELECT course_name, subject, grade, start_week, end_week, total_weeks, use_count FROM course_chapter_templates ORDER BY created_at"
    )

    print("\n📋 All Templates in Database:")
    print("=" * 100)
    for i, row in enumerate(rows, 1):
        print(
            f"{i:2d}. {row['course_name']:<25} | {row['subject']:<12} | {row['grade']:<8} | "
            f"第{row['start_week']}-{row['end_week']}周 (共{row['total_weeks']}周) | 使用{row['use_count']}次"
        )
    print("=" * 100)
    print(f"总计: {len(rows)} 个模板\n")


async def main():
    """Main function."""
    print("🚀 Adding more mock templates...\n")

    try:
        await add_more_templates()
        await verify_all_templates()
        print("✨ Done!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
