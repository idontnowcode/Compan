"""
database.py - SQLite 기반 링크 및 복기 일정 관리
에빙하우스 망각곡선 복기 주기: 1일, 3일, 7일, 14일, 30일
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".rested" / "rested.db"

REVIEW_INTERVALS = [1, 3, 7, 14, 30]   # 에빙하우스 복기 주기 (일)
SNOOZE_HOURS     = 3                    # 미확인 시 재알림 주기 (시간)
BASE_HOUR        = 9                    # 알림 기준 시각 (AM 9)
SLOT_HOURS       = [9, 12, 15, 18, 21]  # 3시간 단위 슬롯


def _next_slot(after: datetime) -> datetime:
    """after 이후 첫 번째 알림 슬롯 반환 (09, 12, 15, 18, 21시 중 가장 가까운 미래)."""
    for h in SLOT_HOURS:
        candidate = after.replace(hour=h, minute=0, second=0, microsecond=0)
        if candidate > after:
            return candidate
    # 당일 슬롯 소진 → 다음날 09:00
    return (after + timedelta(days=1)).replace(
        hour=BASE_HOUR, minute=0, second=0, microsecond=0
    )


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT,
            added_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            interval_days INTEGER NOT NULL,
            scheduled_at TEXT NOT NULL,
            notified INTEGER DEFAULT 0,
            confirmed INTEGER DEFAULT 0,
            last_notified_at TEXT,
            FOREIGN KEY (link_id) REFERENCES links(id)
        )
    """)
    # 기존 DB 마이그레이션 (컬럼 없으면 추가)
    for col, definition in [
        ("confirmed",       "INTEGER DEFAULT 0"),
        ("last_notified_at","TEXT"),
        ("next_notify_at",  "TEXT"),
    ]:
        try:
            c.execute(f"ALTER TABLE reviews ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass  # 이미 존재
    conn.commit()
    conn.close()


def add_link(url: str, title: str = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    display_title = title if title else url

    c.execute(
        "INSERT INTO links (url, title, added_at) VALUES (?, ?, ?)",
        (url, display_title, now.isoformat()),
    )
    link_id = c.lastrowid

    for days in REVIEW_INTERVALS:
        # 복기 알림은 해당 날짜 AM 9:00으로 고정
        scheduled = (now + timedelta(days=days)).replace(
            hour=BASE_HOUR, minute=0, second=0, microsecond=0
        )
        c.execute(
            "INSERT INTO reviews (link_id, interval_days, scheduled_at) VALUES (?, ?, ?)",
            (link_id, days, scheduled.isoformat()),
        )

    conn.commit()
    conn.close()
    return link_id


def get_due_reviews() -> list:
    """처음 알림을 보낼 항목 (notified=0, scheduled_at 도래)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
        SELECT r.id, l.url, l.title, r.interval_days
        FROM reviews r
        JOIN links l ON r.link_id = l.id
        WHERE r.scheduled_at <= ? AND r.notified = 0
        ORDER BY r.scheduled_at ASC
    """, (now,))
    results = c.fetchall()
    conn.close()
    return results


def get_reviews_to_renotify() -> list:
    """
    알림은 보냈지만 아직 확인 안 된 항목 중
    next_notify_at 슬롯이 도래한 것
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
        SELECT r.id, l.url, l.title, r.interval_days
        FROM reviews r
        JOIN links l ON r.link_id = l.id
        WHERE r.notified = 1
          AND r.confirmed = 0
          AND r.next_notify_at IS NOT NULL
          AND r.next_notify_at <= ?
        ORDER BY r.next_notify_at ASC
    """, (now,))
    results = c.fetchall()
    conn.close()
    return results


def get_unconfirmed_reviews() -> list:
    """알림은 보냈지만 아직 확인 안 된 전체 목록"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT r.id, l.url, l.title, r.interval_days, r.last_notified_at
        FROM reviews r
        JOIN links l ON r.link_id = l.id
        WHERE r.notified = 1 AND r.confirmed = 0
        ORDER BY r.last_notified_at ASC
    """)
    results = c.fetchall()
    conn.close()
    return results


def count_unconfirmed() -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM reviews WHERE notified=1 AND confirmed=0")
    n = c.fetchone()[0]
    conn.close()
    return n


def mark_notified(review_id: int):
    """처음 알림 발송 시 호출 — 다음 슬롯(next_notify_at) 설정"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    c.execute(
        "UPDATE reviews SET notified=1, last_notified_at=?, next_notify_at=? WHERE id=?",
        (now.isoformat(), _next_slot(now).isoformat(), review_id),
    )
    conn.commit()
    conn.close()


def mark_renotified(review_id: int):
    """재알림 발송 시 next_notify_at을 다음 슬롯으로 갱신"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    c.execute(
        "UPDATE reviews SET last_notified_at=?, next_notify_at=? WHERE id=?",
        (now.isoformat(), _next_slot(now).isoformat(), review_id),
    )
    conn.commit()
    conn.close()


def confirm_review(review_id: int):
    """사용자가 '확인했어요' 누를 때"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE reviews SET confirmed=1 WHERE id=?", (review_id,))
    conn.commit()
    conn.close()


def get_all_links() -> list:
    """등록된 모든 링크 반환 (최신순).
    반환 컬럼: id, url, title, added_at, pending_reviews, total_reviews, next_review_at
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT l.id, l.url, l.title, l.added_at,
               COUNT(CASE WHEN r.confirmed = 0 THEN 1 END) as pending_reviews,
               COUNT(r.id) as total_reviews,
               MIN(CASE WHEN r.confirmed = 0 THEN r.scheduled_at END) as next_review_at
        FROM links l
        LEFT JOIN reviews r ON l.id = r.link_id
        GROUP BY l.id
        ORDER BY l.added_at DESC
    """)
    results = c.fetchall()
    conn.close()
    return results


def delete_link(link_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM reviews WHERE link_id = ?", (link_id,))
    c.execute("DELETE FROM links WHERE id = ?", (link_id,))
    conn.commit()
    conn.close()
