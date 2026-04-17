import { useEffect, useState } from "react";
import { ValidationReport, validateConfig } from "../backend";

export function useValidation() {
  const [report, setReport] = useState<ValidationReport | null>(null);

  const refresh = async () => setReport(await validateConfig());

  useEffect(() => { refresh(); }, []);

  return { report, refresh };
}
