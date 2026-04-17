import { ButtonItem, PanelSection, PanelSectionRow } from "@decky/ui";
import type { makeT } from "../i18n";

type T = ReturnType<typeof makeT>;

export function IoPanel({ t, onExport, onImport }: {
  t: T;
  onExport: () => void;
  onImport: () => void;
}) {
  return (
    <PanelSection title={t("section.io")}>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onExport}>{t("btn.export")}</ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onImport}>{t("btn.import")}</ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
