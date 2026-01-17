"""
Metadata synchronization service for initializing preset subjects and grades.
"""
from uuid import uuid4
from datetime import datetime
from ..models.database import Database


# Preset subjects with categorization
PRESET_SUBJECTS = [
    # University courses (14 subjects)
    {"name": "大数据技术", "category": "university_course", "sort_order": 1},
    {"name": "信息安全技术", "category": "university_course", "sort_order": 2},
    {"name": "云计算技术", "category": "university_course", "sort_order": 3},
    {"name": "人工智能", "category": "university_course", "sort_order": 4},
    {"name": "Java程序设计", "category": "university_course", "sort_order": 5},
    {"name": "Python程序设计", "category": "university_course", "sort_order": 6},
    {"name": "数据结构", "category": "university_course", "sort_order": 7},
    {"name": "计算机网络", "category": "university_course", "sort_order": 8},
    {"name": "操作系统", "category": "university_course", "sort_order": 9},
    {"name": "数据库原理", "category": "university_course", "sort_order": 10},
    {"name": "软件工程", "category": "university_course", "sort_order": 11},
    {"name": "Web开发", "category": "university_course", "sort_order": 12},
    {"name": "移动应用开发", "category": "university_course", "sort_order": 13},
    {"name": "Linux系统管理", "category": "university_course", "sort_order": 14},
    # Basic subjects (13 subjects)
    {"name": "语文", "category": "basic_subject", "sort_order": 15},
    {"name": "数学", "category": "basic_subject", "sort_order": 16},
    {"name": "英语", "category": "basic_subject", "sort_order": 17},
    {"name": "物理", "category": "basic_subject", "sort_order": 18},
    {"name": "化学", "category": "basic_subject", "sort_order": 19},
    {"name": "生物", "category": "basic_subject", "sort_order": 20},
    {"name": "历史", "category": "basic_subject", "sort_order": 21},
    {"name": "地理", "category": "basic_subject", "sort_order": 22},
    {"name": "政治", "category": "basic_subject", "sort_order": 23},
    {"name": "科学", "category": "basic_subject", "sort_order": 24},
    {"name": "音乐", "category": "basic_subject", "sort_order": 25},
    {"name": "美术", "category": "basic_subject", "sort_order": 26},
    {"name": "体育", "category": "basic_subject", "sort_order": 27},
]

# Preset grades with categorization
PRESET_GRADES = [
    # University grades (7 grades)
    {"name": "大一", "category": "university", "sort_order": 1},
    {"name": "大二", "category": "university", "sort_order": 2},
    {"name": "大三", "category": "university", "sort_order": 3},
    {"name": "大四", "category": "university", "sort_order": 4},
    {"name": "2023级", "category": "university", "sort_order": 5},
    {"name": "2024级", "category": "university", "sort_order": 6},
    {"name": "2025级", "category": "university", "sort_order": 7},
    # High school grades (3 grades)
    {"name": "高一", "category": "high_school", "sort_order": 8},
    {"name": "高二", "category": "high_school", "sort_order": 9},
    {"name": "高三", "category": "high_school", "sort_order": 10},
    # Middle school grades (3 grades)
    {"name": "七年级", "category": "middle_school", "sort_order": 11},
    {"name": "八年级", "category": "middle_school", "sort_order": 12},
    {"name": "九年级", "category": "middle_school", "sort_order": 13},
    # Elementary grades (6 grades)
    {"name": "一年级", "category": "elementary", "sort_order": 14},
    {"name": "二年级", "category": "elementary", "sort_order": 15},
    {"name": "三年级", "category": "elementary", "sort_order": 16},
    {"name": "四年级", "category": "elementary", "sort_order": 17},
    {"name": "五年级", "category": "elementary", "sort_order": 18},
    {"name": "六年级", "category": "elementary", "sort_order": 19},
]


async def init_preset_subjects(db: Database) -> None:
    """
    Initialize preset subjects in the database.
    Only inserts if the subjects table is empty.
    """
    # Check if subjects table already has data
    count_row = await db.fetch_one("SELECT COUNT(*) as count FROM subjects")
    if count_row and count_row["count"] > 0:
        print(f"Subjects table already has {count_row['count']} records. Skipping initialization.")
        return

    print("Initializing preset subjects...")
    timestamp = datetime.now().isoformat()

    for subject in PRESET_SUBJECTS:
        subject_id = str(uuid4())
        await db.execute(
            """
            INSERT INTO subjects (id, name, category, is_preset, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
            (
                subject_id,
                subject["name"],
                subject["category"],
                subject["sort_order"],
                timestamp,
                timestamp,
            ),
            commit=True,
        )

    print(f"Successfully initialized {len(PRESET_SUBJECTS)} preset subjects.")


async def init_preset_grades(db: Database) -> None:
    """
    Initialize preset grades in the database.
    Only inserts if the grades table is empty.
    """
    # Check if grades table already has data
    count_row = await db.fetch_one("SELECT COUNT(*) as count FROM grades")
    if count_row and count_row["count"] > 0:
        print(f"Grades table already has {count_row['count']} records. Skipping initialization.")
        return

    print("Initializing preset grades...")
    timestamp = datetime.now().isoformat()

    for grade in PRESET_GRADES:
        grade_id = str(uuid4())
        await db.execute(
            """
            INSERT INTO grades (id, name, category, is_preset, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
            (
                grade_id,
                grade["name"],
                grade["category"],
                grade["sort_order"],
                timestamp,
                timestamp,
            ),
            commit=True,
        )

    print(f"Successfully initialized {len(PRESET_GRADES)} preset grades.")


async def init_metadata(db: Database) -> None:
    """
    Initialize all metadata (subjects and grades).
    This function should be called during application startup.
    """
    await init_preset_subjects(db)
    await init_preset_grades(db)
