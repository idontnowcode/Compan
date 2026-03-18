import { useState } from "react";

const statusColors = {
  online: "#22c55e",
  active: "#3b82f6",
  idle: "#f59e0b",
  waiting: "#a855f7",
  offline: "#6b7280",
};

const statusLabels = {
  online: "온라인",
  active: "작업 중",
  idle: "대기",
  waiting: "보류",
  offline: "오프라인",
};

const typeIcons = {
  human: "👤",
  ai: "🤖",
};

const modelColors = {
  "claude-opus-4-6": "#7c3aed",
  "claude-sonnet-4-6": "#2563eb",
  "claude-haiku-4-5": "#059669",
};

export default function AgentList({ members, onStatusChange }) {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("status");

  const filtered = members
    .filter((m) => {
      if (filter === "human") return m.type === "human";
      if (filter === "ai") return m.type === "ai";
      if (filter === "active") return m.status === "active";
      if (filter === "idle") return m.status === "idle";
      return true;
    })
    .filter((m) =>
      search === "" ||
      m.name.includes(search) ||
      m.role.includes(search) ||
      (m.department || "").includes(search)
    )
    .sort((a, b) => {
      if (sortBy === "status") {
        const order = { active: 0, online: 1, waiting: 2, idle: 3, offline: 4 };
        return (order[a.status] ?? 5) - (order[b.status] ?? 5);
      }
      if (sortBy === "performance") return (b.performance ?? 0) - (a.performance ?? 0);
      if (sortBy === "tasks") return (b.tasksCompleted ?? 0) - (a.tasksCompleted ?? 0);
      return a.name.localeCompare(b.name);
    });

  const counts = {
    all: members.length,
    human: members.filter((m) => m.type === "human").length,
    ai: members.filter((m) => m.type === "ai").length,
    active: members.filter((m) => m.status === "active").length,
    idle: members.filter((m) => m.status === "idle").length,
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <span className="panel-icon">👥</span>
          에이전트 디렉토리
        </h2>
        <div className="agent-summary">
          <span className="summary-item active">
            <span style={{ color: statusColors.active }}>●</span> 활성 {counts.active}
          </span>
          <span className="summary-item">총 {counts.all}명</span>
        </div>
      </div>

      <div className="agent-controls">
        <input
          className="search-input"
          placeholder="이름, 역할, 부서 검색..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-tabs">
          {[
            { key: "all", label: `전체 (${counts.all})` },
            { key: "ai", label: `AI (${counts.ai})` },
            { key: "human", label: `인간 (${counts.human})` },
            { key: "active", label: `작업중 (${counts.active})` },
            { key: "idle", label: `대기 (${counts.idle})` },
          ].map((f) => (
            <button
              key={f.key}
              className={`filter-tab ${filter === f.key ? "active" : ""}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <select className="sort-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="status">상태순</option>
          <option value="performance">성과순</option>
          <option value="tasks">완료 태스크순</option>
          <option value="name">이름순</option>
        </select>
      </div>

      <div className="agent-grid">
        {filtered.map((member) => (
          <AgentCard key={member.id} member={member} onStatusChange={onStatusChange} />
        ))}
        {filtered.length === 0 && (
          <div className="empty-state">검색 결과가 없습니다.</div>
        )}
      </div>
    </div>
  );
}

function AgentCard({ member, onStatusChange }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className={`agent-card ${member.status}`}>
      <div className="agent-card-header">
        <div className="agent-avatar-wrap">
          <div className="agent-avatar" style={{ background: member.type === "human" ? "#1e40af" : "#6d28d9" }}>
            {member.avatar}
          </div>
          <span className="agent-type-icon">{typeIcons[member.type]}</span>
        </div>
        <div className="agent-header-info">
          <div className="agent-name-row">
            <span className="agent-name">{member.name}</span>
            <span
              className="status-badge"
              style={{ background: statusColors[member.status] + "22", color: statusColors[member.status] }}
            >
              ● {statusLabels[member.status]}
            </span>
          </div>
          <div className="agent-role">{member.role}</div>
          <div className="agent-dept">{member.department}</div>
        </div>
        {member.type === "ai" && (
          <div className="agent-menu-wrap">
            <button className="agent-menu-btn" onClick={() => setMenuOpen(!menuOpen)}>⋮</button>
            {menuOpen && (
              <div className="agent-menu">
                {["active", "idle", "waiting", "offline"].map((s) => (
                  <button
                    key={s}
                    className="agent-menu-item"
                    onClick={() => {
                      onStatusChange(member.id, s);
                      setMenuOpen(false);
                    }}
                  >
                    <span style={{ color: statusColors[s] }}>●</span> {statusLabels[s]}로 변경
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {member.model && (
        <div className="agent-model-tag" style={{ borderColor: modelColors[member.model] ?? "#6b7280", color: modelColors[member.model] ?? "#6b7280" }}>
          {member.model}
        </div>
      )}

      {member.currentTask && (
        <div className="agent-task">
          <span className="task-pulse" />
          {member.currentTask}
        </div>
      )}

      {member.performance !== undefined && (
        <div className="agent-metrics">
          <div className="metric">
            <span className="metric-label">성과</span>
            <div className="metric-bar">
              <div className="metric-fill" style={{ width: `${member.performance}%`, background: member.performance >= 90 ? "#22c55e" : member.performance >= 75 ? "#f59e0b" : "#ef4444" }} />
            </div>
            <span className="metric-value">{member.performance}%</span>
          </div>
          <div className="metric-count">
            완료 태스크 <strong>{member.tasksCompleted}</strong>건
          </div>
        </div>
      )}

      {member.capabilities && (
        <div className="agent-caps">
          {member.capabilities.slice(0, 3).map((cap) => (
            <span key={cap} className="cap-tag">{cap}</span>
          ))}
          {member.capabilities.length > 3 && (
            <span className="cap-tag more">+{member.capabilities.length - 3}</span>
          )}
        </div>
      )}
    </div>
  );
}
