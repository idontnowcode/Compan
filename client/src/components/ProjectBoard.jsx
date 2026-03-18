import { useState } from "react";

const priorityConfig = {
  critical: { label: "긴급", color: "#dc2626", bg: "#fef2f2" },
  high: { label: "높음", color: "#ea580c", bg: "#fff7ed" },
  medium: { label: "보통", color: "#ca8a04", bg: "#fefce8" },
  low: { label: "낮음", color: "#16a34a", bg: "#f0fdf4" },
};

const columns = [
  { key: "planned", label: "예정", icon: "📋", color: "#6b7280" },
  { key: "in_progress", label: "진행 중", icon: "⚡", color: "#3b82f6" },
  { key: "completed", label: "완료", icon: "✅", color: "#22c55e" },
];

function getMemberById(members, id) {
  return members.find((m) => m.id === id);
}

function ProjectCard({ project, members, onStatusChange }) {
  const [expanded, setExpanded] = useState(false);
  const owner = getMemberById(members, project.owner);
  const teamMembers = project.team.map((id) => getMemberById(members, id)).filter(Boolean);
  const pri = priorityConfig[project.priority] ?? priorityConfig.medium;
  const daysLeft = project.dueDate
    ? Math.ceil((new Date(project.dueDate) - new Date()) / 86400000)
    : null;

  return (
    <div className={`project-card ${project.status}`}>
      <div className="project-card-top">
        <div className="project-priority" style={{ color: pri.color, background: pri.bg }}>
          {pri.label}
        </div>
        {project.sprint && <span className="project-sprint">{project.sprint}</span>}
      </div>

      <div className="project-title" onClick={() => setExpanded(!expanded)}>
        {project.name}
        <span className="expand-btn">{expanded ? "▲" : "▼"}</span>
      </div>

      <div className="project-desc">{project.description}</div>

      {project.status === "in_progress" && (
        <div className="project-progress-wrap">
          <div className="progress-header">
            <span>진행률</span>
            <strong>{project.progress}%</strong>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${project.progress}%` }} />
          </div>
        </div>
      )}

      <div className="project-meta">
        {owner && (
          <div className="project-owner">
            <span className="meta-avatar" style={{ background: owner.type === "human" ? "#1e40af" : "#6d28d9" }}>
              {owner.avatar}
            </span>
            <span>{owner.name}</span>
          </div>
        )}
        {daysLeft !== null && project.status !== "completed" && (
          <span className={`due-badge ${daysLeft < 0 ? "overdue" : daysLeft <= 3 ? "urgent" : ""}`}>
            {daysLeft < 0 ? `${Math.abs(daysLeft)}일 초과` : `D-${daysLeft}`}
          </span>
        )}
      </div>

      {expanded && (
        <div className="project-expanded">
          <div className="project-team">
            <span className="meta-label">팀원</span>
            <div className="team-avatars">
              {teamMembers.map((m) => (
                <div
                  key={m.id}
                  className="team-avatar"
                  title={`${m.name} (${m.role})`}
                  style={{ background: m.type === "human" ? "#1e40af" : "#6d28d9" }}
                >
                  {m.avatar}
                </div>
              ))}
            </div>
          </div>
          <div className="project-dates">
            <span>시작: {project.startDate}</span>
            <span>마감: {project.dueDate}</span>
          </div>
          <div className="project-tags">
            {project.tags.map((tag) => (
              <span key={tag} className="tag">{tag}</span>
            ))}
          </div>
          {project.status !== "completed" && (
            <div className="project-actions">
              {project.status === "planned" && (
                <button className="action-btn primary" onClick={() => onStatusChange(project.id, "in_progress")}>
                  ▶ 시작하기
                </button>
              )}
              {project.status === "in_progress" && (
                <button className="action-btn success" onClick={() => onStatusChange(project.id, "completed")}>
                  ✓ 완료 처리
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProjectBoard({ projects, members, onStatusChange }) {
  const [view, setView] = useState("board");

  const stats = {
    planned: projects.filter((p) => p.status === "planned").length,
    in_progress: projects.filter((p) => p.status === "in_progress").length,
    completed: projects.filter((p) => p.status === "completed").length,
  };

  const avgProgress =
    projects.filter((p) => p.status === "in_progress").length > 0
      ? Math.round(
          projects.filter((p) => p.status === "in_progress").reduce((s, p) => s + p.progress, 0) /
            projects.filter((p) => p.status === "in_progress").length
        )
      : 0;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <span className="panel-icon">📊</span>
          프로젝트 현황
        </h2>
        <div className="project-header-right">
          <div className="project-stat-chips">
            <span className="stat-chip planned">예정 {stats.planned}</span>
            <span className="stat-chip in_progress">진행 {stats.in_progress}</span>
            <span className="stat-chip completed">완료 {stats.completed}</span>
            {stats.in_progress > 0 && (
              <span className="stat-chip progress">평균 {avgProgress}%</span>
            )}
          </div>
          <div className="view-toggle">
            <button className={view === "board" ? "active" : ""} onClick={() => setView("board")}>보드</button>
            <button className={view === "list" ? "active" : ""} onClick={() => setView("list")}>목록</button>
          </div>
        </div>
      </div>

      {view === "board" ? (
        <div className="kanban-board">
          {columns.map((col) => {
            const colProjects = projects.filter((p) => p.status === col.key);
            return (
              <div key={col.key} className="kanban-column">
                <div className="kanban-col-header" style={{ borderColor: col.color }}>
                  <span className="col-icon">{col.icon}</span>
                  <span className="col-label" style={{ color: col.color }}>{col.label}</span>
                  <span className="col-count">{colProjects.length}</span>
                </div>
                <div className="kanban-cards">
                  {colProjects.map((project) => (
                    <ProjectCard
                      key={project.id}
                      project={project}
                      members={members}
                      onStatusChange={onStatusChange}
                    />
                  ))}
                  {colProjects.length === 0 && (
                    <div className="empty-col">프로젝트 없음</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="project-list">
          {projects.map((project) => {
            const owner = getMemberById(members, project.owner);
            const col = columns.find((c) => c.key === project.status);
            const pri = priorityConfig[project.priority] ?? priorityConfig.medium;
            return (
              <div key={project.id} className="project-list-row">
                <span className="list-status" style={{ color: col?.color }}>
                  {col?.icon} {col?.label}
                </span>
                <span className="list-name">{project.name}</span>
                <span className="list-priority" style={{ color: pri.color }}>{pri.label}</span>
                <span className="list-owner">{owner?.name}</span>
                <span className="list-progress">
                  {project.status === "in_progress" ? `${project.progress}%` : project.status === "completed" ? "완료" : "-"}
                </span>
                <span className="list-due">{project.dueDate}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
