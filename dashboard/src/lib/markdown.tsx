import { Fragment, type ReactNode } from "react";
import { highlight } from "@/lib/syntax";
import { uid } from "@/lib/id";

const HEAD_TAGS: Record<number, "h1" | "h2" | "h3" | "h4" | "h5" | "h6"> = {
  1: "h1", 2: "h2", 3: "h3", 4: "h4", 5: "h5", 6: "h6",
};

/** Renderiza texto markdown simples como React (sem innerHTML inseguro). */
export function renderMarkdown(text: string): ReactNode {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // código em bloco ```lang ```
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const buf: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith("```")) {
        buf.push(lines[i]);
        i += 1;
      }
      i += 1; // pula fechamento
      blocks.push(<pre key={uid("pre")} dangerouslySetInnerHTML={{ __html: highlight(buf.join("\n"), lang) }} />);
      continue;
    }

    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      const level = h[1].length;
      const Tag = HEAD_TAGS[level];
      blocks.push(<Tag key={uid("h")}>{parseInline(h[2])}</Tag>);
      i += 1;
      continue;
    }

    // parágrafo seção — agrupa linhas consecutivas de texto
    let listMode: "ul" | "ol" | null = null;
    const items: ReactNode[] = [];
    while (i < lines.length && lines[i].trim() !== "" && !lines[i].match(/^#{1,6}\s/) && !lines[i].startsWith("```")) {
      const raw = lines[i];
      const ul = raw.match(/^\s*([-*+])\s+(.*)$/);
      const ol = raw.match(/^\s*\d+[.)]\s+(.*)$/);
      if (ul || ol) {
        if (listMode !== (ul ? "ul" : "ol")) {
          if (items.length) blocks.push(<p key={uid("p")}>{items}</p>);
          items.length = 0;
          listMode = ul ? "ul" : "ol";
        }
        items.push(<li key={uid("li")}>{parseInline((ul ?? ol)![2])}</li>);
        i += 1;
        continue;
      }
      if (listMode) {
        blocks.push(<p key={uid("pl")}>{items}</p>);
        items.length = 0;
        listMode = null;
      }
      items.push(<Fragment key={uid("frag")}>{parseInline(raw)}<br /></Fragment>);
      i += 1;
    }
    if (i < lines.length && lines[i].trim() === "") i += 1;
    if (listMode === "ul") blocks.push(<ul key={uid("ul")}>{items}</ul>);
    else if (listMode === "ol") blocks.push(<ol key={uid("ol")}>{items}</ol>);
    else if (items.length) blocks.push(<p key={uid("p")}>{items}</p>);
  }

  return <Fragment>{blocks}</Fragment>;
}

/** Itens inline: **negrito**, `código`, links. */
function parseInline(line: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(line)) !== null) {
    if (m.index > last) out.push(line.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) {
      out.push(<strong key={uid("b")}>{tok.slice(2, -2)}</strong>);
    } else if (tok.startsWith("`")) {
      out.push(<code key={uid("c")}>{tok.slice(1, -1)}</code>);
    } else {
      const cap = tok.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (cap) {
        out.push(
          <a key={uid("a")} href={cap[2]} onClick={(e) => e.preventDefault()}>
            {cap[1]}
          </a>,
        );
      } else {
        out.push(tok);
      }
    }
    last = m.index + tok.length;
  }
  if (last < line.length) out.push(line.slice(last));
  return out;
}