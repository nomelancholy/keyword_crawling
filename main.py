import os
import logging
import requests
import trafilatura
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Form, Depends, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import (
    urljoin,
    urlparse,
    urlsplit,
    urlunsplit,
    parse_qsl,
    urlencode,
)
from zoneinfo import ZoneInfo
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

KST = ZoneInfo("Asia/Seoul")
MAX_DETAIL_LINKS = int(os.getenv("MAX_DETAIL_LINKS", "30"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))
PAGE_PARAM = os.getenv("PAGE_PARAM", "page")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def format_kst(dt: Optional[datetime]) -> str:
    if not dt:
        return "아직 안함"
    # DB에 저장된 값이 naive(UTC)일 수 있으므로 보정
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")


def extract_alert_link(context: Optional[str]) -> Optional[str]:
    if not context:
        return None
    if context.startswith("[") and "]" in context:
        return context.split("]", 1)[0][1:]
    return None


def strip_alert_link(context: Optional[str]) -> str:
    if not context:
        return ""
    if context.startswith("[") and "]" in context:
        return context.split("]", 1)[1].lstrip()
    return context


def fetch_page_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text


def extract_links(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith("#"):
            continue
        if href.startswith(("javascript:", "mailto:")):
            continue
        absolute = urljoin(base_url, href)
        if not absolute.startswith(("http://", "https://")):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links


def is_same_domain(base_url: str, target_url: str) -> bool:
    try:
        return urlparse(base_url).netloc == urlparse(target_url).netloc
    except Exception:
        return False


def build_paged_url(url: str, page: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query[PAGE_PARAM] = str(page)
    new_query = urlencode(query)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
    )


def fetch_page_text(url: str) -> Optional[str]:
    """
    Try article extraction first; fallback to plain text from HTML.
    """
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        extracted = trafilatura.extract(downloaded)
        if extracted:
            return extracted

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text_content = soup.get_text()
    return text_content if text_content else None


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
            candidate_links: list[str] = []
            seen_links: set[str] = set()
            for page in range(1, MAX_PAGES + 1):
                page_url = task.url if page == 1 else build_paged_url(task.url, page)
                list_html = fetch_page_html(page_url)
                links = extract_links(page_url, list_html)
                same_domain_links = [
                    link for link in links if is_same_domain(task.url, link)
                ]
                existing_links_page = {
                    row[0]
                    for row in db.query(models.TaskLink.url)
                    .filter(models.TaskLink.task_id == task.id)
                    .filter(models.TaskLink.url.in_(same_domain_links))
                    .all()
                }
                new_links_page = [
                    link
                    for link in same_domain_links
                    if link not in existing_links_page
                ]
                if not new_links_page:
                    # No new links on this page -> older pages are likely already processed.
                    break

                for link in new_links_page:
                    if link in seen_links:
                        continue
                    seen_links.add(link)
                    candidate_links.append(link)
                    if len(candidate_links) >= MAX_DETAIL_LINKS:
                        break
                if len(candidate_links) >= MAX_DETAIL_LINKS:
                    break

            if not candidate_links:
                # Fallback: treat the page itself as an article
                text_content = fetch_page_text(task.url)
                if not text_content:
                    logger.warning(f"No text extracted for Task {task_id}: {task.url}")
                    return
                if task.keyword in text_content:
                    idx = text_content.find(task.keyword)
                    start = max(0, idx - 50)
                    end = min(len(text_content), idx + 50)
                    context_snippet = text_content[start:end].replace("\n", " ").strip()
                    alert = models.Alert(
                        task_id=task.id, context=f"...{context_snippet}..."
                    )
                    db.add(alert)
                    logger.info(f"FOUND keyword in Task {task_id}")
            else:
                existing_links = {
                    row[0]
                    for row in db.query(models.TaskLink.url)
                    .filter(models.TaskLink.task_id == task.id)
                    .filter(models.TaskLink.url.in_(candidate_links))
                    .all()
                }
                new_links = [
                    link for link in candidate_links if link not in existing_links
                ]

                for link in new_links:
                    text_content = fetch_page_text(link)
                    if not text_content:
                        logger.warning(f"No text extracted for Task {task_id}: {link}")
                        db.add(models.TaskLink(task_id=task.id, url=link))
                        continue

                    if task.keyword in text_content:
                        idx = text_content.find(task.keyword)
                        start = max(0, idx - 50)
                        end = min(len(text_content), idx + 50)
                        context_snippet = (
                            text_content[start:end].replace("\n", " ").strip()
                        )
                        alert = models.Alert(
                            task_id=task.id,
                            context=f"[{link}] ...{context_snippet}...",
                        )
                        db.add(alert)
                        logger.info(f"FOUND keyword in Task {task_id} (detail page)")

                    db.add(models.TaskLink(task_id=task.id, url=link))

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
                next_check = task.last_checked + timedelta(
                    minutes=task.interval_minutes
                )
                if now >= next_check:
                    should_check = True

            if should_check:
                # perform_check는 키워드를 찾았는지 반환하지 않으므로
                # 여기서는 단순히 체크만 수행
                perform_check(task.id)
                checked_count += 1

        return JSONResponse(
            {
                "status": "success",
                "checked_tasks": checked_count,
                "total_tasks": len(tasks),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    tasks = db.query(models.Task).order_by(models.Task.created_at.desc()).all()
    # Fetch alerts for display (last 7 days)
    cutoff = datetime.utcnow() - timedelta(days=7)
    alerts = (
        db.query(models.Alert)
        .filter(models.Alert.found_at >= cutoff)
        .order_by(models.Alert.found_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tasks": tasks,
            "alerts": alerts,
            "format_kst": format_kst,
            "extract_alert_link": extract_alert_link,
            "strip_alert_link": strip_alert_link,
        },
    )


@app.post("/tasks/add")
def add_task(
    url: str = Form(...),
    keyword: str = Form(...),
    interval_minutes: int = Form(...),
    db: Session = Depends(get_db),
):
    # Ensure URL has schema
    if not url.startswith("http"):
        url = "https://" + url

    new_task = models.Task(url=url, keyword=keyword, interval_minutes=interval_minutes)
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
