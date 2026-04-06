"""
notifier.py - Windows 토스트 알림 발송
클릭 시 해당 URL을 기본 브라우저로 오픈
"""
import webbrowser
import threading


def _open_url(url: str):
    webbrowser.open(url)


def send_review_notification(url: str, title: str, interval_days: int):
    """
    복기 알림 전송.
    winotify가 없으면 plyer로 fallback, 그것도 없으면 콘솔 출력.
    """
    body = f"{interval_days}일 후 복기할 시간입니다!\n{url}"
    app_title = "Compan - 복기 알림"

    try:
        from winotify import Notification, audio

        toast = Notification(
            app_id="Compan",
            title=f"📖 {title}",
            msg=body,
            duration="short",
            launch=url,
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return
    except ImportError:
        pass

    try:
        from plyer import notification

        notification.notify(
            title=f"[Compan] {title}",
            message=body,
            app_name="Compan",
            timeout=10,
        )
        # plyer는 클릭 콜백 미지원 → 별도 스레드로 브라우저 오픈
        threading.Timer(2.0, _open_url, args=[url]).start()
        return
    except ImportError:
        pass

    # 최후 fallback: 콘솔 출력 + 브라우저 오픈
    print(f"[복기 알림] {title}\n  {body}")
    _open_url(url)
