import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
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

  const syncApi = useCallback(() => {
    if (!repository) throw new Error("Repository not ready");
    return {
      getPendingSync: (limit?: number) => repository.getPendingSync(limit),
      markSynced: (id: string) => repository.markSynced(id),
      incrementRetry: (id: string) => repository.incrementRetry(id),
      cleanupSynced: () => repository.cleanupSynced(),
      startAutoSync: () => syncEngine.startAutoSync(),
      stopAutoSync: () => syncEngine.stopAutoSync(),
    };
  }, [repository]);

  return (
    <OfflineContext.Provider value={{ repository, isReady, networkStatus, sync: syncApi(), initialize }}>
      {children}
    </OfflineContext.Provider>
  );
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