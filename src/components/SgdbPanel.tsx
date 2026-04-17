import { ButtonItem, PanelSection, PanelSectionRow, TextField, ToggleField } from "@decky/ui";
import type { makeT } from "../i18n";

type T = ReturnType<typeof makeT>;

export function SgdbPanel({
  apiKey, enabled, busy, t,
  onApiKeyChange, onEnabledChange,
  onOpenLogin, onPasteKey, onTest, onClearCache,
}: {
  apiKey: string;
  enabled: boolean;
  busy: boolean;
  t: T;
  onApiKeyChange: (v: string) => void;
  onEnabledChange: (v: boolean) => void;
  onOpenLogin: () => void;
  onPasteKey: () => void;
  onTest: () => void;
  onClearCache: () => void;
}) {
  return (
    <PanelSection title={t("section.sgdb")}>
      <PanelSectionRow>
        <ToggleField
          label={t("sgdb.enabled")}
          checked={enabled}
          onChange={onEnabledChange}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <div style={{ fontSize: 11, opacity: 0.65, padding: "4px 0" }}>
          {t("sgdb.autoHint")}
        </div>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onOpenLogin}>{t("btn.sgdbOpenLogin")}</ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onPasteKey}>{t("btn.sgdbPasteKey")}</ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <TextField
          label={t("sgdb.apiKey")}
          description={t("sgdb.apiKeyHint")}
          value={apiKey}
          onChange={(e) => onApiKeyChange(e.target.value)}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={busy || !apiKey} onClick={onTest}>
          {t("btn.sgdbTest")}
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={busy} onClick={onClearCache}>
          {t("btn.sgdbClearCache")}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
