import { DropdownItem, PanelSection, PanelSectionRow } from "@decky/ui";
import { Lang, LANG_LABELS, LANGS, type T } from "../i18n";


export function LanguagePanel({
  lang, onChange, t,
}: {
  lang: Lang;
  onChange: (l: Lang) => void;
  t: T;
}) {
  return (
    <PanelSection title={t("section.language")}>
      <PanelSectionRow>
        <DropdownItem
          label={t("language.select")}
          rgOptions={LANGS.map((l) => ({ label: LANG_LABELS[l], data: l }))}
          selectedOption={lang}
          onChange={(opt: { data: Lang }) => onChange(opt.data)}
        />
      </PanelSectionRow>
    </PanelSection>
  );
}
