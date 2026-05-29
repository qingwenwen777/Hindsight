"use client";

import { Button } from "@/components/ui/button";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 py-24">
      <h1 className="text-h1 text-primary">出错了</h1>
      <p className="max-w-md text-center text-small text-secondary">{error.message || "未知错误"}</p>
      <Button onClick={reset}>重试</Button>
    </div>
  );
}
