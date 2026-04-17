import { clearSgdbCache, testSteamgriddbKey } from "../backend";
import { openExternal } from "../steam";

export const SGDB_API_PAGE = "https://www.steamgriddb.com/profile/preferences/api";

const looksLikeKey = (s: string) => /^[A-Za-z0-9]{20,64}$/.test(s.trim());

export function useSgdb() {
  const openLoginPage = () => openExternal(SGDB_API_PAGE);

  const testKey = (key: string | null) => testSteamgriddbKey(key);

  const clearCache = () => clearSgdbCache();

  const pasteKeyFromClipboard = async (): Promise<string | null> => {
    const raw = (await navigator.clipboard.readText()).trim();
    return looksLikeKey(raw) ? raw : null;
  };

  return { openLoginPage, testKey, clearCache, pasteKeyFromClipboard };
}
