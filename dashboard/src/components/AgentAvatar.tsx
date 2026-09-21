import { memo, type CSSProperties, type ReactElement } from "react";
import { getAvatarSpec, type AvatarSpec } from "@/data/avatarSpec";

/**
 * Avatar profissional procedural de um agente NEMO.
 *
 * Renderiza um retrato SVG determinÃ­stico (mesmo agente => mesmo rosto) sobre
 * um fundo com a cor de identidade do agente. Substitui os placeholders de
 * emoji em cards, chat, listas, notificaÃ§Ãµes, histÃ³rico e painÃ©is.
 */

interface AgentAvatarProps {
  id: string;
  accent?: string;
  size?: number;
  shape?: "round" | "square";
  badge?: string | null;
  className?: string;
  style?: CSSProperties;
  title?: string;
}

function mix(hex: string, other: string, t: number): string {
  const parse = (h: string) => {
    const m = /^#?([0-9a-fA-F]{6})$/.exec(h.trim());
    return m ? parseInt(m[1], 16) : 0x38bdf8;
  };
  const a = parse(hex);
  const b = parse(other);
  const r = Math.round(((a >> 16) & 255) * (1 - t) + ((b >> 16) & 255) * t);
  const g = Math.round(((a >> 8) & 255) * (1 - t) + ((b >> 8) & 255) * t);
  const bl = Math.round((a & 255) * (1 - t) + (b & 255) * t);
  return `#${((r << 16) | (g << 8) | bl).toString(16).padStart(6, "0")}`;
}

const shade = (hex: string, factor: number): string => (factor <= 1 ? mix(hex, "#000000", 1 - factor) : mix(hex, "#ffffff", factor - 1));

function hairCap(s: AvatarSpec): ReactElement {
  const h = s.hair;
  switch (s.hairStyle) {
    case "buzz":
      return <path d="M29,50 C29,34 71,34 71,50 L71,44 C71,34 29,34 29,44 Z" fill={h} />;
    case "bald":
      return <path d="M33,46 C38,36 62,36 68,46 L63,44 C57,38 43,38 37,44 Z" fill={h} />;
    case "pixie":
      return (
        <g>
          <path d="M28,52 C28,34 72,34 72,52 C70,44 62,40 50,40 C38,40 30,44 28,52 Z" fill={h} />
          <circle cx="41" cy="34" r="6" fill={h} />
        </g>
      );
    case "bun":
      return (
        <g>
          <circle cx="50" cy="25" r="9.5" fill={h} />
          <path d="M28,52 C28,34 72,34 72,52 C68,44 60,40 50,40 C40,40 32,44 28,52 Z" fill={h} />
        </g>
      );
    case "ponytail":
      return (
        <g>
          <path d="M30,52 C30,32 70,32 70,52 C66,44 58,40 50,40 C42,40 34,44 30,52 Z" fill={h} />
          <path d="M68,44 C86,42 90,58 80,70 C74,78 70,72 70,72 C77,60 75,50 66,48 Z" fill={h} />
        </g>
      );
    case "curly":
      return (
        <g>
          <path d="M28,54 C28,32 72,32 72,54 C68,46 58,42 50,42 C42,42 32,46 28,54 Z" fill={h} />
          <circle cx="36" cy="36" r="7" fill={h} />
          <circle cx="46" cy="32" r="8" fill={h} />
          <circle cx="56" cy="33" r="8" fill={h} />
          <circle cx="65" cy="38" r="6" fill={h} />
        </g>
      );
    case "long":
      return (
        <g>
          <rect x="27" y="42" width="12" height="36" rx="6" fill={h} />
          <rect x="61" y="42" width="12" height="36" rx="6" fill={h} />
          <path d="M28,52 C28,34 72,34 72,52 C68,44 60,40 50,40 C40,40 32,44 28,52 Z" fill={h} />
        </g>
      );
    case "bob":
      return (
        <g>
          <rect x="27" y="42" width="11" height="28" rx="5.5" fill={h} />
          <rect x="62" y="42" width="11" height="28" rx="5.5" fill={h} />
          <path d="M28,52 C28,34 72,34 72,52 C68,44 60,40 50,40 C40,40 32,44 28,52 Z" fill={h} />
        </g>
      );
    default:
      return <path d="M28,54 C28,30 72,30 72,54 C68,44 62,38 50,38 C38,38 32,44 28,54 Z" fill={h} />;
  }
}

function glasses(s: AvatarSpec): ReactElement | null {
  if (s.glasses === "none") return null;
  const stroke = "#1c2733";
  const lw = 2.4;
  if (s.glasses === "round") {
    return (
      <g fill="none" stroke={stroke} strokeWidth={lw}>
        <circle cx="37" cy="58" r="7.5" fill="rgba(255,255,255,0.06)" />
        <circle cx="63" cy="58" r="7.5" fill="rgba(255,255,255,0.06)" />
        <path d="M44.5,58 L55.5,58" />
      </g>
    );
  }
  return (
    <g fill="rgba(255,255,255,0.05)" stroke={stroke} strokeWidth={lw}>
      <rect x="29.5" y="50.5" width="15.5" height="15" rx="4.5" />
      <rect x="55" y="50.5" width="15.5" height="15" rx="4.5" />
      <path d="M45,57 L55,57" fill="none" />
    </g>
  );
}

function accessories(s: AvatarSpec, accent: string): ReactElement | null {
  switch (s.accessory) {
    case "headset":
      return (
        <g>
          <path d="M24,40 C24,15 76,15 76,40" fill="none" stroke="#171b22" strokeWidth="7" strokeLinecap="round" />
          <path d="M24,40 C24,20 76,20 76,40" fill="none" stroke={accent} strokeWidth="1.8" strokeLinecap="round" opacity="0.9" />
          <rect x="19.5" y="46" width="9.5" height="19" rx="4.7" fill="#171b22" />
          <rect x="71" y="46" width="9.5" height="19" rx="4.7" fill="#171b22" />
          <circle cx="75.5" cy="58" r="2" fill={accent} />
          <path d="M71,56 L60,72" stroke="#171b22" strokeWidth="3.4" strokeLinecap="round" />
          <circle cx="59.5" cy="73.5" r="4" fill={accent} stroke="#171b22" strokeWidth="2" />
        </g>
      );
    case "beret":
      return (
        <g>
          <ellipse cx="50" cy="24" rx="27" ry="11" fill={shade(s.hair, 1.28)} transform="rotate(-6 50 24)" />
          <rect x="47.5" y="13" width="5" height="4" rx="2" fill={shade(s.hair, 1.28)} />
          <circle cx="50" cy="27" r="2.4" fill={accent} />
        </g>
      );
    case "cap":
      return (
        <g>
          <path d="M30,45 C30,25 70,25 70,45 L70,41 C70,23 30,23 30,41 Z" fill={shade(s.hair, 1.25)} />
          <path d="M64,38 Q84,34 86,44 Q66,48 64,38 Z" fill={shade(s.hair, 1.35)} />
          <circle cx="50" cy="30" r="2.6" fill={accent} />
        </g>
      );
    case "bow":
      return (
        <g>
          <path d="M77,52 L88,46 L85,57 Z" fill={s.hair} />
          <path d="M77,52 L66,46 L69,57 Z" fill={shade(s.hair, 1.25)} />
          <circle cx="77" cy="52" r="3" fill={accent} />
        </g>
      );
    default:
      return null;
  }
}

export const AgentAvatar: React.FC<AgentAvatarProps> = memo(function AgentAvatar({
  id,
  accent = "#38bdf8",
  size = 34,
  shape = "square",
  badge = null,
  className,
  style,
  title,
}) {
  const spec = getAvatarSpec(id, accent);
  const radius = shape === "round" ? "50%" : "10px";
  const bg = `linear-gradient(150deg, #141926 0%, ${mix(accent, "#141926", 0.72)} 130%)`;

  return (
    <div
      className={className}
      title={title}
      aria-label={title}
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        background: bg,
        border: `1px solid ${mix(accent, "#223043", 0.55)}`,
        position: "relative",
        overflow: "hidden",
        flexShrink: 0,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.12)",
        ...style,
      }}
    >
      <svg
        viewBox="0 0 100 100"
        style={{
          position: "absolute",
          left: "50%",
          top: "54%",
          transform: "translate(-50%, -52%)",
          width: "148%",
          height: "148%",
        }}
      >
        {hairCap(spec)}
        <ellipse cx="29" cy="58" rx="4" ry="4.5" fill={spec.skin} />
        <ellipse cx="71" cy="58" rx="4" ry="4.5" fill={spec.skin} />
        <rect x="31" y="40" width="38" height="40" rx="15" fill={spec.skin} />
        <path d="M49,58 C50,61 50,62 47.5,64" fill="none" stroke={shade(spec.skin, 0.78)} strokeWidth="1.7" strokeLinecap="round" />
        {spec.gender === "f" && (
          <g>
            <ellipse cx="33.5" cy="66" rx="3.6" ry="2.2" fill="rgba(235,120,140,0.22)" />
            <ellipse cx="66.5" cy="66" rx="3.6" ry="2.2" fill="rgba(235,120,140,0.22)" />
          </g>
        )}
        <g fill="#191210">
          <ellipse cx="38" cy="57" rx="3.1" ry="4" />
          <ellipse cx="62" cy="57" rx="3.1" ry="4" />
          <circle cx="36.8" cy="55.6" r="1.05" fill="#fff" />
          <circle cx="60.8" cy="55.6" r="1.05" fill="#fff" />
        </g>
        <g fill={shade(spec.hair, 0.85)}>
          <rect x="33.5" y="50" width="8.5" height="2.3" rx="1.1" />
          <rect x="58" y="50" width="8.5" height="2.3" rx="1.1" />
        </g>
        {glasses(spec)}
        {spec.beard !== "none" && (
          spec.beard === "stubble" ? (
            <rect x="33" y="69" width="34" height="7.5" rx="3.7" fill={shade(spec.skin, 0.8)} opacity="0.75" />
          ) : (
            <path d="M33,67 C33,83 67,83 67,67 L64,67 C60,75 40,75 36,67 Z" fill={shade(spec.hair, 0.92)} opacity="0.92" />
          )
        )}
        <path d="M43,70 Q50,76 57,70" fill="none" stroke={shade(spec.skin, 0.52)} strokeWidth="2.1" strokeLinecap="round" />
        {accessories(spec, accent)}
      </svg>

      {badge && (
        <span
          style={{
            position: "absolute",
            right: -1,
            bottom: -1,
            minWidth: "38%",
            height: "38%",
            borderRadius: "7px 7px 0 0",
            background: "rgba(8,10,16,0.82)",
            border: `1px solid ${mix(accent, "#ffffff", 0.25)}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "calc(100% * 0.52)",
            lineHeight: 1,
            padding: "0 1px",
          }}
        >
          {badge}
        </span>
      )}
    </div>
  );
});