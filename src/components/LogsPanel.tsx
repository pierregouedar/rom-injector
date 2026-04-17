import { ButtonItem, PanelSection, PanelSectionRow } from "@decky/ui";
import type { T } from "../i18n";


export function LogsPanel({ lines, t, onRefresh }: {
  lines: string[];
  t: T;
  onRefresh: () => void;
}) {
  return (
    <PanelSection title={t("section.logs")}>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onRefresh}>{t("btn.refreshLogs")}</ButtonItem>
      </PanelSectionRow>
      {lines.length > 0 && (
        <PanelSectionRow>
          <div style={{
            maxHeight: 140, overflow: "auto", fontFamily: "monospace",
            fontSize: 10, opacity: 0.75, whiteSpace: "pre-wrap",
          }}>
            {lines.slice(-50).join("\n")}
          </div>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}
