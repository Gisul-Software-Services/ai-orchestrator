"use client";

import { useMemo, type ReactNode } from "react";

const KW =
  /^(and|as|assert|async|await|break|class|continue|def|del|elif|else|except|False|finally|for|from|global|if|import|in|is|lambda|None|nonlocal|not|or|pass|raise|return|True|try|while|with|yield)\b/;

function highlightPython(code: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let i = 0;
  const len = code.length;

  const pushText = (s: string, cls: string) => {
    if (!s) return;
    parts.push(
      <span key={parts.length} className={cls}>
        {s}
      </span>
    );
  };

  while (i < len) {
    const ch = code[i];
    if (ch === "#") {
      const end = code.indexOf("\n", i);
      const line = end === -1 ? code.slice(i) : code.slice(i, end + 1);
      pushText(line, "text-zinc-500 italic");
      i += line.length;
      continue;
    }
    if (ch === "'" || ch === '"') {
      const quote = ch;
      let j = i + 1;
      let escaped = false;
      while (j < len) {
        if (escaped) {
          escaped = false;
          j += 1;
          continue;
        }
        if (code[j] === "\\") {
          escaped = true;
          j += 1;
          continue;
        }
        if (code[j] === quote) {
          j += 1;
          break;
        }
        j += 1;
      }
      pushText(code.slice(i, j), "text-emerald-400/90");
      i = j;
      continue;
    }
    const slice = code.slice(i);
    const mKw = slice.match(KW);
    if (mKw) {
      pushText(mKw[0], "text-violet-400");
      i += mKw[0].length;
      continue;
    }
    const mNum = slice.match(/^\d[\d_]*\.?[\d_]*/);
    if (mNum) {
      pushText(mNum[0], "text-amber-400/90");
      i += mNum[0].length;
      continue;
    }
    let j = i + 1;
    while (j < len) {
      const c = code[j];
      if (c === "#" || c === "'" || c === '"') break;
      const rest = code.slice(j);
      if (/^\d/.test(rest)) break;
      if (rest.match(KW)) break;
      j += 1;
    }
    pushText(code.slice(i, j), "text-zinc-200");
    i = j;
  }

  return parts;
}

export function CodeBlock({
  code,
  language = "text",
}: {
  code: string;
  language?: string;
}) {
  const nodes = useMemo(() => {
    if (language === "python") return highlightPython(code);
    return [<span key={0}>{code}</span>];
  }, [code, language]);

  return (
    <pre className="overflow-x-auto rounded-lg border border-zinc-200 bg-zinc-50 p-3.5 font-mono text-[0.8125rem] leading-relaxed text-zinc-800 shadow-inner dark:border-zinc-800/90 dark:bg-zinc-950/70 dark:text-zinc-200">
      <code className={`block whitespace-pre language-${language}`}>{nodes}</code>
    </pre>
  );
}
