import { createContext, useContext, useEffect, useMemo, useState, useCallback, ReactNode } from "react";
import { createRepository, type DataRepository } from "./repository";
import { syncEngine } from "./syncEngine";
import { useNetworkStatus } from "@/hooks/useNetworkStatus";
import { indexedDBManager } from "./indexedDB";

interface OfflineContextValue {
  repository: DataRepository | null;
  isReady: boolean;
  networkStatus: ReturnType<typeof useNetworkStatus>;
  sync: {
    getPendingSync: (limit?: number) => Promise<any[]>;
    markSynced: (id: string) => Promise<void>;
    incrementRetry: (id: string) => Promise<void>;
    cleanupSynced: () => Promise<number>;
    startAutoSync: () => Promise<void>;
    stopAutoSync: () => void;
  };
  initialize: () => Promise<void>;
}

const OfflineContext = createContext<OfflineContextValue | null>(null);

export function OfflineProvider({ children }: { children: ReactNode }) {
  const [repository, setRepository] = useState<DataRepository | null>(null);
  const [isReady, setIsReady] = useState(false);
  const networkStatus = useNetworkStatus();

  const initialize = useCallback(async () => {
    try {
      await indexedDBManager.init();
      const repo = createRepository(() => networkStatus.status === "online");
      setRepository(repo);
      setIsReady(true);

      if (networkStatus.status === "online") {
        syncEngine.startAutoSync();
      }
    } catch (error) {
      console.error("Failed to initialize offline layer:", error);
      setIsReady(true);
    }
  }, [networkStatus.status]);

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (networkStatus.status === "online" && repository) {
      syncEngine.startAutoSync();
    } else {
      syncEngine.stopAutoSync();
    }
  }, [networkStatus.status, repository]);

  // Nunca lanca durante o render: no primeiro render `repository` ainda e null
  // (so e atribuido no efeito initialize). Lancar aqui desmontava a raiz inteira
  // do React e deixava a tela totalmente em branco. Alem disso, este objeto
  // antes era recriado a cada render; agora e memoizado.
  const sync = useMemo<OfflineContextValue["sync"]>(
    () => ({
      getPendingSync: async (limit?: number) => (repository ? repository.getPendingSync(limit) : []),
      markSynced: async (id: string) => {
        if (repository) await repository.markSynced(id);
      },
      incrementRetry: async (id: string) => {
        if (repository) await repository.incrementRetry(id);
      },
      cleanupSynced: async () => (repository ? repository.cleanupSynced() : 0),
      startAutoSync: async () => {
        await syncEngine.startAutoSync();
      },
      stopAutoSync: () => {
        syncEngine.stopAutoSync();
      },
    }),
    [repository]
  );

  const value = useMemo<OfflineContextValue>(
    () => ({ repository, isReady, networkStatus, sync, initialize }),
    [repository, isReady, networkStatus, sync, initialize]
  );

  return <OfflineContext.Provider value={value}>{children}</OfflineContext.Provider>;
}

export function useOffline() {
  const context = useContext(OfflineContext);
  if (!context) {
    throw new Error("useOffline must be used within an OfflineProvider");
  }
  return context;
}

export function useRepository(): DataRepository {
  const { repository, isReady } = useOffline();
  if (!repository || !isReady) {
    throw new Error("Repository not ready");
  }
  return repository;
}