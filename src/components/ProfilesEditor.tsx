import { ButtonItem, DialogButton, Focusable, PanelSection, PanelSectionRow, TextField } from "@decky/ui";
import { FaFile, FaPlus, FaTrash } from "react-icons/fa";
import { EMPTY_PROFILE, Profile, ValidationReport } from "../backend";
import type { T } from "../i18n";
import { pickFile } from "../steam";


export function ProfilesEditor({
  profiles, onChange, t, validation,
}: {
  profiles: Profile[];
  onChange: (profiles: Profile[]) => void;
  t: T;
  validation: ValidationReport | null;
}) {
  const patch = (i: number, key: keyof Profile, value: string) => {
    const next = profiles.slice();
    next[i] = { ...next[i], [key]: value };
    onChange(next);
  };

  return (
    <PanelSection title={t("section.profiles")}>
      {profiles.map((p, i) => {
        const v = validation?.profiles[i];
        const exeBad = !!v && !v.exe_exists;
        return (
          <PanelSectionRow key={`prof-${i}`}>
            <Focusable
              style={{
                display: "flex", flexDirection: "column", gap: 4,
                padding: "6px 0",
                borderBottom: "1px solid rgba(255,255,255,0.08)",
                width: "100%",
              }}
            >
              <TextField label={t("profile.ext")}    value={p.ext}  onChange={(e) => patch(i, "ext",  e.target.value)} />
              <Focusable style={{ display: "flex", gap: 6, alignItems: "center", width: "100%" }}>
                <div style={{ flex: 1 }}>
                  <TextField
                    label={`${t("profile.exe")}${v ? ` · ${exeBad ? t("valid.exeMissing") : t("valid.exeOk")}` : ""}`}
                    value={p.exe}
                    style={exeBad ? { outline: "1px solid #d33" } : undefined}
                    onChange={(e) => patch(i, "exe",  e.target.value)}
                  />
                </div>
                <DialogButton
                  style={{ minWidth: 40, width: 40, padding: 8 }}
                  onClick={async () => {
                    const picked = await pickFile(p.exe || "/usr/bin");
                    if (picked) patch(i, "exe", picked);
                  }}
                >
                  <FaFile />
                </DialogButton>
              </Focusable>
              <TextField label={t("profile.args")}   value={p.args} onChange={(e) => patch(i, "args", e.target.value)} />
              <TextField label={t("profile.compat")} value={p.compat_tool} onChange={(e) => patch(i, "compat_tool", e.target.value)} />
              <DialogButton
                style={{ alignSelf: "flex-end", marginTop: 4 }}
                onClick={() => onChange(profiles.filter((_, j) => j !== i))}
              >
                <FaTrash style={{ marginRight: 6 }} /> {t("profile.remove")}
              </DialogButton>
            </Focusable>
          </PanelSectionRow>
        );
      })}
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => onChange([...profiles, { ...EMPTY_PROFILE }])}>
          <FaPlus style={{ marginRight: 6 }} /> {t("profile.add")}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
