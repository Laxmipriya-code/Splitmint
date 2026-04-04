import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { ApiError, useApiClient } from "../../lib/api";
import type { MintSenseParseResponse, MintSenseSummary, Participant } from "../../lib/types";
import { Button } from "../ui/Button";
import { EmptyState, ErrorState } from "../ui/State";

type MintSensePanelProps = {
  groupId: string;
  participants: Participant[];
  onApplyDraft: (draft: MintSenseParseResponse) => void;
};

export function MintSensePanel({
  groupId,
  participants,
  onApplyDraft,
}: MintSensePanelProps) {
  const api = useApiClient();
  const [text, setText] = useState("");
  const [draft, setDraft] = useState<MintSenseParseResponse | null>(null);
  const [summary, setSummary] = useState<MintSenseSummary | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const parseMutation = useMutation({
    mutationFn: () => api.parseExpense({ group_id: groupId, text }),
    onSuccess(data) {
      setDraft(data);
      setErrorMessage(null);
    },
    onError(error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Unable to parse the expense.");
    },
  });

  const summaryMutation = useMutation({
    mutationFn: () => api.summarizeGroup(groupId),
    onSuccess(data) {
      setSummary(data);
      setErrorMessage(null);
    },
    onError(error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Unable to summarize the group.");
    },
  });

  return (
    <section className="panel stack">
      <div className="panel-header">
        <div>
          <h3 className="panel-title">MintSense</h3>
          <p className="panel-copy">
            Parse natural language into a draft, then review before it reaches the expense form.
          </p>
        </div>
      </div>

      {errorMessage ? <ErrorState title="MintSense issue" detail={errorMessage} /> : null}

      <textarea
        className="textarea"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={`Example: I paid 1200 for dinner with ${participants
          .filter((participant) => !participant.is_owner)
          .map((participant) => participant.name)
          .join(" and ")}`}
      />

      <div className="button-row">
        <Button
          onClick={() => {
            if (text.trim().length < 3) {
              setErrorMessage("Enter at least 3 characters before parsing.");
              return;
            }
            parseMutation.mutate();
          }}
          disabled={parseMutation.isPending}
        >
          {parseMutation.isPending ? "Parsing..." : "Parse expense"}
        </Button>
        <Button
          variant="secondary"
          onClick={() => summaryMutation.mutate()}
          disabled={summaryMutation.isPending}
        >
          {summaryMutation.isPending ? "Generating..." : "Generate group summary"}
        </Button>
      </div>

      {draft ? (
        <div className="notice stack">
          <strong>Draft result</strong>
          <div>{draft.draft.description}</div>
          <div className="tiny">
            Amount: {draft.draft.amount ?? "unknown"} | Payer: {draft.draft.payer_name ?? "unknown"} |
            Participants: {draft.draft.participant_names.join(", ") || "unknown"}
          </div>
          {draft.validation_issues.length ? (
            <ul>
              {draft.validation_issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          ) : null}
          <Button variant="ghost" onClick={() => onApplyDraft(draft)}>
            Use draft in expense form
          </Button>
        </div>
      ) : (
        <EmptyState title="No draft yet" detail="Parse a sentence to get a structured suggestion." />
      )}

      {summary ? (
        <div className="notice stack">
          <strong>Group summary</strong>
          <div>{summary.summary}</div>
          <ul>
            {summary.highlights.map((highlight) => (
              <li key={highlight}>{highlight}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
