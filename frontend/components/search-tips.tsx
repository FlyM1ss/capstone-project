"use client";

import { useState } from "react";
import { Info, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SearchTips() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        onClick={() => setOpen(!open)}
        aria-label="Search tips"
      >
        {open ? <X className="h-4 w-4" /> : <Info className="h-4 w-4" />}
      </Button>

      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 rounded-lg border bg-card p-4 shadow-lg">
          <h4 className="mb-2 font-semibold text-sm">Search Tips</h4>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            <li>Use natural language: <span className="text-foreground">&quot;Q4 healthcare consulting deck&quot;</span></li>
            <li>Search by topic: <span className="text-foreground">&quot;travel reimbursement policy&quot;</span></li>
            <li>Find by type: <span className="text-foreground">&quot;annual financial report with charts&quot;</span></li>
            <li>Search by author: <span className="text-foreground">&quot;presentation by marketing team&quot;</span></li>
          </ul>
        </div>
      )}
    </div>
  );
}
