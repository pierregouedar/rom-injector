import { useState } from "react";
import { Rom, getRomsToSync } from "../backend";

export function usePreview() {
  const [preview, setPreview] = useState<Rom[] | null>(null);
  const [scanning, setScanning] = useState(false);

  const scan = async (): Promise<Rom[]> => {
    setScanning(true);
    try {
      const roms = await getRomsToSync();
      setPreview(roms);
      return roms;
    } finally {
      setScanning(false);
    }
  };

  const clear = () => setPreview(null);

  return { preview, scanning, scan, clear };
}
