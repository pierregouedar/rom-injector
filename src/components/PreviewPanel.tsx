import { ButtonItem, PanelSection, PanelSectionRow } from "@decky/ui";
import type { Rom } from "../backend";
import type { T } from "../i18n";


export function PreviewPanel({
  preview, busy, progressLabel, t, onPreview, onConfirm,
}: {
  preview: Rom[] | null;
  busy: boolean;
  progressLabel: string | null;
  t: T;
  onPreview: () => void;
  onConfirm: (roms: Rom[]) => void;
}) {
  return (
    <PanelSection title={t("section.preview")}>
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={busy} onClick={onPreview}>
          {busy && !progressLabel ? t("btn.previewing") : t("btn.preview")}
        </ButtonItem>
      </PanelSectionRow>
      {preview && (
        <>
          <PanelSectionRow>
            <div style={{ fontSize: 12, opacity: 0.8 }}>
              {preview.length === 0 ? t("preview.none") : t("preview.count", { n: preview.length })}
            </div>
          </PanelSectionRow>
          <PanelSectionRow>
            <div style={{ maxHeight: 120, overflow: "auto", fontSize: 11, opacity: 0.7 }}>
              {preview.slice(0, 50).map((r) => (
                <div key={r.dedupe_key}>• {r.name}</div>
              ))}
              {preview.length > 50 && <div>…</div>}
            </div>
          </PanelSectionRow>
          {preview.length > 0 && (
            <PanelSectionRow>
              <ButtonItem layout="below" disabled={busy} onClick={() => onConfirm(preview)}>
                {progressLabel ?? t("btn.confirmSync", { n: preview.length })}
              </ButtonItem>
            </PanelSectionRow>
          )}
        </>
      )}
    </PanelSection>
  );
}
