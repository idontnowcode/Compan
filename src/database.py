"""
database.py - SQLite 기반 링크 및 복기 일정 관리
에빙하우스 망각곡선 복기 주기: 1일, 3일, 7일, 14일, 30일
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".compan" / "compan.db"

REVIEW_INTERVALS = [1, 3, 7, 14, 30]   # 에빙하우스 복기 주기 (일)
SNOOZE_HOURS     = 3                    # 미확인 시 재알림 주기 (시간)


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
        scheduled = now + timedelta(days=days)
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
    마지막 알림으로부터 SNOOZE_HOURS 시간 이상 지난 것
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=SNOOZE_HOURS)).isoformat()
    c.execute("""
        SELECT r.id, l.url, l.title, r.interval_days
        FROM reviews r
        JOIN links l ON r.link_id = l.id
        WHERE r.notified = 1
          AND r.confirmed = 0
          AND r.last_notified_at <= ?
        ORDER BY r.last_notified_at ASC
    """, (cutoff,))
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
    """처음 알림 발송 시 호출"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute(
        "UPDATE reviews SET notified=1, last_notified_at=? WHERE id=?",
        (now, review_id),
    )
    conn.commit()
    conn.close()


def mark_renotified(review_id: int):
    """재알림 발송 시 last_notified_at 갱신"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE reviews SET last_notified_at=? WHERE id=?",
        (datetime.now().isoformat(), review_id),
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
    """등록된 모든 링크 반환 (최신순)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT l.id, l.url, l.title, l.added_at,
               COUNT(CASE WHEN r.notified = 0 THEN 1 END) as pending_reviews,
               COUNT(r.id) as total_reviews
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
