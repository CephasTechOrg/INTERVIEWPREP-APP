export const sanitizeAiText = (text: string): string => {
  if (!text) return '';
  let out = text;

  const replacements: Record<string, string> = {
    '\u2019': "'",
    '\u2018': "'",
    '\u201c': '"',
    '\u201d': '"',
    '\u2014': '--',
    '\u2013': '-',
    '\u2026': '...',
    '\u2022': '-',
    '\u00b7': '-',
    '\u00a0': ' ',
  };

  out = out
    .split('')
    .map((ch) => (replacements[ch] ? replacements[ch] : ch))
    .join('');

  // Remove non-printable characters (keep tabs/newlines and common Unicode ranges)
  // This preserves emoji and international characters
  out = out.replace(/[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]/g, '');
  out = out.replace(/\r\n/g, '\n');
  out = out.replace(/\n{3,}/g, '\n\n');

  return out.trim();
};
