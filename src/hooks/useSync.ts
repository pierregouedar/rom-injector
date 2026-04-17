import { useEffect, useState } from "react";
import {
  Rom,
  clearLastSync,
  findStaleRomPaths,
  getLastSync,
  recordLastSync,
} from "../backend";
import {
  SteamClient,
  buildExistingSet,
  extractRomPathFromLaunchOpts,
  snapshotShortcuts,
  syncOne,
} from "../steam";

export type Progress = { done: number; total: number };
export type SyncSummary = {
  added: number;
  skipped: number;
  failed: number;
  artworkApplied: number;
  addedAppIds: number[];
};
export type CleanupSummary = { removed: number; kept: number };

export function useSync() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [undoCount, setUndoCount] = useState(0);

  useEffect(() => {
    getLastSync().then((ids) => setUndoCount(ids.length));
  }, []);

  const runSync = async (roms: Rom[], collection: string): Promise<SyncSummary> => {
    setProgress({ done: 0, total: roms.length });
    try {
      const current = await snapshotShortcuts();
      const existing = buildExistingSet(current);
      const summary: SyncSummary = {
        added: 0, skipped: 0, failed: 0, artworkApplied: 0, addedAppIds: [],
      };
      let i = 0;
      for (const rom of roms) {
        const res = await syncOne(rom, existing, collection);
        if (res.status === "added") {
          summary.added++;
          if (res.appid != null) summary.addedAppIds.push(res.appid);
          if (res.artwork) summary.artworkApplied += res.artwork;
        } else if (res.status === "skipped") {
          summary.skipped++;
        } else {
          summary.failed++;
        }
        i++;
        setProgress({ done: i, total: roms.length });
      }
      if (summary.addedAppIds.length) {
        await recordLastSync(summary.addedAppIds);
        setUndoCount(summary.addedAppIds.length);
      }
      return summary;
    } finally {
      setProgress(null);
    }
  };

  const cleanStale = async (): Promise<CleanupSummary> => {
    const current = await snapshotShortcuts();
    const candidates = current
      .map((s) => ({ appid: s.appid, romQuoted: extractRomPathFromLaunchOpts(s.strLaunchOptions) }))
      .filter((c): c is { appid: number; romQuoted: string } => c.romQuoted !== null);
    const stale = new Set(await findStaleRomPaths(candidates.map((c) => c.romQuoted)));
    let removed = 0;
    for (const c of candidates) {
      if (!stale.has(c.romQuoted)) continue;
      try {
        await SteamClient.Apps.RemoveShortcut(c.appid);
        removed++;
      } catch (e) {
        console.error("[rom-injector] RemoveShortcut failed", c.appid, e);
      }
    }
    return { removed, kept: candidates.length - removed };
  };

  const undoLast = async (): Promise<number> => {
    const ids = await getLastSync();
    if (!ids.length) return 0;
    for (const id of ids) {
      try { await SteamClient.Apps.RemoveShortcut(id); } catch (e) { console.error(e); }
    }
    await clearLastSync();
    setUndoCount(0);
    return ids.length;
  };

  return { progress, undoCount, runSync, cleanStale, undoLast };
}
