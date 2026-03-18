import express from "express";
import { createServer } from "http";
import { WebSocketServer } from "ws";
import cors from "cors";
import { initialState } from "./data.js";

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server });

app.use(cors());
app.use(express.json());

// Deep clone state
let state = JSON.parse(JSON.stringify(initialState));

// ─── Broadcast to all connected clients ─────────────────────────────────────
function broadcast(event, data) {
  const payload = JSON.stringify({ event, data, timestamp: new Date().toISOString() });
  wss.clients.forEach((client) => {
    if (client.readyState === 1) client.send(payload);
  });
}

// ─── REST API ────────────────────────────────────────────────────────────────
app.get("/api/state", (req, res) => res.json(state));

app.patch("/api/agents/:id/status", (req, res) => {
  const { id } = req.params;
  const { status } = req.body;
  const agent = state.members.find((m) => m.id === id);
  if (!agent) return res.status(404).json({ error: "Agent not found" });
  agent.status = status;
  broadcast("agent:update", agent);
  res.json(agent);
});

app.patch("/api/projects/:id/status", (req, res) => {
  const { id } = req.params;
  const { status } = req.body;
  const project = state.projects.find((p) => p.id === id);
  if (!project) return res.status(404).json({ error: "Project not found" });
  project.status = status;
  if (status === "completed") project.progress = 100;
  broadcast("project:update", project);
  res.json(project);
});

// ─── WebSocket ───────────────────────────────────────────────────────────────
wss.on("connection", (ws) => {
  console.log("Client connected");
  ws.send(JSON.stringify({ event: "init", data: state, timestamp: new Date().toISOString() }));

  ws.on("close", () => console.log("Client disconnected"));
});

// ─── Real-time simulation ─────────────────────────────────────────────────────
const taskTemplates = [
  "코드 리뷰 진행 중",
  "유닛 테스트 실행",
  "API 응답 최적화",
  "문서 업데이트",
  "버그 수정 중",
  "스프린트 계획 검토",
  "성능 프로파일링",
  "보안 취약점 스캔",
  "데이터 마이그레이션 검증",
  "컴포넌트 테스트 작성",
];

const activityTemplates = [
  { action: "커밋 푸시: feat/dashboard-update", type: "commit" },
  { action: "PR #34 코드 리뷰 완료 → APPROVED", type: "review" },
  { action: "테스트 케이스 실행 → 12/12 PASS", type: "test" },
  { action: "산출물 업로드: API_spec_v3.pdf", type: "upload" },
  { action: "이슈 #89 수정 완료 → CLOSED", type: "fix" },
  { action: "스프린트 진행률 업데이트: 67%", type: "update" },
  { action: "데이터 파이프라인 검증 완료", type: "data" },
];

// Simulate agent activity every 8 seconds
setInterval(() => {
  const agents = state.members.filter((m) => m.type === "ai" && m.status !== "offline");
  const agent = agents[Math.floor(Math.random() * agents.length)];
  if (!agent) return;

  // Update task
  agent.currentTask = taskTemplates[Math.floor(Math.random() * taskTemplates.length)];
  broadcast("agent:update", agent);

  // Add activity
  const template = activityTemplates[Math.floor(Math.random() * activityTemplates.length)];
  const newActivity = {
    id: Date.now(),
    agentId: agent.id,
    action: template.action,
    time: "방금 전",
    type: template.type,
  };
  state.activityLog.unshift(newActivity);
  if (state.activityLog.length > 50) state.activityLog.pop();
  broadcast("activity:new", newActivity);
}, 8000);

// Simulate project progress every 20 seconds
setInterval(() => {
  const active = state.projects.filter((p) => p.status === "in_progress" && p.progress < 99);
  if (!active.length) return;
  const project = active[Math.floor(Math.random() * active.length)];
  project.progress = Math.min(99, project.progress + Math.floor(Math.random() * 3) + 1);
  broadcast("project:update", project);
}, 20000);

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
