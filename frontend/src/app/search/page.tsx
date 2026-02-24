"use client";

import { useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import { search, SearchResult } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  // Optional filters
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("");
  const [client, setClient] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setSearched(false);
    try {
      const res = await search(query, 10, {
        source: source || undefined,
        category: category || undefined,
        client: client || undefined,
      });
      setResults(res.results);
      setSearched(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthGuard>
      <div className="max-w-2xl">
        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">Search</h1>
          <p className="text-sm text-gray-500 mt-1">
            Ask anything across your documents
          </p>
        </div>

        {/* Search form */}
        <form onSubmit={handleSearch} className="flex flex-col gap-3 mb-6">
          <div className="flex gap-2">
            <input
              className="input flex-1"
              placeholder="e.g. backpropagation regularization techniques"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" className="btn-primary px-5" disabled={loading}>
              {loading ? "..." : "Search"}
            </button>
          </div>

          {/* Filters toggle */}
          <button
            type="button"
            className="text-xs text-gray-400 hover:text-gray-600 self-start transition-colors"
            onClick={() => setShowFilters((v) => !v)}
          >
            {showFilters ? "▲ Hide filters" : "▼ Filter by source / category / client"}
          </button>

          {showFilters && (
            <div className="flex gap-2 flex-wrap">
              <input
                className="input w-36"
                placeholder="Source"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              />
              <input
                className="input w-36"
                placeholder="Category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
              <input
                className="input w-36"
                placeholder="Client"
                value={client}
                onChange={(e) => setClient(e.target.value)}
              />
            </div>
          )}
        </form>

        {/* Error */}
        {error && (
          <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg mb-4">
            {error}
          </p>
        )}

        {/* Results */}
        {searched && results.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-12">
            No results found. Try a different query.
          </p>
        )}

        <div className="flex flex-col gap-3">
          {results.map((r, i) => (
            <div key={r.qdrant_id} className="card p-5 hover:shadow-md transition-shadow">
              {/* Meta row */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                    {r.filename}
                  </span>
                  {r.source && (
                    <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                      {r.source}
                    </span>
                  )}
                  {r.category && (
                    <span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded">
                      {r.category}
                    </span>
                  )}
                </div>
                <span className="text-xs text-gray-300 shrink-0">
                  #{i + 1} · score {r.score.toFixed(4)}
                </span>
              </div>

              {/* Content */}
              <p className="text-sm text-gray-700 leading-relaxed line-clamp-4">
                {r.content}
              </p>
            </div>
          ))}
        </div>
      </div>
    </AuthGuard>
  );
}