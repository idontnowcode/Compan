const activityIcons = {
  commit: "💾",
  review: "🔍",
  test: "🧪",
  upload: "📤",
  update: "📝",
  fix: "🔧",
  data: "📊",
  message: "💬",
};

export default function ActivityFeed({ activities, members }) {
  function getMember(id) {
    return members.find((m) => m.id === id);
  }

  return (
    <div className="activity-feed">
      <div className="feed-title">
        <span>🔴</span> 실시간 활동
      </div>
      <div className="feed-list">
        {activities.slice(0, 12).map((act) => {
          const member = getMember(act.agentId);
          return (
            <div key={act.id} className="feed-item">
              <span className="feed-icon">{activityIcons[act.type] ?? "▶"}</span>
              <div className="feed-content">
                <span className="feed-actor" style={{ color: member?.type === "human" ? "#60a5fa" : "#a78bfa" }}>
                  {member?.name ?? act.agentId}
                </span>
                <span className="feed-action">{act.action}</span>
              </div>
              <span className="feed-time">{act.time}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
