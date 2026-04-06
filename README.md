# Compan

에빙하우스 망각곡선 기반 복기 알림 앱.  
링크를 등록하면 **1일 → 3일 → 7일 → 14일 → 30일** 주기로 Windows 토스트 알림을 보냅니다.

## 구조

```
Compan/
├── src/
│   ├── main.py        # 진입점 (시스템 트레이)
│   ├── database.py    # SQLite DB & 복기 일정
│   ├── scheduler.py   # 백그라운드 알림 스케줄러
│   ├── notifier.py    # Windows 토스트 알림
│   └── ui.py          # 링크 추가/목록 Tkinter UI
├── assets/
│   └── icon.png       # 트레이 아이콘 (없으면 자동 생성)
├── requirements.txt
└── build.bat          # .exe 빌드 스크립트
```

## 개발 환경 설정

```bash
pip install -r requirements.txt
python src/main.py
```

## .exe 빌드 (Windows)

```bat
build.bat
```

빌드 후 `dist/Compan.exe` 실행.  
시작 프로그램에 등록하려면 `shell:startup` 폴더에 바로가기 추가.

## 사용법

1. 시스템 트레이 아이콘 우클릭 → **링크 추가**
2. URL 입력 (제목은 자동 감지, 직접 입력도 가능)
3. 이후 1/3/7/14/30일에 알림 자동 발송
4. 알림 클릭 → 브라우저에서 링크 오픈

## 데이터 저장 위치

`%USERPROFILE%\.compan\compan.db` (SQLite)
