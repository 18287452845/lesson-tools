"""Test script for the lesson plan generation API"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from backend.utils.ai_config import get_ai_generator
from backend.models.schemas import LessonPlanGenerateRequest

async def test_ai_generation():
    """Test the AI generation directly"""
    print("Testing AI generation...")

    request = LessonPlanGenerateRequest(
        template_id="7298647c-4e63-42da-84b6-19106f2ce169",
        subject="数学",
        grade="一年级",
        topic="加法入门",
        duration="1课时",
    )

    print(f"Request: {request.model_dump()}")

    try:
        generator = await get_ai_generator()
        print(f"Generator created: {generator}")
        content = await generator.generate_lesson_plan(request)
        print(f"Generated content: {json.dumps(content.model_dump(), indent=2, ensure_ascii=False)}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ai_generation())
    print(f"Test {'passed' if result else 'failed'}")
