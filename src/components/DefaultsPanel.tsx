import { PanelSection, PanelSectionRow, TextField } from "@decky/ui";
import type { makeT } from "../i18n";

type T = ReturnType<typeof makeT>;

export function DefaultsPanel({
  compatTool, collection, t, onCompatToolChange, onCollectionChange,
}: {
  compatTool: string;
  collection: string;
  t: T;
  onCompatToolChange: (v: string) => void;
  onCollectionChange: (v: string) => void;
}) {
  return (
    <>
      <PanelSection title={t("section.defaults")}>
        <PanelSectionRow>
          <TextField
            label={t("default.compat")}
            value={compatTool}
            onChange={(e) => onCompatToolChange(e.target.value)}
          />
        </PanelSectionRow>
      </PanelSection>
      <PanelSection title={t("section.collection")}>
        <PanelSectionRow>
          <TextField
            label={t("collection.name")}
            value={collection}
            onChange={(e) => onCollectionChange(e.target.value)}
          />
        </PanelSectionRow>
      </PanelSection>
    </>
  );
}
