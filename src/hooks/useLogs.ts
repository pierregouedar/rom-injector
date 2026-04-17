import { useState } from "react";
import { getLogs } from "../backend";

export function useLogs() {
  const [lines, setLines] = useState<string[]>([]);
  const refresh = async () => setLines(await getLogs(100));
  return { lines, refresh };
}
