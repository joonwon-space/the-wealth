"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  error: Error;
  reset: () => void;
}

export default function DashboardError({ error, reset }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <AlertTriangle className="mb-3 h-10 w-10 text-destructive/60" />
      <h2 className="text-lg font-semibold">오류가 발생했습니다</h2>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{error.message}</p>
      <Button onClick={reset} variant="outline" className="mt-5 gap-2">
        <RefreshCw className="h-4 w-4" />
        다시 시도
      </Button>
    </div>
  );
}
