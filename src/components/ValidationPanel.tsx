import { ButtonItem, PanelSection, PanelSectionRow } from "@decky/ui";
import { FaUndo } from "react-icons/fa";
import type { CefStatus } from "../backend";
import type { T } from "../i18n";


export function ValidationPanel({
  cef, t, onCheckCef, onReset,
}: {
  cef: CefStatus | null;
  t: T;
  onCheckCef: () => void;
  onReset: () => void;
}) {
  return (
    <PanelSection title={t("section.validation")}>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onCheckCef}>{t("btn.cef")}</ButtonItem>
      </PanelSectionRow>
      {cef && (
        <PanelSectionRow>
          <div style={{ fontSize: 12, opacity: 0.7 }}>
            {t("cef.prefix")}: {cef.ok ? t("cef.ok") : (cef.error ?? cef.note)}
          </div>
        </PanelSectionRow>
      )}
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onReset}>
          <FaUndo style={{ marginRight: 6 }} /> {t("btn.reset")}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
