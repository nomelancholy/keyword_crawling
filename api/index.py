"""
Vercel serverless function entry point
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app

# Vercel은 ASGI 앱을 직접 사용합니다
# FastAPI는 ASGI 앱이므로 그대로 export
