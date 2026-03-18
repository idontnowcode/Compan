import { useState, useCallback } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import OrgChart from "./components/OrgChart";
import AgentList from "./components/AgentList";
import ProjectBoard from "./components/ProjectBoard";
import Deliverables from "./components/Deliverables";
import ActivityFeed from "./components/ActivityFeed";
import "./App.css";

const WS_URL = "ws://localhost:3001";
const API_URL = "http://localhost:3001/api";

const tabs = [
  { key: "overview", label: "개요", icon: "🏠" },
  { key: "org", label: "조직도", icon: "🏢" },
  { key: "agents", label: "에이전트", icon: "🤖" },
  { key: "projects", label: "프로젝트", icon: "📊" },
  { key: "deliverables", label: "산출물", icon: "📦" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  const handlers = {
    init: useCallback((d) => {
      setData(d);
      setConnected(true);
      setLastUpdate(new Date());
    }, []),

    "agent:update": useCallback((updated) => {
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          members: prev.members.map((m) => (m.id === updated.id ? updated : m)),
        };
      });
      setLastUpdate(new Date());
    }, []),

    "project:update": useCallback((updated) => {
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          projects: prev.projects.map((p) => (p.id === updated.id ? updated : p)),
        };
      });
      setLastUpdate(new Date());
    }, []),

    "activity:new": useCallback((activity) => {
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          activityLog: [activity, ...prev.activityLog].slice(0, 50),
        };
      });
      setLastUpdate(new Date());
    }, []),
  };

  useWebSocket(WS_URL, handlers);

  async function handleAgentStatusChange(agentId, status) {
    await fetch(`${API_URL}/agents/${agentId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
  }

  async function handleProjectStatusChange(projectId, status) {
    await fetch(`${API_URL}/projects/${projectId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
  }

  if (!data) {
    return (
      <div className="loading-screen">
        <div className="loading-logo">COMPAN</div>
        <div className="loading-text">AI 관리 시스템 연결 중...</div>
        <div className="loading-dots">
          <span /><span /><span />
        </div>
      </div>
    );
  }

  const activeAgents = data.members.filter((m) => m.type === "ai" && m.status === "active").length;
  const totalAgents = data.members.filter((m) => m.type === "ai").length;
  const inProgressProjects = data.projects.filter((p) => p.status === "in_progress").length;
  const completedProjects = data.projects.filter((p) => p.status === "completed").length;
  const pendingDeliverables = data.deliverables.filter((d) => d.status === "in_review").length;

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-mark">C</div>
          <div className="logo-text">
            <span className="logo-name">COMPAN</span>
            <span className="logo-sub">AI Management</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              className={`nav-item ${activeTab === tab.key ? "active" : ""}`}
              onClick={() => setActiveTab(tab.key)}
            >
              <span className="nav-icon">{tab.icon}</span>
              <span className="nav-label">{tab.label}</span>
              {tab.key === "agents" && (
                <span className="nav-badge">{activeAgents}/{totalAgents}</span>
              )}
              {tab.key === "projects" && inProgressProjects > 0 && (
                <span className="nav-badge">{inProgressProjects}</span>
              )}
              {tab.key === "deliverables" && pendingDeliverables > 0 && (
                <span className="nav-badge alert">{pendingDeliverables}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-status">
          <div className={`ws-indicator ${connected ? "connected" : "disconnected"}`}>
            <span className="ws-dot" />
            {connected ? "실시간 연결됨" : "연결 끊김"}
          </div>
          {lastUpdate && (
            <div className="last-update">
              {lastUpdate.toLocaleTimeString("ko-KR")} 업데이트
            </div>
          )}
        </div>
      </aside>

      {/* Main */}
      <main className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <h1 className="page-title">
              {tabs.find((t) => t.key === activeTab)?.icon}{" "}
              {tabs.find((t) => t.key === activeTab)?.label}
            </h1>
          </div>
          <div className="topbar-right">
            <div className="quick-stats">
              <div className="qstat">
                <span className="qstat-val" style={{ color: "#3b82f6" }}>{activeAgents}</span>
                <span className="qstat-label">활성 AI</span>
              </div>
              <div className="qstat">
                <span className="qstat-val" style={{ color: "#f59e0b" }}>{inProgressProjects}</span>
                <span className="qstat-label">진행 프로젝트</span>
              </div>
              <div className="qstat">
                <span className="qstat-val" style={{ color: "#22c55e" }}>{completedProjects}</span>
                <span className="qstat-label">완료 프로젝트</span>
              </div>
              <div className="qstat">
                <span className="qstat-val" style={{ color: "#a855f7" }}>{pendingDeliverables}</span>
                <span className="qstat-label">검토 대기</span>
              </div>
            </div>
          </div>
        </header>

        <div className="content-area">
          {activeTab === "overview" && (
            <OverviewTab data={data} />
          )}
          {activeTab === "org" && <OrgChart members={data.members} />}
          {activeTab === "agents" && (
            <AgentList members={data.members} onStatusChange={handleAgentStatusChange} />
          )}
          {activeTab === "projects" && (
            <ProjectBoard
              projects={data.projects}
              members={data.members}
              onStatusChange={handleProjectStatusChange}
            />
          )}
          {activeTab === "deliverables" && (
            <Deliverables
              deliverables={data.deliverables}
              members={data.members}
              projects={data.projects}
            />
          )}
        </div>
      </main>

      {/* Activity sidebar */}
      <aside className="activity-sidebar">
        <ActivityFeed activities={data.activityLog} members={data.members} />
      </aside>
    </div>
  );
}

function OverviewTab({ data }) {
  const aiAgents = data.members.filter((m) => m.type === "ai");
  const activeCount = aiAgents.filter((m) => m.status === "active").length;
  const inProgressProjects = data.projects.filter((p) => p.status === "in_progress");
  const avgProgress = inProgressProjects.length
    ? Math.round(inProgressProjects.reduce((s, p) => s + p.progress, 0) / inProgressProjects.length)
    : 0;

  return (
    <div className="overview-grid">
      <div className="kpi-row">
        <div className="kpi-card blue">
          <div className="kpi-icon">🤖</div>
          <div className="kpi-val">{activeCount}<span>/{aiAgents.length}</span></div>
          <div className="kpi-label">AI 에이전트 활성</div>
          <div className="kpi-bar"><div style={{ width: `${(activeCount / aiAgents.length) * 100}%` }} /></div>
        </div>
        <div className="kpi-card orange">
          <div className="kpi-icon">⚡</div>
          <div className="kpi-val">{inProgressProjects.length}</div>
          <div className="kpi-label">진행 중 프로젝트</div>
          <div className="kpi-sub">평균 진행률 {avgProgress}%</div>
        </div>
        <div className="kpi-card green">
          <div className="kpi-icon">✅</div>
          <div className="kpi-val">{data.projects.filter((p) => p.status === "completed").length}</div>
          <div className="kpi-label">완료된 프로젝트</div>
          <div className="kpi-sub">총 {data.projects.length}개 프로젝트</div>
        </div>
        <div className="kpi-card purple">
          <div className="kpi-icon">📦</div>
          <div className="kpi-val">{data.deliverables.filter((d) => d.status === "approved").length}</div>
          <div className="kpi-label">승인된 산출물</div>
          <div className="kpi-sub">검토 대기 {data.deliverables.filter((d) => d.status === "in_review").length}건</div>
        </div>
      </div>

      <div className="overview-section">
        <h3 className="section-title">⚡ 현재 작업 중인 AI</h3>
        <div className="active-agents-list">
          {aiAgents.filter((a) => a.status === "active" && a.currentTask).map((agent) => (
            <div key={agent.id} className="active-agent-row">
              <div className="mini-avatar" style={{ background: "#6d28d9" }}>{agent.avatar}</div>
              <div className="active-agent-info">
                <span className="active-agent-name">{agent.name}</span>
                <span className="active-agent-role">{agent.role}</span>
              </div>
              <div className="active-task">
                <span className="task-pulse" />
                {agent.currentTask}
              </div>
              <div className="perf-mini">
                <div className="perf-bar">
                  <div style={{ width: `${agent.performance}%`, background: "#3b82f6" }} />
                </div>
                <span>{agent.performance}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="overview-section">
        <h3 className="section-title">📊 진행 중 프로젝트</h3>
        <div className="overview-projects">
          {inProgressProjects.map((proj) => (
            <div key={proj.id} className="overview-project-row">
              <span className="ov-proj-name">{proj.name}</span>
              <div className="ov-progress">
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${proj.progress}%` }} />
                </div>
                <span>{proj.progress}%</span>
              </div>
              <span className="ov-due">{proj.dueDate}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="overview-section">
        <h3 className="section-title">🏆 AI 성과 순위</h3>
        <div className="ranking-list">
          {[...aiAgents].sort((a, b) => (b.performance ?? 0) - (a.performance ?? 0)).slice(0, 5).map((agent, i) => (
            <div key={agent.id} className="ranking-row">
              <span className={`rank-num rank-${i + 1}`}>{i + 1}</span>
              <div className="mini-avatar" style={{ background: "#6d28d9" }}>{agent.avatar}</div>
              <span className="rank-name">{agent.name}</span>
              <span className="rank-role">{agent.role}</span>
              <div className="rank-score">
                <div className="rank-bar">
                  <div style={{ width: `${agent.performance}%`, background: i === 0 ? "#f59e0b" : i === 1 ? "#9ca3af" : i === 2 ? "#b45309" : "#3b82f6" }} />
                </div>
                <span>{agent.performance}%</span>
              </div>
              <span className="rank-tasks">{agent.tasksCompleted}건</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
