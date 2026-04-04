import { useState } from "react";

import type { Participant } from "../../lib/types";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";

type ParticipantPanelProps = {
  participants: Participant[];
  onAdd: (payload: { name: string; color_hex?: string }) => Promise<void>;
  onUpdate: (participantId: string, payload: { name?: string; color_hex?: string }) => Promise<void>;
  onDelete: (participantId: string) => Promise<void>;
};

export function ParticipantPanel({
  participants,
  onAdd,
  onUpdate,
  onDelete,
}: ParticipantPanelProps) {
  const [name, setName] = useState("");
  const [color, setColor] = useState("#0f766e");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [editingParticipantId, setEditingParticipantId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [editingColor, setEditingColor] = useState("#0f766e");

  const toErrorMessage = (error: unknown) =>
    error instanceof Error ? error.message : "Participant action failed.";

  return (
    <section className="panel stack">
      <div className="panel-header">
        <div>
          <h3 className="panel-title">Participants</h3>
          <p className="panel-copy">
            Active participants can be used in new expenses. Participants with history become
            inactive instead of being erased.
          </p>
        </div>
      </div>

      <form
        className="grid grid-2"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!name.trim()) {
            setErrorMessage("Participant name is required.");
            return;
          }

          try {
            setErrorMessage(null);
            await onAdd({ name: name.trim(), color_hex: color });
            setName("");
          } catch (error) {
            setErrorMessage(error instanceof Error ? error.message : "Unable to add participant.");
          }
        }}
      >
        <Field label="Name" error={errorMessage ?? undefined}>
          <input
            className="input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Rahul"
          />
        </Field>

        <Field label="Color">
          <input
            className="input"
            type="color"
            value={color}
            onChange={(event) => setColor(event.target.value)}
          />
        </Field>

        <Button type="submit">Add participant</Button>
      </form>

      <div className="stack">
        {participants.map((participant) => {
          const isEditing = editingParticipantId === participant.id;
          return (
            <div key={participant.id} className="participant-row">
              <div className="participant-identity">
                <span
                  className="participant-dot"
                  style={{ backgroundColor: participant.color_hex ?? "#94a3b8" }}
                />
                <div>
                  <strong>{participant.name}</strong>
                  <div className="inline-actions">
                    {participant.is_owner ? <span className="badge">Owner</span> : null}
                    {!participant.is_active ? <span className="badge">Inactive</span> : null}
                  </div>
                </div>
              </div>

              <div className="inline-actions">
                {isEditing ? (
                  <>
                    <input
                      className="input"
                      style={{ width: 180 }}
                      value={editingName}
                      onChange={(event) => setEditingName(event.target.value)}
                    />
                    <input
                      className="input"
                      type="color"
                      value={editingColor}
                      onChange={(event) => setEditingColor(event.target.value)}
                    />
                    <Button
                      variant="secondary"
                      onClick={async () => {
                        try {
                          setErrorMessage(null);
                          await onUpdate(participant.id, {
                            name: editingName.trim(),
                            color_hex: editingColor,
                          });
                          setEditingParticipantId(null);
                        } catch (error) {
                          setErrorMessage(toErrorMessage(error));
                        }
                      }}
                    >
                      Save
                    </Button>
                    <Button variant="ghost" onClick={() => setEditingParticipantId(null)}>
                      Cancel
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setEditingParticipantId(participant.id);
                        setEditingName(participant.name);
                        setEditingColor(participant.color_hex ?? "#0f766e");
                      }}
                    >
                      Edit
                    </Button>
                    {!participant.is_owner ? (
                      <Button
                        variant="danger"
                        onClick={async () => {
                          try {
                            setErrorMessage(null);
                            await onDelete(participant.id);
                          } catch (error) {
                            setErrorMessage(toErrorMessage(error));
                          }
                        }}
                      >
                        Remove
                      </Button>
                    ) : null}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
