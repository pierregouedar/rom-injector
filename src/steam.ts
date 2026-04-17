import type { Artwork, Rom } from "./backend";

export type ShortcutEntry = {
  appid: number;
  strAppName: string;
  strExePath: string;
  strShortcutStartDir: string;
  strLaunchOptions: string;
};

export const getCollectionStore = () =>
  (typeof collectionStore !== "undefined" ? collectionStore : null);

export const removeShortcut = (appid: number) => SteamClient.Apps.RemoveShortcut(appid);

export function snapshotShortcuts(): Promise<ShortcutEntry[]> {
  return new Promise((resolve) => {
    const sub = SteamClient.Apps.RegisterForShortcutList((list) => {
      sub.unregister();
      resolve(list ?? []);
    });
  });
}

export const stripQuotes = (s: string) => s?.replace(/^"|"$/g, "") ?? "";

export const buildExistingSet = (entries: ShortcutEntry[]) =>
  new Set(entries.map((s) => `${stripQuotes(s.strExePath)}|${s.strLaunchOptions}`));

export function extractRomPathFromLaunchOpts(opts: string): string | null {
  const m = opts.match(/"([^"]+)"/g);
  if (!m) return null;
  for (const tok of m.reverse()) {
    if (tok.slice(1, -1).includes("/")) return tok;
  }
  return null;
}

export async function applyArtwork(appid: number, art: Artwork): Promise<number> {
  const map: [keyof Artwork, number][] = [["grid", 0], ["hero", 1], ["logo", 2], ["icon", 3]];
  let applied = 0;
  for (const [k, type] of map) {
    const a = art[k];
    if (!a) continue;
    try {
      await SteamClient.Apps.SetCustomArtworkForApp(appid, a.b64, a.ext, type);
      applied++;
    } catch (e) {
      console.error("[rom-injector] artwork failed", k, e);
    }
  }
  return applied;
}

export async function addToCollection(appid: number, collectionName: string): Promise<void> {
  if (!collectionName) return;
  const store = getCollectionStore();
  if (!store) return;
  try {
    let col = store.userCollections?.find?.((c: any) => c.displayName === collectionName);
    if (!col && typeof store.CreateCollection === "function") {
      col = await store.CreateCollection(collectionName);
    }
    const id = col?.id ?? col?.m_strId;
    if (!id) return;
    if (typeof store.AddAppsToCollection === "function") {
      await store.AddAppsToCollection(id, [appid]);
    } else if (typeof col.AsEditableCollection === "function") {
      col.AsEditableCollection().AddApps([{ appid }]);
    }
  } catch (e) {
    console.warn("[rom-injector] collection assign failed", e);
  }
}

export type SyncResult = {
  status: "added" | "skipped" | "failed";
  appid?: number;
  artwork?: number;
};

export async function syncOne(
  rom: Rom,
  existing: Set<string>,
  collection: string,
): Promise<SyncResult> {
  if (existing.has(rom.dedupe_key)) return { status: "skipped" };
  try {
    const appid = await SteamClient.Apps.AddShortcut(rom.name, rom.exe, rom.start_dir, rom.launch_opts);
    if (appid == null) throw new Error("AddShortcut returned null");
    if (rom.icon_path)   await SteamClient.Apps.SetShortcutIcon(appid, rom.icon_path);
    if (rom.launch_opts) await SteamClient.Apps.SetShortcutLaunchOptions(appid, rom.launch_opts);
    if (rom.compat_tool) await SteamClient.Apps.SpecifyCompatTool(appid, rom.compat_tool);
    const artwork = await applyArtwork(appid, rom.artwork || {});
    if (collection) await addToCollection(appid, collection);
    existing.add(rom.dedupe_key);
    return { status: "added", appid, artwork };
  } catch (e) {
    console.error("[rom-injector] AddShortcut failed", rom.name, e);
    return { status: "failed" };
  }
}

export function openExternal(url: string): void {
  try {
    if (SteamClient.URL?.ExecuteSteamURL) {
      SteamClient.URL.ExecuteSteamURL(`steam://openurl/${url}`);
      return;
    }
    if (SteamClient.System?.OpenInSystemBrowser) {
      SteamClient.System.OpenInSystemBrowser(url);
      return;
    }
    window.open(url, "_blank");
  } catch (e) {
    console.error("[rom-injector] open url failed", e);
    window.open(url, "_blank");
  }
}
