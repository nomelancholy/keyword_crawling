"""
GitHub Actions에서 실행할 크롤링 작업 스크립트
"""

import os
import sys
import logging
import re
import requests
import trafilatura
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from urllib.parse import (
    urljoin,
    urlparse,
    urlsplit,
    urlunsplit,
    parse_qsl,
    urlencode,
)
from database import SessionLocal
import models

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MAX_DETAIL_LINKS = int(os.getenv("MAX_DETAIL_LINKS", "30"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))
PAGE_PARAM = os.getenv("PAGE_PARAM", "page")
ALLOW_PATH_REGEX = os.getenv("ALLOW_PATH_REGEX", "")
DENY_PATH_REGEX = os.getenv("DENY_PATH_REGEX", "")


def fetch_page_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        if response.status_code == 403:
            logger.warning(f"403 Forbidden for list page: {url}")
            return ""
        raise exc
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


def normalize_detail_url(url: str) -> str:
    parts = urlsplit(url)
    query_pairs = [(k, v) for k, v in parse_qsl(parts.query) if k != "comment_srl"]
    new_query = urlencode(query_pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, ""))


def should_follow_link(url: str) -> bool:
    path = urlsplit(url).path
    if DENY_PATH_REGEX and re.search(DENY_PATH_REGEX, path):
        return False
    if ALLOW_PATH_REGEX:
        return re.search(ALLOW_PATH_REGEX, path) is not None
    return True


def fetch_page_text(url: str):
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
    response = requests.get(url, headers=headers, timeout=30)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        if response.status_code == 403:
            logger.warning(f"403 Forbidden for detail page: {url}")
            return None
        raise exc
    soup = BeautifulSoup(response.text, "html.parser")
    text_content = soup.get_text()
    return text_content if text_content else None


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
            candidate_links: list[str] = []
            seen_links: set[str] = set()
            for page in range(1, MAX_PAGES + 1):
                page_url = task.url if page == 1 else build_paged_url(task.url, page)
                list_html = fetch_page_html(page_url)
                links = extract_links(page_url, list_html)
                same_domain_links = [
                    link for link in links if is_same_domain(task.url, link)
                ]
                normalized_links: list[str] = []
                for link in same_domain_links:
                    normalized = normalize_detail_url(link)
                    if not should_follow_link(normalized):
                        continue
                    normalized_links.append(normalized)
                existing_links_page = {
                    row[0]
                    for row in db.query(models.TaskLink.url)
                    .filter(models.TaskLink.task_id == task.id)
                    .filter(models.TaskLink.url.in_(normalized_links))
                    .all()
                }
                new_links_page = [
                    link for link in normalized_links if link not in existing_links_page
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

            keyword_found = False
            if not candidate_links:
                text_content = fetch_page_text(task.url)
                if not text_content:
                    logger.warning(f"No text extracted for Task {task_id}: {task.url}")
                    return False

                if task.keyword in text_content:
                    idx = text_content.find(task.keyword)
                    start = max(0, idx - 50)
                    end = min(len(text_content), idx + 50)
                    context_snippet = text_content[start:end].replace("\n", " ").strip()
                    alert = models.Alert(
                        task_id=task.id, context=f"...{context_snippet}..."
                    )
                    db.add(alert)
                    keyword_found = True
                    logger.info(f"✅ FOUND keyword '{task.keyword}' in Task {task_id}")
                else:
                    logger.info(
                        f"❌ Keyword '{task.keyword}' not found in Task {task_id}"
                    )
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
                        keyword_found = True
                        logger.info(
                            f"✅ FOUND keyword '{task.keyword}' in Task {task_id} (detail page)"
                        )

                    db.add(models.TaskLink(task_id=task.id, url=link))

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
                next_check = task.last_checked + timedelta(
                    minutes=task.interval_minutes
                )
                if now >= next_check:
                    should_check = True

            if should_check:
                if perform_check(task.id):
                    found_count += 1
                checked_count += 1
            else:
                logger.info(f"Task {task.id} skipped (not yet time to check)")

        logger.info(
            f"✅ Checked {checked_count} tasks, found keywords in {found_count} tasks"
        )
        return {"checked": checked_count, "found": found_count, "total": len(tasks)}
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
