"""
scheduler.py - 백그라운드 복기 알림 스케줄러

매 CHECK_INTERVAL 초마다:
  1. 처음 알림 보낼 항목 (notified=0, scheduled_at 도래)
  2. 확인 안 된 항목 중 마지막 알림으로부터 3시간 경과한 것 (재알림)

두 경우 모두 on_review_due 콜백을 호출.
UI 조작은 반드시 메인 스레드에서 해야 하므로
콜백 호출 자체는 메인 스레드에서 수행(main.py 에서 root.after 래핑).
"""
import threading

import database
from notifier import send_review_notification

CHECK_INTERVAL_SECONDS = 60


class ReviewScheduler:
    def __init__(self, on_review_due=None):
        """
        on_review_due: callable(review_id, url, title, interval_days)
            복기 팝업 등 UI 액션을 트리거할 콜백.
            None 이면 토스트 알림만 발송.
        """
        self._on_due = on_review_due
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            self._tick()
            self._stop.wait(CHECK_INTERVAL_SECONDS)

    def _tick(self):
        try:
            # 1) 최초 알림
            for review_id, url, title, days in database.get_due_reviews():
                send_review_notification(url, title, days)
                database.mark_notified(review_id)
                if self._on_due:
                    self._on_due(review_id, url, title, days)

            # 2) 미확인 재알림 (3시간 경과)
            for review_id, url, title, days in database.get_reviews_to_renotify():
                send_review_notification(url, title, days)
                database.mark_renotified(review_id)
                if self._on_due:
                    self._on_due(review_id, url, title, days)

        except Exception as e:
            print(f"[Scheduler] 오류: {e}")
