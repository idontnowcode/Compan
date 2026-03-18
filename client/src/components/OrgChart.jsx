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

function MemberCard({ member, level, onSelect, selected }) {
  const isSelected = selected?.id === member.id;
  return (
    <div
      className={`org-card ${member.type} ${isSelected ? "selected" : ""}`}
      style={{ "--level": level }}
      onClick={() => onSelect(isSelected ? null : member)}
    >
      <div className="org-avatar" style={{ background: member.type === "human" ? "#1e40af" : "#6d28d9" }}>
        {member.avatar}
      </div>
      <div className="org-info">
        <div className="org-name">{member.name}</div>
        <div className="org-role">{member.role}</div>
        {member.type === "ai" && member.model && (
          <div className="org-model">{member.model}</div>
        )}
      </div>
      <div className="org-status-dot" style={{ background: statusColors[member.status] }} title={statusLabels[member.status]} />
    </div>
  );
}

function OrgNode({ member, allMembers, level, onSelect, selected }) {
  const children = allMembers.filter((m) => m.reportsTo === member.id);
  return (
    <div className="org-node">
      <MemberCard member={member} level={level} onSelect={onSelect} selected={selected} />
      {children.length > 0 && (
        <div className="org-children">
          {children.map((child) => (
            <OrgNode
              key={child.id}
              member={child}
              allMembers={allMembers}
              level={level + 1}
              onSelect={onSelect}
              selected={selected}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function OrgChart({ members }) {
  const [selected, setSelected] = useState(null);
  const roots = members.filter((m) => m.reportsTo === null);

  const depts = {};
  members.forEach((m) => {
    if (!depts[m.department]) depts[m.department] = { total: 0, active: 0 };
    depts[m.department].total++;
    if (m.status === "active" || m.status === "online") depts[m.department].active++;
  });

  return (
    <div className="panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <span className="panel-icon">🏢</span>
          조직도
        </h2>
        <div className="org-stats">
          {Object.entries(depts).map(([dept, info]) => (
            <span key={dept} className="dept-badge">
              {dept} <strong>{info.active}/{info.total}</strong>
            </span>
          ))}
        </div>
      </div>

      <div className="org-tree">
        {roots.map((root) => (
          <OrgNode
            key={root.id}
            member={root}
            allMembers={members}
            level={0}
            onSelect={setSelected}
            selected={selected}
          />
        ))}
      </div>

      {selected && (
        <div className="org-detail-panel">
          <button className="detail-close" onClick={() => setSelected(null)}>✕</button>
          <div className="detail-header">
            <div className="detail-avatar" style={{ background: selected.type === "human" ? "#1e40af" : "#6d28d9" }}>
              {selected.avatar}
            </div>
            <div>
              <div className="detail-name">{selected.name}</div>
              {selected.fullName && <div className="detail-fullname">{selected.fullName}</div>}
              <div className="detail-role">{selected.role}</div>
            </div>
          </div>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">상태</span>
              <span className="detail-value" style={{ color: statusColors[selected.status] }}>
                ● {statusLabels[selected.status]}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">부서</span>
              <span className="detail-value">{selected.department}</span>
            </div>
            {selected.model && (
              <div className="detail-item">
                <span className="detail-label">모델</span>
                <span className="detail-value model-tag">{selected.model}</span>
              </div>
            )}
            {selected.performance !== undefined && (
              <div className="detail-item">
                <span className="detail-label">성과 점수</span>
                <span className="detail-value">{selected.performance}점</span>
              </div>
            )}
            {selected.tasksCompleted !== undefined && (
              <div className="detail-item">
                <span className="detail-label">완료 태스크</span>
                <span className="detail-value">{selected.tasksCompleted}건</span>
              </div>
            )}
            {selected.email && (
              <div className="detail-item">
                <span className="detail-label">이메일</span>
                <span className="detail-value">{selected.email}</span>
              </div>
            )}
          </div>
          {selected.currentTask && (
            <div className="detail-task">
              <span className="detail-label">현재 작업</span>
              <div className="current-task-badge">⚡ {selected.currentTask}</div>
            </div>
          )}
          {selected.capabilities && (
            <div className="detail-caps">
              <span className="detail-label">역량</span>
              <div className="caps-list">
                {selected.capabilities.map((cap) => (
                  <span key={cap} className="cap-tag">{cap}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
