import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  staticClasses,
} from "@decky/ui";
import { definePlugin, toaster } from "@decky/api";
import { FaGamepad } from "react-icons/fa";
import { useMemo, useState } from "react";

import { CefStatus, checkCefDebugging, exportConfig, importConfig, Rom } from "./backend";
import { Lang, makeT, type T } from "./i18n";

import { useConfig } from "./hooks/useConfig";
import { useLogs } from "./hooks/useLogs";
import { usePreview } from "./hooks/usePreview";
import { useSgdb } from "./hooks/useSgdb";
import { useSync } from "./hooks/useSync";
import { useValidation } from "./hooks/useValidation";

import { CleanupPanel } from "./components/CleanupPanel";
import { DefaultsPanel } from "./components/DefaultsPanel";
import { IoPanel } from "./components/IoPanel";
import { LanguagePanel } from "./components/LanguagePanel";
import { LogsPanel } from "./components/LogsPanel";
import { PreviewPanel } from "./components/PreviewPanel";
import { ProfilesEditor } from "./components/ProfilesEditor";
import { RootsEditor } from "./components/RootsEditor";
import { SgdbPanel } from "./components/SgdbPanel";
import { ValidationPanel } from "./components/ValidationPanel";

function notify(
  t: T,
  titleKey: string,
  opts?: { body?: string; bodyKey?: string; vars?: Record<string, string | number>; duration?: number },
) {
  toaster.toast({
    title:    t(titleKey, opts?.vars),
    body:     opts?.body ?? (opts?.bodyKey ? t(opts.bodyKey, opts?.vars) : undefined),
    duration: opts?.duration,
  });
}

function Content() {
  const { cfg, dirty, mutate, persist, reset, replace } = useConfig();
  const { report: validation, refresh: refreshValidation } = useValidation();
  const { preview, scan, clear: clearPreview } = usePreview();
  const { progress, undoCount, runSync, cleanStale, undoLast } = useSync();
  const { lines: logs, refresh: refreshLogs } = useLogs();
  const sgdb = useSgdb();

  const [busy, setBusy] = useState(false);
  const [cef, setCef]   = useState<CefStatus | null>(null);

  const lang: Lang = cfg?.language ?? "en";
  const t = useMemo(() => makeT(lang), [lang]);

  if (!cfg) return <PanelSection title={t("loading")} />;

  const savePersist = async () => {
    const saved = await persist();
    if (saved) await refreshValidation();
    return saved;
  };

  const onSave = async () => {
    const saved = await savePersist();
    if (!saved) return;
    notify(t, "toast.saved.title", {
      bodyKey: "toast.saved.body",
      vars: { roots: saved.roots.length, profiles: saved.profiles.length },
    });
  };

  const onReset = async () => {
    await reset(lang);
    notify(t, "toast.reset");
  };

  const onPreview = async () => {
    setBusy(true);
    try {
      if (dirty) await savePersist();
      const roms = await scan();
      notify(t, roms.length === 0 ? "preview.none" : "preview.count", { vars: { n: roms.length } });
    } finally {
      setBusy(false);
    }
  };

  const doSync = async (roms: Rom[]) => {
    setBusy(true);
    try {
      const s = await runSync(roms, cfg.assign_collection);
      clearPreview();
      const baseBody = s.failed
        ? t("toast.sync.bodyFail", { added: s.added, skipped: s.skipped, failed: s.failed })
        : t("toast.sync.body",     { added: s.added, skipped: s.skipped });
      const artBody = s.artworkApplied ? ` · ${t("artwork.applied", { n: s.artworkApplied })}` : "";
      notify(t, "toast.sync.title", { body: baseBody + artBody, duration: 5000 });
    } catch (e) {
      notify(t, "toast.syncFail", { body: String(e) });
    } finally {
      setBusy(false);
    }
  };

  const onDirectSync = async () => {
    if (dirty) await savePersist();
    const roms = await scan();
    await doSync(roms);
  };

  const onCleanStale = async () => {
    setBusy(true);
    try {
      const s = await cleanStale();
      notify(t, "toast.clean.title", {
        bodyKey: "toast.clean.body",
        vars: { removed: s.removed, kept: s.kept },
      });
    } finally {
      setBusy(false);
    }
  };

  const onUndo = async () => {
    setBusy(true);
    try {
      const n = await undoLast();
      if (n) notify(t, "toast.undo", { vars: { n } });
    } finally {
      setBusy(false);
    }
  };

  const onExport = async () => {
    const blob = await exportConfig();
    try {
      await navigator.clipboard.writeText(blob);
      notify(t, "toast.export");
    } catch {
      notify(t, "toast.export", { body: blob.slice(0, 120) + "…" });
    }
  };

  const onImport = async () => {
    try {
      const blob = await navigator.clipboard.readText();
      const imported = await importConfig(blob);
      if (!imported.language) imported.language = lang;
      replace(imported);
      await refreshValidation();
      notify(t, "toast.importOk");
    } catch (e) {
      notify(t, "toast.importFail", { body: String(e) });
    }
  };

  const onTestSgdb = async () => {
    if (dirty) await savePersist();
    const res = await sgdb.testKey(cfg.steamgriddb_api_key || null);
    notify(t, res.ok ? "toast.sgdbOk" : "toast.sgdbKo", { body: res.ok ? undefined : res.error });
  };

  const onClearSgdbCache = async () => {
    const n = await sgdb.clearCache();
    notify(t, "toast.sgdbCacheCleared", { vars: { n } });
  };

  const onPasteSgdbKey = async () => {
    try {
      const key = await sgdb.pasteKeyFromClipboard();
      if (!key) {
        notify(t, "toast.sgdbPasteBad");
        return;
      }
      replace({ ...cfg, steamgriddb_api_key: key, steamgriddb_enabled: true });
      const saved = await persist();
      notify(t, "toast.sgdbPasteOk");
      const res = await sgdb.testKey(saved?.steamgriddb_api_key ?? key);
      notify(t, res.ok ? "toast.sgdbOk" : "toast.sgdbKo", { body: res.ok ? undefined : res.error });
    } catch (e) {
      notify(t, "toast.sgdbPasteBad", { body: String(e) });
    }
  };

  const onCheckCef = async () => {
    const s = await checkCefDebugging();
    setCef(s);
    notify(t, s.ok ? "toast.cefOk" : "toast.cefKo", {
      body: s.ok ? t("toast.cefOkBody", { targets: s.targets ?? 0 }) : (s.error ?? s.note ?? "unknown"),
    });
  };

  const progressLabel = progress
    ? t("progress.label", { done: progress.done, total: progress.total })
    : null;

  return (
    <>
      <LanguagePanel lang={lang} onChange={(l) => mutate({ language: l })} t={t} />

      <RootsEditor    roots={cfg.roots}       onChange={(roots) => mutate({ roots })}       t={t} validation={validation} />
      <ProfilesEditor profiles={cfg.profiles} onChange={(profiles) => mutate({ profiles })} t={t} validation={validation} />

      <DefaultsPanel
        compatTool={cfg.default_compat_tool}
        collection={cfg.assign_collection}
        t={t}
        onCompatToolChange={(v) => mutate({ default_compat_tool: v })}
        onCollectionChange={(v) => mutate({ assign_collection: v })}
      />

      <SgdbPanel
        apiKey={cfg.steamgriddb_api_key}
        enabled={cfg.steamgriddb_enabled}
        busy={busy}
        t={t}
        onApiKeyChange={(v) => mutate({ steamgriddb_api_key: v })}
        onEnabledChange={(v) => mutate({ steamgriddb_enabled: v })}
        onOpenLogin={sgdb.openLoginPage}
        onPasteKey={onPasteSgdbKey}
        onTest={onTestSgdb}
        onClearCache={onClearSgdbCache}
      />

      <PreviewPanel
        preview={preview}
        busy={busy}
        progressLabel={progressLabel}
        t={t}
        onPreview={onPreview}
        onConfirm={doSync}
      />

      <PanelSection title={t("section.actions")}>
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={!dirty || busy} onClick={onSave}>
            {dirty ? t("btn.save") : t("btn.saved")}
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={busy} onClick={onDirectSync}>
            {progressLabel ?? (busy ? t("btn.syncing") : t("btn.sync"))}
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>

      <CleanupPanel busy={busy} undoCount={undoCount} t={t} onClean={onCleanStale} onUndo={onUndo} />

      <IoPanel t={t} onExport={onExport} onImport={onImport} />

      <LogsPanel lines={logs} t={t} onRefresh={refreshLogs} />

      <ValidationPanel cef={cef} t={t} onCheckCef={onCheckCef} onReset={onReset} />
    </>
  );
}

export default definePlugin(() => ({
  name: "ROM Injector",
  titleView: <div className={staticClasses.Title}>ROM Injector</div>,
  content: <Content />,
  icon: <FaGamepad />,
  onDismount() {},
}));
