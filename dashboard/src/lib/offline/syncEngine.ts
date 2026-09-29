import { nemoApi } from "@/api/nemo";
import { useNetworkStatus } from "@/hooks/useNetworkStatus";
import { useCallback, useEffect, useState } from "react";
import { useOffline } from "@/lib/offline";

interface SyncResult {
  success: number;
  failed: number;
  conflicts: number;
  errors: string[];
}

type NetworkStatusChecker = () => boolean;

class SyncEngine {
  private isSyncing = false;
  private syncInterval: ReturnType<typeof setInterval> | null = null;
  private listeners: Set<(status: "idle" | "syncing" | "error" | "complete", result?: SyncResult) => void> = new Set();
  private isOnlineChecker: NetworkStatusChecker = () => true;
  private lastSyncVersion = 0;
  private syncApi: {
    getPendingSync: (limit?: number) => Promise<any[]>;
    markSynced: (id: string) => Promise<void>;
    incrementRetry: (id: string) => Promise<void>;
    cleanupSynced: () => Promise<number>;
  } | null = null;

  setOnlineChecker(checker: NetworkStatusChecker): void {
    this.isOnlineChecker = checker;
  }

  setSyncApi(api: {
    getPendingSync: (limit?: number) => Promise<any[]>;
    markSynced: (id: string) => Promise<void>;
    incrementRetry: (id: string) => Promise<void>;
    cleanupSynced: () => Promise<number>;
  }): void {
    this.syncApi = api;
  }

  async startAutoSync(intervalMs = 30000): Promise<void> {
    if (this.syncInterval) return;

    const runSync = async () => {
      if (!this.isOnlineChecker()) return;
      await this.sync();
    };

    this.syncInterval = setInterval(runSync, intervalMs);
    runSync();
  }

  stopAutoSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  subscribe(listener: (status: "idle" | "syncing" | "error" | "complete", result?: SyncResult) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(status: "idle" | "syncing" | "error" | "complete", result?: SyncResult): void {
    for (const listener of this.listeners) {
      try {
        listener(status, result);
      } catch {}
    }
  }

  async sync(): Promise<SyncResult> {
    if (this.isSyncing) return { success: 0, failed: 0, conflicts: 0, errors: ["Already syncing"] };
    if (!this.isOnlineChecker()) return { success: 0, failed: 0, conflicts: 0, errors: ["Offline"] };
    if (!this.syncApi) return { success: 0, failed: 0, conflicts: 0, errors: ["Sync API not initialized"] };

    this.isSyncing = true;
    this.notify("syncing");

    const { getPendingSync, markSynced, incrementRetry, cleanupSynced } = this.syncApi;
    const pending = await getPendingSync(100);

    const result: SyncResult = { success: 0, failed: 0, conflicts: 0, errors: [] };

    if (pending.length > 0) {
      try {
        const pushResult = await nemoApi.syncPush(pending, this.lastSyncVersion);
        
      // O servidor devolve os resultados na MESMA ordem das operações, mas
        // casa por `client_id`: indexar por posição marcava a operação errada
        // como sincronizada quando o servidor reordenava ou omitia alguma.
        const resultsByClient = new Map(
          (pushResult.results ?? []).map((r) => [r.client_id, r] as const),
        );

        for (let i = 0; i < pending.length; i++) {
          const item = pending[i];
          const pushItemResult = resultsByClient.get(item.client_id) ?? pushResult.results?.[i];

          if (pushItemResult?.status === "ok") {
            await markSynced(item.id);
            result.success++;
          } else if (pushItemResult?.status === "conflict") {
            result.conflicts++;
            result.errors.push(`${item.operation} ${item.store}: Conflict detected`);
          } else {
            await incrementRetry(item.id);
            result.failed++;
            result.errors.push(`${item.operation} ${item.store}: ${pushItemResult?.error || "Unknown error"}`);
          }
        }
        
        if (pushResult.server_version) {
          this.lastSyncVersion = pushResult.server_version;
        }
      } catch (error) {
        result.failed += pending.length;
        result.errors.push(`Push failed: ${error instanceof Error ? error.message : String(error)}`);
      }
    }

    try {
      const pullResult = await nemoApi.syncPull(this.lastSyncVersion);

      if (pullResult.changes) {
        for (const [store, items] of Object.entries(pullResult.changes)) {
          for (const item of items) {
            try {
              await this.applyServerChange(store, item);
            } catch (error) {
              // Antes o `catch {}` vazio em applyServerChange escondia falha de
              // escrita: o cliente recebia "sincronizado" com o dado perdido.
              result.failed++;
              result.errors.push(
                `apply ${store} falhou: ${error instanceof Error ? error.message : String(error)}`,
              );
            }
          }
        }
      }

      if (pullResult.unreadable_stores?.length) {
        // O servidor não conseguiu ler estas lojas. O cursor NÃO pode avançar:
        // doingo isso, a próxima sincronização pularia esses registros para
        // sempre. Fica no valor anterior e a próxima tentativa reprocessa.
        result.failed += pullResult.unreadable_stores.length;
        result.errors.push(`Lojas ilegíveis no servidor: ${pullResult.unreadable_stores.join(", ")}`);
      } else if (pullResult.server_version) {
        this.lastSyncVersion = pullResult.server_version;
      }
    } catch (error) {
      result.errors.push(`Pull failed: ${error instanceof Error ? error.message : String(error)}`);
    }

    await cleanupSynced();

    this.isSyncing = false;
    this.notify(result.failed > 0 || result.conflicts > 0 ? "error" : "complete", result);
    return result;
  }

  private async applyServerChange(store: string, item: any): Promise<void> {
    const { getRepository } = await import("./repository");
    const repo = getRepository();

    switch (store) {
      case "conversations":
        await repo.updateConversation(item.id, item);
        break;
      case "tasks":
        await repo.saveTask(item);
        break;
      case "events":
        await repo.saveEvent(item);
        break;
      case "profile":
        await repo.saveProfile(item);
        break;
      case "ai_settings":
        await repo.saveAiSettings(item);
        break;
      case "memories":
        // Era um caso vazio: a memória alterada em outro dispositivo nunca
        // era gravada localmente. `saveMemory` recria com novo id, então a
        // remoção do id antigo é o que mantém a lista sem duplicatas.
        await repo.deleteMemory(item.id);
        await repo.saveMemory(item.agent_id || "nemo", item.content || "", item.kind || "obs");
        break;
      default:
        // `ai_keys`, `messages`, `activity_logs` e `web_searches` não têm
        // escrita local: são somente leitura/registro no servidor.
        break;
    }
  }

  async resolveConflicts(conflicts: any[]): Promise<any[]> {
    const resolutions = conflicts.map(c => ({
      client_id: c.client_id,
      store: c.store,
      resolution: c.resolution || "local-wins",
      resolved_data: c.resolved_data,
    }));
    
    const result = await nemoApi.syncResolveConflicts(resolutions);
    return result.results;
  }

  getStatus(): "idle" | "syncing" {
    return this.isSyncing ? "syncing" : "idle";
  }
}

export const syncEngine = new SyncEngine();

export function useSyncEngine() {
  const { status: networkStatus } = useNetworkStatus();
  const offline = useOffline();
  const [syncStatus, setSyncStatus] = useState<"idle" | "syncing" | "error" | "complete">("idle");
  const [lastResult, setLastResult] = useState<SyncResult | null>(null);

  useEffect(() => {
    if (offline.sync) {
      syncEngine.setSyncApi(offline.sync);
    }

    const unsubscribe = syncEngine.subscribe((status, result) => {
      setSyncStatus(status);
      if (result) setLastResult(result);
    });

    if (networkStatus === "online") {
      syncEngine.startAutoSync();
    } else {
      syncEngine.stopAutoSync();
    }

    return () => {
      unsubscribe();
      syncEngine.stopAutoSync();
    };
  }, [networkStatus, offline.sync]);

  const manualSync = useCallback(async () => {
    const result = await syncEngine.sync();
    setLastResult(result);
    setSyncStatus(result.failed > 0 ? "error" : "complete");
    return result;
  }, []);

  return { syncStatus, lastResult, manualSync, isSyncing: syncEngine.getStatus() === "syncing" };
}