import chinese from "./ui.zh.json";

export type Locale = "en" | "zh";

export function translator(locale: Locale) {
  return (text: string): string => {
    if (locale === "en") return text;
    const translated = (chinese as Record<string, string>)[text];
    if (translated === undefined)
      throw new Error(`Missing Chinese UI text: ${text}`);
    return translated;
  };
}
