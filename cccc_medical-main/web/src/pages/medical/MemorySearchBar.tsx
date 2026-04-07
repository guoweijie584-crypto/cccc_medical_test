import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { medicalApiUrl } from "./api";

export interface MemorySearchResult {
  uri: string;
  path: string;
  content: Record<string, unknown> | null;
  category: string;
  score: number;
  snippet: string;
}

interface MemorySearchBarProps {
  patientId?: string;
  /** Controlled value — if provided, the parent owns the query string. */
  value?: string;
  /** Controlled onChange — called with the raw query string. */
  onChange?: (query: string) => void;
  onSelect?: (result: MemorySearchResult) => void;
  /** Callback with all results so parent can highlight matching nodes. */
  onResults?: (results: MemorySearchResult[]) => void;
  onClear?: () => void;
}

export function MemorySearchBar({ patientId, value, onChange, onSelect, onResults, onClear }: MemorySearchBarProps) {
  const [internalQuery, setInternalQuery] = useState("");
  const query = value !== undefined ? value : internalQuery;
  const setQuery = (q: string) => {
    if (onChange) onChange(q);
    else setInternalQuery(q);
  };
  const [results, setResults] = useState<MemorySearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const containerRef = useRef<HTMLDivElement>(null);

  const doSearch = useCallback(
    async (q: string) => {
      if (!q.trim()) {
        setResults([]);
        onResults?.([]);
        return;
      }
      setLoading(true);
      try {
        const params = new URLSearchParams({ q: q.trim(), max_results: "20" });
        if (patientId) params.set("patient_id", patientId);
        const resp = await fetch(medicalApiUrl(`/api/memory/search?${params}`));
        if (!resp.ok) throw new Error("search failed");
        const data = await resp.json();
        const items: MemorySearchResult[] = Array.isArray(data.results) ? data.results : [];
        setResults(items);
        onResults?.(items);
        setOpen(items.length > 0);
      } catch {
        setResults([]);
        onResults?.([]);
      } finally {
        setLoading(false);
      }
    },
    [patientId, onResults],
  );

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setResults([]);
      onResults?.([]);
      setOpen(false);
      return;
    }
    debounceRef.current = setTimeout(() => doSearch(query), 350);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, doSearch, onResults]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleClear = () => {
    setQuery("");
    setResults([]);
    setOpen(false);
    onResults?.([]);
    onClear?.();
  };

  const categoryColor = (cat: string) => {
    const map: Record<string, string> = {
      profile: "text-amber-300",
      glucose: "text-cyan-300",
      medications: "text-blue-300",
      diet: "text-emerald-300",
      alerts: "text-red-300",
      consultations: "text-violet-300",
    };
    return map[cat] ?? "text-slate-400";
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      {/* Input */}
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder="Search memories..."
          className="w-full rounded-lg bg-slate-800/60 border border-slate-600/40 text-sm text-slate-200 pl-9 pr-8 py-2 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50 transition-colors"
        />
        {/* Search icon */}
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        {/* Clear / spinner */}
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-sm"
            aria-label="Clear search"
          >
            {loading ? (
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
              </svg>
            ) : (
              <span>&times;</span>
            )}
          </button>
        )}
      </div>

      {/* Dropdown results */}
      <AnimatePresence>
        {open && results.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute z-50 mt-1 w-full max-h-72 overflow-auto rounded-lg border border-slate-600/40 bg-slate-800/95 backdrop-blur-md shadow-xl"
          >
            {results.map((r, idx) => {
              const text =
                typeof r.content === "object" && r.content
                  ? (r.content.content as string) || r.snippet || JSON.stringify(r.content)
                  : r.snippet || String(r.content ?? "");
              return (
                <button
                  key={r.uri || idx}
                  onClick={() => {
                    onSelect?.(r);
                    setOpen(false);
                  }}
                  className="w-full text-left px-4 py-2.5 hover:bg-slate-700/50 transition-colors border-b border-slate-700/30 last:border-0"
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold uppercase ${categoryColor(r.category)}`}>{r.category}</span>
                    {r.score > 0 && <span className="text-[10px] text-slate-500">score: {r.score.toFixed(2)}</span>}
                  </div>
                  <p className="text-sm text-slate-300 mt-0.5 line-clamp-2">{text}</p>
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default MemorySearchBar;
