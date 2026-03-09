"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import { SearchBar } from "@/components/search-bar";
import { ResultCard } from "@/components/result-card";
import { FilterPanel } from "@/components/filter-panel";
import { searchDocuments, type SearchResponse } from "@/lib/api";

function SearchContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!query) return;
    setLoading(true);
    setError(null);
    searchDocuments(query, Object.keys(filters).length > 0 ? filters : undefined)
      .then(setResponse)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [query, filters]);

  return (
    <div className="min-h-screen">
      <header className="border-b px-6 py-4">
        <div className="flex items-center gap-4 max-w-5xl mx-auto">
          <a href="/" className="text-xl font-bold whitespace-nowrap">
            Deloitte Search
          </a>
          <SearchBar defaultValue={query} />
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-6 flex gap-6">
        <aside className="w-48 shrink-0 hidden md:block">
          <FilterPanel filters={filters} onFilterChange={setFilters} />
        </aside>

        <main className="flex-1">
          {loading && <p className="text-muted-foreground">Searching...</p>}
          {error && <p className="text-destructive">{error}</p>}
          {response && !loading && (
            <>
              <p className="text-sm text-muted-foreground mb-4">
                {response.total} results in {response.latency_ms}ms
              </p>
              {response.results.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-lg font-medium mb-2">No results found</p>
                  <p className="text-sm text-muted-foreground">
                    Try different keywords or remove filters
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {response.results.map((result) => (
                    <ResultCard key={result.document_id} result={result} />
                  ))}
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <SearchContent />
    </Suspense>
  );
}
