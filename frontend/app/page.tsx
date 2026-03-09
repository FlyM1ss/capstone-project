import { SearchBar } from "@/components/search-bar";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight mb-2">
          Deloitte Search
        </h1>
        <p className="text-muted-foreground">
          Find internal resources using natural language
        </p>
      </div>
      <SearchBar />
      <div className="mt-6 flex gap-2 flex-wrap justify-center">
        {["Q4 consulting deck", "travel policy", "annual report 2025"].map((example) => (
          <a
            key={example}
            href={`/search?q=${encodeURIComponent(example)}`}
            className="rounded-full border px-3 py-1 text-sm text-muted-foreground hover:text-foreground hover:border-foreground transition-colors"
          >
            {example}
          </a>
        ))}
      </div>
    </main>
  );
}
