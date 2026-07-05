import type { Citation } from "../../types/contracts";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) {
    return (
      <p className="citation-list__empty">
        No protocol rule was needed: the response was routine, so MILA didn't go looking for one.
      </p>
    );
  }

  return (
    <ul className="citation-list">
      {citations.map((citation, index) => (
        <li key={`${citation.doc_id}-${index}`}>
          <details>
            <summary>
              {citation.article}, {citation.doc_id.replace(/_/g, " ")}
              {typeof citation.score === "number" ? ` (score ${citation.score.toFixed(2)})` : ""}
            </summary>
            <p className="citation-list__meta">
              Page {citation.page} · rule type: {citation.rule_type}
            </p>
            <blockquote>{citation.quote}</blockquote>
          </details>
        </li>
      ))}
    </ul>
  );
}
