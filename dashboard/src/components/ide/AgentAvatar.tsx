import { avatarMarkup } from "@/data/avatars";
import type { AgentCard } from "@/types/idea";

export function AgentAvatar({
  agent,
  size = 34,
  rounded = "28%",
  title,
}: {
  agent: AgentCard;
  size?: number;
  rounded?: string;
  title?: string;
}) {
  return (
    <span
      className="agent-avatar"
      role="img"
      aria-label={`Avatar de ${agent.name}`}
      title={title ?? agent.title}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size,
        borderRadius: rounded,
        overflow: "hidden",
        flexShrink: 0,
        lineHeight: 0,
      }}
    >
      <span
        style={{ display: "block", width: "100%", height: "100%" }}
        dangerouslySetInnerHTML={{ __html: avatarMarkup(agent) }}
      />
    </span>
  );
}
