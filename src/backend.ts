import { callable } from "@decky/api";
import type { Lang } from "./i18n";

export type Profile = {
  ext: string;
  exe: string;
  args: string;
  compat_tool: string;
};

export type Cfg = {
  roots: string[];
  default_compat_tool: string;
  assign_collection: string;
  steamgriddb_api_key: string;
  steamgriddb_enabled: boolean;
  profiles: Profile[];
  language?: Lang;
};

export type ArtworkAsset = { b64: string; ext: string };
export type Artwork = {
  grid?: ArtworkAsset;
  hero?: ArtworkAsset;
  logo?: ArtworkAsset;
  icon?: ArtworkAsset;
};

export type Rom = {
  name: string;
  exe: string;
  start_dir: string;
  launch_opts: string;
  icon_path: string;
  compat_tool: string;
  dedupe_key: string;
  rom_path: string;
  artwork: Artwork;
};

export type CefStatus = {
  ok: boolean;
  error?: string;
  note?: string;
  targets?: number;
};

export type ValidationReport = {
  roots: { path: string; exists: boolean }[];
  profiles: { ext: string; exe: string; exe_exists: boolean }[];
};

export const getConfig          = callable<[], Cfg>("get_config");
export const saveConfig         = callable<[Cfg], Cfg>("save_config");
export const resetConfig        = callable<[], Cfg>("reset_config");
export const exportConfig       = callable<[], string>("export_config");
export const importConfig       = callable<[string], Cfg>("import_config");
export const validateConfig     = callable<[], ValidationReport>("validate_config");
export const getRomsToSync      = callable<[], Rom[]>("get_roms_to_sync");
export const findStaleRomPaths  = callable<[string[]], string[]>("find_stale_rom_paths");
export const recordLastSync     = callable<[number[]], void>("record_last_sync");
export const getLastSync        = callable<[], number[]>("get_last_sync");
export const clearLastSync      = callable<[], void>("clear_last_sync");
export const getLogs            = callable<[number], string[]>("get_logs");
export const checkCefDebugging  = callable<[], CefStatus>("check_cef_debugging");
export const testSteamgriddbKey = callable<[string | null], { ok: boolean; error?: string }>("test_steamgriddb_key");
export const clearSgdbCache     = callable<[], number>("clear_sgdb_cache");
export const debugPaths         = callable<[], Record<string, unknown>>("debug_paths");

export const EMPTY_PROFILE: Profile = { ext: "", exe: "", args: "{rom}", compat_tool: "" };
