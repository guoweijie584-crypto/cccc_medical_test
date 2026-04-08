import { useState, useEffect, useRef } from 'react';

interface MemorySearchProps {
  onSearch: (query: string) => void;
}

export function MemorySearch({ onSearch }: MemorySearchProps) {
  const [query, setQuery] = useState('');
  const debounceRef = useRef<number | null>(null);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = window.setTimeout(() => {
      onSearch(query);
    }, 350);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, onSearch]);

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="搜索记忆..."
        className="w-full rounded-btn bg-surface-800 border border-white/10 pl-9 pr-4 py-2 text-sm
                   text-gray-200 placeholder-gray-500
                   focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500/30"
      />
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">🔍</span>
      {query && (
        <button
          onClick={() => setQuery('')}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 text-sm"
        >
          ✕
        </button>
      )}
    </div>
  );
}
