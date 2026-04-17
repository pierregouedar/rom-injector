import { ButtonItem, PanelSection, PanelSectionRow } from "@decky/ui";
import type { T } from "../i18n";


export function CleanupPanel({
  busy, undoCount, t, onClean, onUndo,
}: {
  busy: boolean;
  undoCount: number;
  t: T;
  onClean: () => void;
  onUndo: () => void;
}) {
  return (
    <PanelSection title={t("section.cleanup")}>
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={busy} onClick={onClean}>
          {busy ? t("btn.cleaning") : t("btn.clean")}
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={busy || undoCount === 0} onClick={onUndo}>
          {undoCount > 0 ? t("btn.undo", { n: undoCount }) : t("btn.undoNone")}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
