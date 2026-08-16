
export const pgvToColor = (pgv: number): string => {
  const pgvMicrons = pgv * 1_000_000;

  if (pgvMicrons < 0.2) return "#0055FF";
  if (pgvMicrons < 0.4) return "#6688FF";
  if (pgvMicrons < 0.8) return "#00FFFF";
  if (pgvMicrons < 1.5) return "#80FF80";
  if (pgvMicrons < 4.0) return "#FFFF00";
  if (pgvMicrons < 12)  return "#FFCC00";
  if (pgvMicrons < 30)  return "#FF9900";
  if (pgvMicrons < 60)  return "#FF5500";
  return "#FF0000";
};

export const getMagColor = (mag: number): string => {
  if (mag >= 7) return "#B71C1C";
  if (mag >= 6) return "#D32F2F";
  if (mag >= 5) return "#F57C00";
  if (mag >= 4) return "#FBC02D";
  return "#388E3C";
};

export const getEarthquakeRadius = (magnitude: number): number => {
  return Math.max(20000, magnitude * 12000);
};

export const getColorMmi = (intensity: number) => {
  const mmiColors = ["#464646", "#777777", "#aae0fa", "#6cbce8", "#4cd3c2", "#6cd94e", "#f2db36", "#e59b12", "#dc6e19", "#e24329", "#b81414", "#8f0606", "#500000"];
  try {
    return mmiColors[Math.round(intensity)];
  } catch {
    return mmiColors[0];
  }
};

export const getColorShindo = (intensity: number) => {
  const shindoColors = ["#464646", "#2b8cb3", "#3fa887", "#e0b134", "#e88527", "#c92214", "#b01312", "#7c0b53", "#6d0359", "#440375"];
  try {
    return shindoColors[Math.round(intensity)];
  } catch {
    return shindoColors[0];
  }
};

export const getNumericIntensityMMI = (intensity: number) => {
  const mmiSymbols = ["-", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];
  return mmiSymbols[Math.round(intensity)] ?? "?";
};

export const getNumericIntensityShindo = (intensity: number) => {
  const shindoSymbols = ["0", "1", "2", "3", "4", "5-", "5+", "6-", "6+", "7"];
  return shindoSymbols[Math.round(intensity)] ?? "?";
};

export const getTextColorShindo = (intensity: number) => {
  switch (Math.round(intensity)) {
    case 2:
    case 3:
    case 4:
      return "#1a1a1a";
    default:
      return "#f5f5f5";
  }
};

export const getTextColorMmi = (intensity: number) => {
  if (Math.round(intensity) <= 1) return "#f5f5f5";
  return "#1a1a1a";
};

export const pgaPgvToMmi = (pga: number, pgv: number): number => {
  if (pga <= 0 && pgv <= 0) return 1;

  let rawMmi: number;

  if (pgv > 0) {
    const logPgv = Math.log10(pgv * 100);
    rawMmi = logPgv <= 0.5 ? 2.10 * logPgv + 3.47 : 3.47 * logPgv + 2.35;
  } else {
    const logPga = Math.log10(pga * 100);
    rawMmi = logPga <= 1.15 ? 2.20 * logPga + 1.00 : 3.66 * logPga - 1.66;
  }

  return Math.min(12, Math.max(1, Math.round(rawMmi * 10) / 10));
};

export const pgvToShindo = (pgv: number) => {
  const jma = 2.68 + 1.72 * Math.log10(pgv * 100);

  if (jma < 0.5) return 0;
  if (jma < 1.5) return 1;
  if (jma < 2.5) return 2;
  if (jma < 3.5) return 3;
  if (jma < 4.5) return 4;
  if (jma < 5.0) return 5;
  if (jma < 5.5) return 6;
  if (jma < 6.0) return 7;
  if (jma < 6.5) return 8;
  return 9;
};
