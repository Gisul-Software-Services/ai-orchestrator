import { Suspense } from "react";
import { FlaskConical } from "lucide-react";
import { PlaygroundClient } from "@/components/playground/PlaygroundClient";

function PlaygroundFallback() {
  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-sm text-zinc-500">
      <FlaskConical className="h-8 w-8 animate-pulse text-console-accent/60" strokeWidth={1.5} />
      Loading playground…
    </div>
  );
}

export default function PlaygroundPage() {
  return (
    <Suspense fallback={<PlaygroundFallback />}>
      <PlaygroundClient />
    </Suspense>
  );
}
