import { useState } from "react";
import { api } from "../../api";
import type { MonitoringBrief } from "../../types/contracts";
import { formatDateTime } from "../../lib/format";

// No auth in scope for this demo — a plausible synthetic default, still a real editable field.
const DEFAULT_VALIDATOR = "Dr. Amélie Laurent (biologist)";

export function ValidateBriefButton({
  brief,
  onValidated,
}: {
  brief: MonitoringBrief;
  onValidated: (brief: MonitoringBrief) => void;
}) {
  const [validatedBy, setValidatedBy] = useState(DEFAULT_VALIDATOR);
  const [submitting, setSubmitting] = useState(false);

  if (brief.validated_by) {
    // A rejection also sets validated_by/validated_at (see db/repo.reject_brief) and prepends a
    // "[REJECTED …]" marker to recommended_action. There is no dedicated status field on the
    // contract, so detect rejection from that prefix and render a distinct danger-toned state.
    const rejected = brief.recommended_action.startsWith("[REJECTED");
    if (rejected) {
      return (
        <p className="validate-brief__done validate-brief__done--rejected" role="alert">
          Rejected by {brief.validated_by} on{" "}
          {formatDateTime(brief.validated_at ?? brief.created_at)}.
        </p>
      );
    }
    return (
      <p className="validate-brief__done">
        Validated by {brief.validated_by} on {formatDateTime(brief.validated_at ?? brief.created_at)}.
      </p>
    );
  }

  async function handleValidate() {
    setSubmitting(true);
    try {
      const updated = await api.validateBrief(brief.id, validatedBy);
      onValidated(updated);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="validate-brief">
      <label className="validate-brief__field">
        Validated by
        <input
          type="text"
          value={validatedBy}
          onChange={(event) => setValidatedBy(event.target.value)}
        />
      </label>
      <button
        type="button"
        className="button button--primary"
        onClick={() => void handleValidate()}
        disabled={submitting || validatedBy.trim().length === 0}
      >
        {submitting ? "Validating…" : "Validate brief"}
      </button>
    </div>
  );
}
