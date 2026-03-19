import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText, User, Calendar } from "lucide-react";
import type { SearchResult } from "@/lib/api";

const categoryColors: Record<string, string> = {
  policy: "bg-blue-100 text-blue-800",
  report: "bg-green-100 text-green-800",
  deck: "bg-purple-100 text-purple-800",
  memo: "bg-orange-100 text-orange-800",
};

export function ResultCard({ result }: { result: SearchResult }) {
  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base leading-snug">{result.title}</CardTitle>
            {result.version && result.version > 1 && (
              <Badge variant="secondary" className="text-xs shrink-0">
                v{result.version}
              </Badge>
            )}
          </div>
          <Badge variant="outline" className={categoryColors[result.category] || ""}>
            {result.category}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-3 mb-3">
          {result.snippet}
        </p>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {result.author && (
            <span className="flex items-center gap-1">
              <User className="h-3 w-3" /> {result.author}
            </span>
          )}
          {result.created_date && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {new Date(result.created_date).toLocaleDateString()}
            </span>
          )}
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3" /> {result.doc_type.toUpperCase()}
          </span>
          {result.page_count && (
            <span>{result.page_count} pages</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
