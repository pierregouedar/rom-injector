import { ButtonItem, DialogButton, Focusable, PanelSection, PanelSectionRow, TextField } from "@decky/ui";
import { FaFolderOpen, FaPlus, FaTrash } from "react-icons/fa";
import type { ValidationReport } from "../backend";
import type { T } from "../i18n";
import { pickFolder } from "../steam";


export function RootsEditor({
  roots, onChange, t, validation,
}: {
  roots: string[];
  onChange: (roots: string[]) => void;
  t: T;
  validation: ValidationReport | null;
}) {
  return (
    <PanelSection title={t("section.roots")}>
      {roots.map((r, i) => {
        const v = validation?.roots[i];
        const bad = !!v && !v.exists;
        return (
          <PanelSectionRow key={`root-${i}`}>
            <Focusable style={{ display: "flex", gap: 8, alignItems: "center", width: "100%" }}>
              <div style={{ flex: 1 }}>
                <TextField
                  label={`${t("root.label", { n: i + 1 })}${v ? ` · ${bad ? t("valid.rootMissing") : t("valid.rootOk")}` : ""}`}
                  value={r}
                  style={bad ? { outline: "1px solid #d33" } : undefined}
                  onChange={(e) => {
                    const next = roots.slice();
                    next[i] = e.target.value;
                    onChange(next);
                  }}
                />
              </div>
              <DialogButton
                style={{ minWidth: 40, width: 40, padding: 8 }}
                onClick={async () => {
                  const picked = await pickFolder(r || "/home/deck/Emulation");
                  if (picked) {
                    const next = roots.slice();
                    next[i] = picked;
                    onChange(next);
                  }
                }}
              >
                <FaFolderOpen />
              </DialogButton>
              <DialogButton
                style={{ minWidth: 40, width: 40, padding: 8 }}
                onClick={() => onChange(roots.filter((_, j) => j !== i))}
              >
                <FaTrash />
              </DialogButton>
            </Focusable>
          </PanelSectionRow>
        );
      })}
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => onChange([...roots, ""])}>
          <FaPlus style={{ marginRight: 6 }} /> {t("root.add")}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
