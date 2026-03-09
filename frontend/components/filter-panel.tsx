"use client";

import { Button } from "@/components/ui/button";

interface FilterPanelProps {
  filters: Record<string, string>;
  onFilterChange: (filters: Record<string, string>) => void;
}

const categories = ["policy", "report", "deck", "memo"];
const docTypes = ["pdf", "docx", "pptx"];

export function FilterPanel({ filters, onFilterChange }: FilterPanelProps) {
  const toggleFilter = (key: string, value: string) => {
    const updated = { ...filters };
    if (updated[key] === value) {
      delete updated[key];
    } else {
      updated[key] = value;
    }
    onFilterChange(updated);
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold mb-2">Category</h3>
        <div className="flex flex-col gap-1">
          {categories.map((cat) => (
            <Button
              key={cat}
              variant={filters.category === cat ? "default" : "ghost"}
              size="sm"
              className="justify-start capitalize"
              onClick={() => toggleFilter("category", cat)}
            >
              {cat}
            </Button>
          ))}
        </div>
      </div>
      <div>
        <h3 className="text-sm font-semibold mb-2">File Type</h3>
        <div className="flex flex-col gap-1">
          {docTypes.map((dt) => (
            <Button
              key={dt}
              variant={filters.doc_type === dt ? "default" : "ghost"}
              size="sm"
              className="justify-start uppercase"
              onClick={() => toggleFilter("doc_type", dt)}
            >
              {dt}
            </Button>
          ))}
        </div>
      </div>
      {Object.keys(filters).length > 0 && (
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={() => onFilterChange({})}
        >
          Clear Filters
        </Button>
      )}
    </div>
  );
}
