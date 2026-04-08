import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useMemoryStore } from '../stores/memoryStore';
import { usePatientStore } from '../stores/patientStore';
import { MemoryStarMap } from '../components/memory/MemoryStarMap';
import { MemoryDetail } from '../components/memory/MemoryDetail';
import { MemorySearch } from '../components/memory/MemorySearch';
import { MemoryCreate } from '../components/memory/MemoryCreate';
import { MemoryEmpty } from '../components/memory/MemoryEmpty';
import { ErrorToast } from '../components/common/ErrorToast';

export function MemoryPalacePage() {
  const patientId = usePatientStore((s) => s.selectedPatientId);
  const {
    memories,
    selectedMemory,
    searchResults,
    loading,
    error,
    degraded,
    fetchMemoryTree,
    fetchStats,
    searchMemories,
    selectMemory,
    createMemory,
    deleteMemory,
  } = useMemoryStore();

  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    if (patientId) {
      fetchMemoryTree();
      fetchStats();
    }
  }, [patientId, fetchMemoryTree, fetchStats]);

  const handleSearch = useCallback(
    (query: string) => {
      if (patientId) searchMemories(query);
    },
    [patientId, searchMemories],
  );

  const handleDelete = useCallback(
    async (path: string) => {
      await deleteMemory(path);
    },
    [deleteMemory],
  );

  // Degraded state
  if (degraded && !loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex h-full flex-col items-center justify-center gap-4"
      >
        <div className="text-5xl">🌑</div>
        <h2 className="text-lg font-semibold text-gray-400">记忆服务暂时不可用</h2>
        <p className="text-sm text-gray-500 max-w-md text-center">
          Memory Palace 服务暂时无法连接。请稍后再试，或联系管理员检查服务状态。
        </p>
        <button
          onClick={() => {
            if (patientId) fetchMemoryTree();
          }}
          className="btn-primary text-sm"
        >
          重试
        </button>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex h-full"
    >
      {/* Left: Star map + search */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Search bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5">
          <div className="flex-1">
            <MemorySearch onSearch={handleSearch} />
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary text-sm whitespace-nowrap"
          >
            + 新建
          </button>
        </div>

        {/* Canvas area */}
        <div className="flex-1 relative">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                className="h-8 w-8 rounded-full border-2 border-primary-500 border-t-transparent"
              />
            </div>
          ) : memories.length === 0 ? (
            <MemoryEmpty onCreateClick={() => setShowCreate(true)} />
          ) : (
            <MemoryStarMap
              memories={memories}
              searchResults={searchResults}
              selectedMemory={selectedMemory}
              onSelectMemory={selectMemory}
            />
          )}
        </div>
      </div>

      {/* Right: Detail panel */}
      {selectedMemory && (
        <div className="w-80 border-l border-white/5 overflow-y-auto p-4">
          <MemoryDetail
            memory={selectedMemory}
            onClose={() => selectMemory(null)}
            onEdit={() => {
              // TODO: edit modal
            }}
            onDelete={handleDelete}
          />
        </div>
      )}

      {/* Create modal */}
      {patientId && (
        <MemoryCreate
          patientId={patientId}
          open={showCreate}
          onClose={() => setShowCreate(false)}
          onCreate={createMemory}
        />
      )}

      <ErrorToast message={error} />
    </motion.div>
  );
}
