// Shorter bits ("Ok.") ride along with the next sentence: fewer voice calls.
const MIN_LINE = 20;

// A sentence ends at . ! ? or … followed by a space (so "3.5" stays whole), or at a new line.
const LINE_END = /[.!?…]+["')\]]*\s+|\n+/g;

// Cuts a reply into lines Luna says one at a time, like a visual novel.
// Each line keeps its spaces, so joining the lines gives back the exact text.
export function splitSentences(text: string): string[] {
  const pieces: string[] = [];
  let start = 0;
  for (const match of text.matchAll(LINE_END)) {
    const end = match.index + match[0].length;
    pieces.push(text.slice(start, end));
    start = end;
  }
  if (start < text.length) pieces.push(text.slice(start));

  const lines: string[] = [];
  for (const piece of pieces) {
    const last = lines.length - 1;
    if (last >= 0 && (lines[last].trim().length < MIN_LINE || !piece.trim())) {
      lines[last] += piece;
    } else {
      lines.push(piece);
    }
  }
  // A tiny last bit joins the line before it.
  const last = lines.length - 1;
  if (last > 0 && lines[last].trim().length < MIN_LINE) {
    lines[last - 1] += lines.pop();
  }
  return lines;
}
