"""
GitHub Actions에서 실행할 크롤링 작업 스크립트
"""
import os
import sys
import logging
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import SessionLocal
import models

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def perform_check(task_id: int):
    """
    특정 작업을 체크하고 키워드를 찾습니다.
    """
    db = SessionLocal()
    try:
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if not task or not task.is_active:
            logger.info(f"Task {task_id} is not active or not found")
            return False

        logger.info(f"Checking Task {task_id}: {task.url} for '{task.keyword}'")
        
        try:
            # User-Agent 설정
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(task.url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text()
            
            keyword_found = False
            if task.keyword in text_content:
                # Find context (simple snippet)
                idx = text_content.find(task.keyword)
                start = max(0, idx - 50)
                end = min(len(text_content), idx + 50)
                context_snippet = text_content[start:end].replace("\n", " ").strip()
                
                alert = models.Alert(
                    task_id=task.id,
                    context=f"...{context_snippet}..."
                )
                db.add(alert)
                keyword_found = True
                logger.info(f"✅ FOUND keyword '{task.keyword}' in Task {task_id}")
            else:
                logger.info(f"❌ Keyword '{task.keyword}' not found in Task {task_id}")
            
            task.last_checked = datetime.utcnow()
            db.commit()
            return keyword_found
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error checking task {task_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking task {task_id}: {e}")
            return False
            
    finally:
        db.close()


def check_all_tasks():
    """
    모든 활성 작업을 체크합니다.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        tasks = db.query(models.Task).filter(models.Task.is_active == True).all()
        
        logger.info(f"Found {len(tasks)} active tasks")
        
        checked_count = 0
        found_count = 0
        
        for task in tasks:
            # 마지막 체크 시간 확인
            should_check = False
            if not task.last_checked:
                should_check = True
            else:
                next_check = task.last_checked + timedelta(minutes=task.interval_minutes)
                if now >= next_check:
                    should_check = True
            
            if should_check:
                if perform_check(task.id):
                    found_count += 1
                checked_count += 1
            else:
                logger.info(f"Task {task.id} skipped (not yet time to check)")
        
        logger.info(f"✅ Checked {checked_count} tasks, found keywords in {found_count} tasks")
        return {
            "checked": checked_count,
            "found": found_count,
            "total": len(tasks)
        }
    finally:
        db.close()


if __name__ == "__main__":
    # 데이터베이스 초기화
    from database import engine
    models.Base.metadata.create_all(bind=engine)
    
    logger.info("Starting cron job...")
    result = check_all_tasks()
    logger.info(f"Cron job completed: {result}")
    sys.exit(0)
