import type { ReactNode } from "react";
import { terms } from "../../lib/glossary";

// A lightweight plain-language affordance: renders text with a dotted underline and a native
// tooltip drawn from the glossary, so a non-biologist can hover any clinical term (E2, OHSS,
// PCOS…) and read what it means. Falls back gracefully if the term is unknown.
export function Term({ name, children }: { name: string; children?: ReactNode }) {
  const tooltip = terms[name];
  const content = children ?? name;
  if (!tooltip) return <>{content}</>;
  return (
    <abbr className="term" title={tooltip}>
      {content}
    </abbr>
  );
}
