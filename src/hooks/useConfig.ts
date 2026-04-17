import { useEffect, useState } from "react";
import { Cfg, getConfig, resetConfig, saveConfig } from "../backend";
import { detectLang, Lang } from "../i18n";

export function useConfig() {
  const [cfg, setCfg]     = useState<Cfg | null>(null);
  const [dirty, setDirty] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

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

  const mutate = (patch: Partial<Cfg>) => {
    if (!cfg) return;
    setCfg({ ...cfg, ...patch });
    setDirty(true);
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

  return { cfg, dirty, mutate, persist, reset, replace, setDirty, loadError };
}
