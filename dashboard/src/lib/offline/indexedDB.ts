const DB_NAME = "NEMO_OFFLINE_DB";
const DB_VERSION = 1;

export type OfflineStoreName =
  | "conversations"
  | "messages"
  | "memories"
  | "tasks"
  | "events"
  | "ai_keys"
  | "ai_settings"
  | "profile"
  | "sync_queue"
  | "activity_logs"
  | "web_searches";

interface SyncQueueItem {
  id: string;
  operation: "create" | "update" | "delete";
  store: OfflineStoreName;
  data: any;
  timestamp: number;
  retries: number;
  synced: boolean;
}

type StoreName = string; // Allow prefixed names from LocalRepository

export class IndexedDBManager {
  private db: IDBDatabase | null = null;
  private initPromise: Promise<IDBDatabase> | null = null;

  async init(): Promise<IDBDatabase> {
    if (this.db) return this.db;
    if (this.initPromise) return this.initPromise;

    this.initPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const database = (event.target as IDBOpenDBRequest).result;
        const stores: OfflineStoreName[] = [
          "conversations",
          "messages",
          "memories",
          "tasks",
          "events",
          "ai_keys",
          "ai_settings",
          "profile",
          "sync_queue",
          "activity_logs",
          "web_searches",
        ];

        for (const storeName of stores) {
          if (!database.objectStoreNames.contains(storeName)) {
            const store = database.createObjectStore(storeName, { keyPath: "id" });
            if (storeName === "messages") {
              store.createIndex("conversation_id", "conversation_id", { unique: false });
            }
            if (storeName === "sync_queue") {
              store.createIndex("timestamp", "timestamp", { unique: false });
              store.createIndex("synced", "synced", { unique: false });
            }
          }
        }
      };
    });

    return this.initPromise;
  }

  async close(): Promise<void> {
    if (this.db) {
      this.db.close();
      this.db = null;
      this.initPromise = null;
    }
  }

  private async getStore(storeName: StoreName, mode: IDBTransactionMode = "readonly"): Promise<IDBObjectStore> {
    const db = await this.init();
    return db.transaction(storeName, mode).objectStore(storeName);
  }

  async get<T>(storeName: StoreName, id: string): Promise<T | undefined> {
    const store = await this.getStore(storeName);
    return new Promise((resolve, reject) => {
      const request = store.get(id);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getAll<T>(storeName: StoreName): Promise<T[]> {
    const store = await this.getStore(storeName);
    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getAllByIndex<T>(
    storeName: StoreName,
    indexName: string,
    value: any
  ): Promise<T[]> {
    const store = await this.getStore(storeName);
    const index = store.index(indexName);
    return new Promise((resolve, reject) => {
      const request = index.getAll(value);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async put<T extends { id: string }>(storeName: StoreName, data: T): Promise<void> {
    const store = await this.getStore(storeName, "readwrite");
    return new Promise((resolve, reject) => {
      const request = store.put(data);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async putMany<T extends { id: string }>(storeName: StoreName, items: T[]): Promise<void> {
    const store = await this.getStore(storeName, "readwrite");
    return new Promise((resolve, reject) => {
      let completed = 0;
      const total = items.length;
      if (total === 0) return resolve();

      for (const item of items) {
        const request = store.put(item);
        request.onsuccess = () => {
          completed++;
          if (completed === total) resolve();
        };
        request.onerror = () => reject(request.error);
      }
    });
  }

  async delete(storeName: StoreName, id: string): Promise<void> {
    const store = await this.getStore(storeName, "readwrite");
    return new Promise((resolve, reject) => {
      const request = store.delete(id);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async clear(storeName: StoreName): Promise<void> {
    const store = await this.getStore(storeName, "readwrite");
    return new Promise((resolve, reject) => {
      const request = store.clear();
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  // Sync Queue Operations
  async enqueueSync(item: Omit<SyncQueueItem, "id" | "timestamp" | "retries" | "synced">): Promise<string> {
    const id = `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const syncItem: SyncQueueItem = {
      ...item,
      id,
      timestamp: Date.now(),
      retries: 0,
      synced: false,
    };
    await this.put("sync_queue", syncItem);
    return id;
  }

  async getPendingSync(limit = 50): Promise<SyncQueueItem[]> {
    const store = await this.getStore("sync_queue");
    const index = store.index("synced");
    return new Promise((resolve, reject) => {
      const request = index.getAll(IDBKeyRange.only(false));
      request.onsuccess = () => {
        const items = request.result as SyncQueueItem[];
        items.sort((a, b) => a.timestamp - b.timestamp);
        resolve(items.slice(0, limit));
      };
      request.onerror = () => reject(request.error);
    });
  }

  async markSynced(id: string): Promise<void> {
    const item = await this.get<SyncQueueItem>("sync_queue", id);
    if (item) {
      item.synced = true;
      await this.put("sync_queue", item);
    }
  }

  async incrementRetry(id: string): Promise<void> {
    const item = await this.get<SyncQueueItem>("sync_queue", id);
    if (item) {
      item.retries++;
      await this.put("sync_queue", item);
    }
  }

  async removeSynced(olderThanMs = 60 * 60 * 24 * 1000): Promise<number> {
    const store = await this.getStore("sync_queue", "readwrite");
    const index = store.index("synced");
    const cutoff = Date.now() - olderThanMs;

    return new Promise((resolve, reject) => {
      const request = index.openCursor(IDBKeyRange.only(true));
      let count = 0;
      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          if (cursor.value.timestamp < cutoff) {
            cursor.delete();
            count++;
          }
          cursor.continue();
        } else {
          resolve(count);
        }
      };
      request.onerror = () => reject(request.error);
    });
  }
}

export const indexedDBManager = new IndexedDBManager();