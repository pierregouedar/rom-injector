import { useEffect, useRef, useState } from "react";
import { Cfg, getConfig, resetConfig, saveConfig } from "../backend";
import { detectLang, Lang } from "../i18n";

const AUTOSAVE_DEBOUNCE_MS = 500;

export function useConfig() {
  const [cfg, setCfg]             = useState<Cfg | null>(null);
  const [dirty, setDirty]         = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving]       = useState(false);
  const autosaveTimer             = useRef<number | null>(null);

  useEffect(() => {
    getConfig()
      .then((c) => {
        if (!c.language) c.language = detectLang();
        setCfg(c);
      })
      .catch((e) => {
        const msg = String(e?.message ?? e);
        console.error("[rom-injector] get_config failed", e);
        setLoadError(msg);
      });
  }, []);

  useEffect(() => {
    return () => {
      if (autosaveTimer.current != null) {
        clearTimeout(autosaveTimer.current);
      }
    };
  }, []);

  const flushAutosave = (next: Cfg) => {
    if (autosaveTimer.current != null) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = window.setTimeout(async () => {
      setSaving(true);
      try {
        const saved = await saveConfig(next);
        if (!saved.language) saved.language = next.language;
        setCfg(saved);
        setDirty(false);
        setSaveError(null);
      } catch (e) {
        const msg = String((e as Error)?.message ?? e);
        console.error("[rom-injector] autosave failed", e);
        setSaveError(msg);
      } finally {
        setSaving(false);
      }
    }, AUTOSAVE_DEBOUNCE_MS);
  };

  const mutate = (patch: Partial<Cfg>) => {
    if (!cfg) return;
    const next = { ...cfg, ...patch };
    setCfg(next);
    setDirty(true);
    flushAutosave(next);
  };

  const persist = async (): Promise<Cfg | null> => {
    if (!cfg) return null;
    const saved = await saveConfig(cfg);
    if (!saved.language) saved.language = cfg.language;
    setCfg(saved);
    setDirty(false);
    return saved;
  };

  const reset = async (keepLang: Lang) => {
    const fresh = await resetConfig();
    fresh.language = keepLang;
    setCfg(fresh);
    setDirty(true);
  };

  const replace = (next: Cfg) => {
    setCfg(next);
    setDirty(false);
  };

  return { cfg, dirty, mutate, persist, reset, replace, setDirty, loadError, saveError, saving };
}
