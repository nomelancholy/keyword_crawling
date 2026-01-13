import os
import logging
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Form, Depends, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from database import SessionLocal, engine

# Initialize DB
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 환경 확인
IS_VERCEL = os.getenv("VERCEL") == "1"
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def perform_check(task_id: int):
    """
    Background job to scrape the URL and check for the keyword.
    """
    db = SessionLocal()
    try:
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if not task or not task.is_active:
            return

        logger.info(f"Checking Task {task_id}: {task.url} for '{task.keyword}'")
        
        try:
            # Simple User-Agent to avoid immediate blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(task.url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text()
            
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
                logger.info(f"FOUND keyword in Task {task_id}")
            
            task.last_checked = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            logger.error(f"Error checking task {task_id}: {e}")
            
    finally:
        db.close()

@app.get("/api/cron/check-tasks")
def cron_check_tasks():
    """
    GitHub Actions 또는 외부에서 호출할 수 있는 엔드포인트
    모든 활성 작업을 체크합니다.
    """
    # 보안: API 키 확인 (선택사항)
    api_key = os.getenv("CRON_API_KEY")
    # 필요시 Authorization 헤더로 보안 강화
    
    db = SessionLocal()
    try:
        # 체크해야 할 작업들 찾기 (마지막 체크 시간 + interval_minutes가 지난 작업)
        now = datetime.utcnow()
        tasks = db.query(models.Task).filter(models.Task.is_active == True).all()
        
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
                # perform_check는 키워드를 찾았는지 반환하지 않으므로
                # 여기서는 단순히 체크만 수행
                perform_check(task.id)
                checked_count += 1
        
        return JSONResponse({
            "status": "success",
            "checked_tasks": checked_count,
            "total_tasks": len(tasks),
            "timestamp": datetime.utcnow().isoformat()
        })
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    tasks = db.query(models.Task).order_by(models.Task.created_at.desc()).all()
    # Fetch alerts for display (simplified: just last 10 alerts globally or per task)
    alerts = db.query(models.Alert).order_by(models.Alert.found_at.desc()).limit(20).all()
    return templates.TemplateResponse("index.html", {"request": request, "tasks": tasks, "alerts": alerts})

@app.post("/tasks/add")
def add_task(
    url: str = Form(...),
    keyword: str = Form(...),
    interval_minutes: int = Form(...),
    db: Session = Depends(get_db)
):
    # Ensure URL has schema
    if not url.startswith("http"):
        url = "https://" + url
        
    new_task = models.Task(
        url=url,
        keyword=keyword,
        interval_minutes=interval_minutes
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # 새 작업 추가 시 즉시 한 번 체크 (선택사항)
    # GitHub Actions가 주기적으로 체크하므로 즉시 체크는 선택사항
    # perform_check(new_task.id)
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/tasks/{task_id}/delete")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/tasks/{task_id}/check-now")
def check_task_now(task_id: int, db: Session = Depends(get_db)):
    """
    특정 작업을 즉시 체크하는 엔드포인트
    """
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    perform_check(task_id)
    return RedirectResponse(url="/", status_code=303)
