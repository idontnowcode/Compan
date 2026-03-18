import { useState } from "react";

const typeConfig = {
  document: { icon: "📄", label: "문서", color: "#3b82f6" },
  code: { icon: "💻", label: "코드", color: "#8b5cf6" },
  design: { icon: "🎨", label: "디자인", color: "#ec4899" },
  report: { icon: "📊", label: "리포트", color: "#f59e0b" },
  data: { icon: "🗄️", label: "데이터", color: "#06b6d4" },
};

const statusConfig = {
  approved: { label: "승인됨", color: "#22c55e", bg: "#f0fdf4" },
  in_review: { label: "검토 중", color: "#f59e0b", bg: "#fefce8" },
  draft: { label: "초안", color: "#6b7280", bg: "#f9fafb" },
  rejected: { label: "반려", color: "#ef4444", bg: "#fef2f2" },
};

function getMemberById(members, id) {
  return members.find((m) => m.id === id);
}

function getProjectById(projects, id) {
  return projects.find((p) => p.id === id);
}

function timeAgo(isoString) {
  const diff = (Date.now() - new Date(isoString)) / 1000;
  if (diff < 60) return "방금 전";
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

export default function Deliverables({ deliverables, members, projects }) {
  const [filter, setFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [search, setSearch] = useState("");

  const filtered = deliverables
    .filter((d) => {
      if (filter !== "all" && d.status !== filter) return false;
      if (typeFilter !== "all" && d.type !== typeFilter) return false;
      if (search && !d.name.toLowerCase().includes(search.toLowerCase()) &&
          !d.description.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    })
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

  const counts = {
    all: deliverables.length,
    approved: deliverables.filter((d) => d.status === "approved").length,
    in_review: deliverables.filter((d) => d.status === "in_review").length,
    draft: deliverables.filter((d) => d.status === "draft").length,
  };

  const typeCounts = {};
  deliverables.forEach((d) => {
    typeCounts[d.type] = (typeCounts[d.type] || 0) + 1;
  });

  return (
    <div className="panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <span className="panel-icon">📦</span>
          산출물 관리
        </h2>
        <div className="deliverable-stats">
          <span className="stat-badge approved">승인 {counts.approved}</span>
          <span className="stat-badge review">검토 {counts.in_review}</span>
          <span className="stat-badge draft">초안 {counts.draft}</span>
        </div>
      </div>

      <div className="deliverable-controls">
        <input
          className="search-input"
          placeholder="산출물 검색..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-row">
          <div className="filter-tabs">
            {[
              { key: "all", label: `전체 (${counts.all})` },
              { key: "approved", label: `승인 (${counts.approved})` },
              { key: "in_review", label: `검토중 (${counts.in_review})` },
              { key: "draft", label: `초안 (${counts.draft})` },
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
          <div className="type-filters">
            <button
              className={`type-tab ${typeFilter === "all" ? "active" : ""}`}
              onClick={() => setTypeFilter("all")}
            >
              전체 유형
            </button>
            {Object.entries(typeConfig).map(([key, cfg]) => (
              <button
                key={key}
                className={`type-tab ${typeFilter === key ? "active" : ""}`}
                onClick={() => setTypeFilter(key)}
                style={typeFilter === key ? { borderColor: cfg.color, color: cfg.color } : {}}
              >
                {cfg.icon} {cfg.label} {typeCounts[key] ? `(${typeCounts[key]})` : ""}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="deliverable-list">
        {filtered.map((item) => {
          const author = getMemberById(members, item.author);
          const project = getProjectById(projects, item.projectId);
          const typeCfg = typeConfig[item.type] ?? typeConfig.document;
          const statusCfg = statusConfig[item.status] ?? statusConfig.draft;

          return (
            <div key={item.id} className="deliverable-row">
              <div className="del-type-icon" style={{ background: typeCfg.color + "18", color: typeCfg.color }}>
                {typeCfg.icon}
              </div>

              <div className="del-main">
                <div className="del-name-row">
                  <span className="del-name">{item.name}</span>
                  <span className="del-format">{item.format}</span>
                  <span className="del-status" style={{ color: statusCfg.color, background: statusCfg.bg }}>
                    {statusCfg.label}
                  </span>
                </div>
                <div className="del-desc">{item.description}</div>
                <div className="del-meta">
                  {author && (
                    <span className="del-author">
                      <span className="mini-avatar" style={{ background: author.type === "human" ? "#1e40af" : "#6d28d9" }}>
                        {author.avatar}
                      </span>
                      {author.name}
                    </span>
                  )}
                  {project && (
                    <span className="del-project">
                      📌 {project.name}
                    </span>
                  )}
                  <span className="del-size">💾 {item.size}</span>
                  <span className="del-time">🕐 {timeAgo(item.createdAt)}</span>
                </div>
              </div>

              <div className="del-actions">
                <button className="del-btn view" title="미리보기">👁</button>
                <button className="del-btn download" title="다운로드">⬇</button>
                {item.status === "in_review" && (
                  <button className="del-btn approve" title="승인">✓</button>
                )}
              </div>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div className="empty-state">해당하는 산출물이 없습니다.</div>
        )}
      </div>
    </div>
  );
}
