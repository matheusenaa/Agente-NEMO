import { useNetworkStatus } from "@/hooks/useNetworkStatus";

export function NetworkStatusIndicator() {
  const { status, lastOnline, lastOffline } = useNetworkStatus();

  const statusConfig = {
    online: { icon: "🟢", label: "Online", tone: "success" as const },
    offline: { icon: "🟠", label: "Offline — dados salvos localmente", tone: "warn" as const },
    reconnecting: { icon: "🔄", label: "Reconectando...", tone: "info" as const },
    syncing: { icon: "🔄", label: "Sincronizando...", tone: "info" as const },
  };

  const config = statusConfig[status];

  return (
    <div
      className="network-status-indicator"
      data-status={status}
      title={`Status: ${config.label}${lastOnline ? ` • Última conexão: ${new Date(lastOnline).toLocaleTimeString()}` : ""}${lastOffline ? ` • Ficou offline: ${new Date(lastOffline).toLocaleTimeString()}` : ""}`}
    >
      <span className="network-dot" />
      <span className="network-icon">{config.icon}</span>
      <span className="network-label">{config.label}</span>
    </div>
  );
}