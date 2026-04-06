"""
scheduler.py - 백그라운드 복기 알림 스케줄러
1분마다 DB를 확인하여 기한이 된 복기 항목에 알림 전송
"""
import threading
import time

from database import get_due_reviews, mark_notified
from notifier import send_review_notification

CHECK_INTERVAL_SECONDS = 60  # 1분마다 체크


class ReviewScheduler:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.is_set():
            self._check_reviews()
            self._stop_event.wait(CHECK_INTERVAL_SECONDS)

    def _check_reviews(self):
        try:
            due = get_due_reviews()
            for review_id, url, title, interval_days in due:
                send_review_notification(url, title, interval_days)
                mark_notified(review_id)
        except Exception as e:
            print(f"[Scheduler] 오류: {e}")
