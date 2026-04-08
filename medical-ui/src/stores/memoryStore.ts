import { create } from 'zustand';
import { api, ApiError } from '../api/client';
import { usePatientStore } from './patientStore';

export interface MemoryNode {
  path: string;
  content: string;
  category: string;
  priority: number;
  vitality: number;
  disclosure?: string;
  created_at?: string;
  updated_at?: string;
  children?: MemoryNode[];
}

export interface MemoryStats {
  total: number;
  by_category: Record<string, number>;
}

interface MemoryStore {
  memories: MemoryNode[];
  stats: MemoryStats | null;
  selectedMemory: MemoryNode | null;
  searchResults: MemoryNode[];
  loading: boolean;
  error: string | null;
  degraded: boolean;

  fetchMemoryTree: () => Promise<void>;
  fetchStats: () => Promise<void>;
  searchMemories: (query: string) => Promise<void>;
  selectMemory: (memory: MemoryNode | null) => void;
  createMemory: (data: {
    path: string;
    content: string;
    priority?: number;
    disclosure?: string;
  }) => Promise<boolean>;
  updateMemory: (
    path: string,
    data: { content?: string; priority?: number; disclosure?: string },
  ) => Promise<boolean>;
  deleteMemory: (path: string) => Promise<boolean>;
}

function flattenTree(nodes: MemoryNode[]): MemoryNode[] {
  const result: MemoryNode[] = [];
  for (const node of nodes) {
    result.push(node);
    if (node.children) {
      result.push(...flattenTree(node.children));
    }
  }
  return result;
}

export const useMemoryStore = create<MemoryStore>((set, get) => ({
  memories: [],
  stats: null,
  selectedMemory: null,
  searchResults: [],
  loading: false,
  error: null,
  degraded: false,

  fetchMemoryTree: async () => {
    const patientId = usePatientStore.getState().selectedPatientId;
    if (!patientId) return;

    set({ loading: true, error: null, degraded: false });
    try {
      const data = await api.get<{ tree: MemoryNode | MemoryNode[]; memoryStatus?: string }>(
        `/api/memory/tree/${patientId}`,
      );
      // Backend returns { tree: { path, children } } (single object) or { tree: [...] } (array)
      let treeNodes: MemoryNode[];
      if (Array.isArray(data.tree)) {
        treeNodes = data.tree;
      } else if (data.tree && typeof data.tree === 'object') {
        // Single root node — extract children
        treeNodes = (data.tree as MemoryNode).children || [data.tree as MemoryNode];
      } else {
        treeNodes = [];
      }
      set({
        memories: flattenTree(treeNodes),
        loading: false,
        degraded: data.memoryStatus === 'degraded',
      });
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : '记忆加载失败';
      set({ loading: false, error: msg, degraded: true });
    }
  },

  fetchStats: async () => {
    const patientId = usePatientStore.getState().selectedPatientId;
    if (!patientId) return;
    try {
      const data = await api.get<MemoryStats>(`/api/memory/stats?patient_id=${patientId}`);
      set({ stats: data });
    } catch {
      // non-critical
    }
  },

  searchMemories: async (query: string) => {
    const patientId = usePatientStore.getState().selectedPatientId;
    if (!patientId || !query.trim()) {
      set({ searchResults: [] });
      return;
    }
    try {
      const data = await api.get<{ results: MemoryNode[] }>(
        `/api/memory/search?q=${encodeURIComponent(query)}&patient_id=${patientId}&mode=hybrid`,
      );
      set({ searchResults: data.results || [] });
    } catch {
      set({ searchResults: [] });
    }
  },

  selectMemory: (memory) => set({ selectedMemory: memory }),

  createMemory: async (data) => {
    try {
      await api.post('/api/memory/create', data);
      await get().fetchMemoryTree();
      await get().fetchStats();
      return true;
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : '创建失败';
      set({ error: msg });
      return false;
    }
  },

  updateMemory: async (path, data) => {
    try {
      await api.put(`/api/memory/${encodeURIComponent(path)}`, data);
      await get().fetchMemoryTree();
      return true;
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : '更新失败';
      set({ error: msg });
      return false;
    }
  },

  deleteMemory: async (path) => {
    try {
      await api.delete(`/api/memory/${encodeURIComponent(path)}`);
      set({ selectedMemory: null });
      await get().fetchMemoryTree();
      await get().fetchStats();
      return true;
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : '删除失败';
      set({ error: msg });
      return false;
    }
  },
}));
