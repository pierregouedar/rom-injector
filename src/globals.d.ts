import type { ShortcutEntry } from "./steam";

declare global {
  const SteamClient: {
    URL?: { ExecuteSteamURL?: (url: string) => void };
    System?: { OpenInSystemBrowser?: (url: string) => void };
    Apps: {
      AddShortcut: (name: string, exe: string, startDir: string, launchOpts: string) => Promise<number>;
      RemoveShortcut: (appid: number) => Promise<void>;
      SetShortcutIcon: (appid: number, path: string) => Promise<void>;
      SetShortcutLaunchOptions: (appid: number, opts: string) => Promise<void>;
      SpecifyCompatTool: (appid: number, tool: string) => Promise<void>;
      SetCustomArtworkForApp: (appid: number, b64: string, ext: string, assetType: number) => Promise<void>;
      RegisterForShortcutList: (cb: (list: ShortcutEntry[]) => void) => { unregister: () => void };
    };
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const collectionStore: any;
}

export {};
