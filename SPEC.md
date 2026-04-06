# COMPAN AI Management Dashboard — 기능 명세서

> 이 문서는 다른 세션에서 개발을 이어가기 위한 설계 명세서입니다.

---

## 1. 프로젝트 구조

```
Compan/
├── package.json          # 서버 루트 패키지 (Express + ws + cors)
├── server/
│   ├── index.js          # Express 서버 + WebSocket 서버
│   └── data.js           # 초기 목(mock) 데이터 (현재는 인메모리)
└── client/               # Vite + React 프론트엔드
    ├── package.json
    ├── vite.config.js    # 프록시 설정 포함
    └── src/
        ├── main.jsx
        ├── index.css     # 전역 리셋 스타일
        ├── App.jsx       # 라우팅, WebSocket 연결, 레이아웃
        ├── App.css       # 전체 디자인 시스템 (다크테마)
        ├── hooks/
        │   └── useWebSocket.js   # WS 연결 + 자동 재연결 훅
        └── components/
            ├── OrgChart.jsx      # 조직도 트리
            ├── AgentList.jsx     # 에이전트 디렉토리 (카드형)
            ├── ProjectBoard.jsx  # 칸반 보드 + 목록 뷰
            ├── Deliverables.jsx  # 산출물 관리
            └── ActivityFeed.jsx  # 실시간 활동 피드 (사이드바)
```

### 실행 방법

```bash
# 서버 실행 (포트 3001)
node server/index.js

# 클라이언트 실행 (포트 5173)
cd client && npm run dev
```

---

## 2. 데이터 모델

### 2-1. Member (멤버)

```js
{
  id: string,            // "human-ceo", "agent-dev-01" 등
  name: string,          // 표시 이름
  role: string,          // 직책
  type: "human" | "ai",
  avatar: string,        // 2글자 이니셜
  status: "online" | "active" | "idle" | "waiting" | "offline",
  department: string,
  reportsTo: string | null,  // 상위 멤버 id (조직도 트리 구성에 사용)
  email?: string,            // human만
  model?: string,            // ai만 (claude-opus-4-6 등)
  currentTask?: string | null,
  performance?: number,      // 0~100
  tasksCompleted?: number,
  joinedAt: string,          // ISO date
  capabilities?: string[],   // ai만
  fullName?: string,         // ai 에이전트 풀네임
}
```

### 2-2. Project (프로젝트)

```js
{
  id: string,
  name: string,
  description: string,
  status: "planned" | "in_progress" | "completed",
  priority: "critical" | "high" | "medium" | "low",
  owner: string,         // member id
  team: string[],        // member id 배열
  progress: number,      // 0~100 (%)
  startDate: string,     // YYYY-MM-DD
  dueDate: string,
  tags: string[],
  sprint: string | null,
}
```

### 2-3. Deliverable (산출물)

```js
{
  id: string,
  name: string,
  type: "document" | "code" | "design" | "report" | "data",
  projectId: string,
  author: string,        // member id
  status: "approved" | "in_review" | "draft" | "rejected",
  createdAt: string,     // ISO datetime
  size: string,          // "2.4 MB"
  format: string,        // "PDF", "ZIP", "Figma", "HTML" 등
  description: string,
}
```

### 2-4. ActivityLog (활동 로그)

```js
{
  id: number,
  agentId: string,       // member id
  action: string,        // 활동 설명
  time: string,          // "5분 전" 등 상대 시간
  type: "commit" | "review" | "test" | "upload" | "update" | "fix" | "data",
}
```

---

## 3. API 명세

### REST API (기본 URL: `http://localhost:3001/api`)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/state` | 전체 상태 반환 (members, projects, deliverables, activityLog) |
| PATCH | `/agents/:id/status` | 에이전트 상태 변경 (`{ status: "active" \| "idle" \| ... }`) |
| PATCH | `/projects/:id/status` | 프로젝트 상태 변경 (`{ status: "planned" \| "in_progress" \| "completed" }`) |

### WebSocket (`ws://localhost:3001`)

#### 서버 → 클라이언트 이벤트

| event | data | 설명 |
|-------|------|------|
| `init` | 전체 state 객체 | 최초 연결 시 전체 데이터 수신 |
| `agent:update` | Member 객체 | 에이전트 상태/태스크 변경 |
| `project:update` | Project 객체 | 프로젝트 진행률/상태 변경 |
| `activity:new` | ActivityLog 항목 | 새 활동 로그 추가 |

#### 현재 시뮬레이션 주기
- **에이전트 태스크 업데이트**: 8초마다 랜덤 에이전트 태스크 교체
- **프로젝트 진행률**: 20초마다 진행 중 프로젝트 1~3% 증가

---

## 4. 컴포넌트 상세

### App.jsx (루트)
- 사이드바 네비게이션 (5개 탭)
- 상단 바 (페이지 타이틀 + 요약 KPI 4개)
- 오른쪽 실시간 활동 피드 사이드바
- `useWebSocket` 훅으로 WS 연결 및 상태 관리
- REST API 호출 핸들러 (`handleAgentStatusChange`, `handleProjectStatusChange`)

### OrgChart.jsx
- `reportsTo` 필드로 재귀 트리 렌더링
- 멤버 클릭 시 상세 패널 표시
- 상태 표시 점 (색상 코딩)
- 부서별 인원 현황 배지

### AgentList.jsx
- 타입/상태/검색 필터
- 정렬: 상태순, 성과순, 완료 태스크순, 이름순
- 카드에서 ⋮ 메뉴로 상태 직접 변경
- 성과 바 + 역량 태그 표시

### ProjectBoard.jsx
- **보드 뷰**: 칸반 3열 (예정/진행중/완료)
- **목록 뷰**: 테이블 형식
- 카드 클릭으로 팀 구성, 날짜, 태그 확장
- 상태 변경 버튼 (시작하기 / 완료 처리)
- D-day 배지 (긴급/초과 시 색상 변경)

### Deliverables.jsx
- 상태 + 유형 복합 필터
- 산출물 목록 (생성일 최신순)
- 미리보기/다운로드/승인 버튼
- 작성자, 연관 프로젝트, 크기, 경과시간 표시

### ActivityFeed.jsx
- 오른쪽 사이드바 고정
- 최신 12개 표시
- WS `activity:new` 이벤트로 실시간 갱신

---

## 5. 향후 개발 계획 (로컬 저장소 연동)

현재는 서버 메모리에만 데이터가 저장됨. 다음 세션에서 구현 예정:

### 5-1. 로컬 파일 기반 영속성
```
server/
└── db/
    ├── members.json
    ├── projects.json
    ├── deliverables.json
    └── activity.json
```
- `server/data.js`를 JSON 파일 읽기/쓰기로 교체
- 변경 시 즉시 파일 동기화 (`fs.writeFileSync`)

### 5-2. 추가 REST API (우선순위 순)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/agents` | 새 AI 에이전트 등록 |
| DELETE | `/api/agents/:id` | 에이전트 제거 |
| POST | `/api/projects` | 프로젝트 생성 |
| PUT | `/api/projects/:id` | 프로젝트 전체 수정 |
| DELETE | `/api/projects/:id` | 프로젝트 삭제 |
| POST | `/api/deliverables` | 산출물 등록 |
| PATCH | `/api/deliverables/:id/status` | 산출물 상태 변경 |

### 5-3. Claude Code 연동
- Claude Code 세션 훅에서 이벤트를 `POST /api/activity`로 전송
- 실제 에이전트 작업 내역을 ActivityFeed에 반영
- `server/claude-hook.js` 작성 예정

### 5-4. 인증
- 관리자 로그인 (JWT 또는 간단한 API 키)
- 읽기/쓰기 권한 분리

---

## 6. 디자인 시스템 요약

다크 테마 전용. CSS 변수 기반 (`App.css` `:root` 섹션):

| 변수 | 값 | 용도 |
|------|-----|------|
| `--bg` | `#0f1117` | 페이지 배경 |
| `--bg2` | `#161b27` | 패널, 사이드바 |
| `--bg3` | `#1e2536` | 카드, 입력 |
| `--border` | `#2a3147` | 기본 테두리 |
| `--blue` | `#3b82f6` | 주요 액션, 활성 상태 |
| `--green` | `#22c55e` | 완료, 온라인 |
| `--orange` | `#f59e0b` | 경고, 대기 |
| `--purple` | `#a855f7` | AI 에이전트 |
| `--red` | `#ef4444` | 오류, 반려 |

---

## 7. 개발 환경

- Node.js 18+
- npm
- 서버: Express 4.x + ws 8.x
- 클라이언트: React 19 + Vite 6
- 브라우저: Chrome/Edge 최신 권장 (WebSocket 사용)
