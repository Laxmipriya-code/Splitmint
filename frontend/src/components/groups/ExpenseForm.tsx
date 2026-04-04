/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";

import type { Expense, ExpensePayload, Participant } from "../../lib/types";
import { Button } from "../ui/Button";
import { Field } from "../ui/Field";
import { ErrorState } from "../ui/State";

type ExpenseFormProps = {
  groupId: string;
  participants: Participant[];
  initialExpense?: Expense | null;
  onCancelEdit: () => void;
  onSubmit: (payload: ExpensePayload, expenseId?: string) => Promise<void>;
};

type ExpenseFormValues = {
  amount: string;
  description: string;
  category: string;
  date: string;
  payer_id: string;
  split_mode: "equal" | "custom" | "percentage";
};

function decimalSum(values: string[]) {
  return values.reduce((total, current) => total + Number.parseFloat(current || "0"), 0);
}

export function ExpenseForm({
  groupId,
  participants,
  initialExpense,
  onCancelEdit,
  onSubmit,
}: ExpenseFormProps) {
  const isEditing = Boolean(initialExpense?.id);
  const [selectedParticipantIds, setSelectedParticipantIds] = useState<string[]>([]);
  const [splitValues, setSplitValues] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const allowedParticipants = useMemo(
    () =>
      participants.filter(
        (participant) =>
          participant.is_active ||
          initialExpense?.payer_id === participant.id ||
          initialExpense?.splits.some((split) => split.participant_id === participant.id),
      ),
    [initialExpense, participants],
  );

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { isSubmitting },
  } = useForm<ExpenseFormValues>({
    defaultValues: {
      amount: "",
      description: "",
      category: "",
      date: new Date().toISOString().slice(0, 10),
      payer_id: "",
      split_mode: "equal",
    },
  });

  const splitMode = useWatch({ control, name: "split_mode" });

  useEffect(() => {
    if (initialExpense) {
      reset({
        amount: initialExpense.amount,
        description: initialExpense.description,
        category: initialExpense.category ?? "",
        date: initialExpense.date,
        payer_id: initialExpense.payer_id,
        split_mode: initialExpense.split_mode,
      });
      setSelectedParticipantIds(initialExpense.splits.map((split) => split.participant_id));
      setSplitValues(
        Object.fromEntries(
          initialExpense.splits.map((split) => [
            split.participant_id,
            split.input_value ?? split.owed_amount,
          ]),
        ),
      );
      return;
    }

    const ownerParticipant = allowedParticipants.find((participant) => participant.is_owner);
    reset({
      amount: "",
      description: "",
      category: "",
      date: new Date().toISOString().slice(0, 10),
      payer_id: ownerParticipant?.id ?? "",
      split_mode: "equal",
    });
    setSelectedParticipantIds(ownerParticipant ? [ownerParticipant.id] : []);
    setSplitValues({});
  }, [allowedParticipants, initialExpense, reset]);

  const submitHandler = handleSubmit(async (values) => {
    if (!selectedParticipantIds.length) {
      setFormError("Choose at least one participant for the expense.");
      return;
    }
    if (!values.payer_id) {
      setFormError("Choose a payer.");
      return;
    }

    const splits =
      values.split_mode === "equal"
        ? []
        : selectedParticipantIds.map((participantId) => ({
            participant_id: participantId,
            value: splitValues[participantId] ?? "",
          }));

    if (values.split_mode === "custom") {
      const total = decimalSum(splits.map((split) => split.value));
      if (Math.abs(total - Number.parseFloat(values.amount || "0")) > 0.001) {
        setFormError("Custom split values must add up to the exact expense amount.");
        return;
      }
    }

    if (values.split_mode === "percentage") {
      const total = decimalSum(splits.map((split) => split.value));
      if (Math.abs(total - 100) > 0.0001) {
        setFormError("Percentage split values must total exactly 100.0000.");
        return;
      }
    }

    try {
      setFormError(null);
      await onSubmit(
        {
          group_id: groupId,
          amount: values.amount,
          description: values.description.trim(),
          category: values.category.trim() ? values.category.trim() : null,
          date: values.date,
          payer_id: values.payer_id,
          participants: selectedParticipantIds,
          split_mode: values.split_mode,
          splits,
        },
        initialExpense?.id,
      );
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to save the expense.");
    }
  });

  return (
    <section className="panel stack">
      <div className="panel-header">
        <div>
          <h3 className="panel-title">
            {isEditing ? "Edit expense" : "Add expense"}
          </h3>
          <p className="panel-copy">
            Splits are normalized on the backend. The client only sends raw inputs.
          </p>
        </div>

        {isEditing ? (
          <Button variant="ghost" onClick={onCancelEdit}>
            Cancel edit
          </Button>
        ) : null}
      </div>

      {formError ? <ErrorState title="Expense form issue" detail={formError} /> : null}

      <form className="stack" onSubmit={submitHandler}>
        <div className="grid grid-2">
          <Field label="Amount">
            <input className="input" inputMode="decimal" placeholder="1200.00" {...register("amount")} />
          </Field>
          <Field label="Date">
            <input className="input" type="date" {...register("date")} />
          </Field>
          <Field label="Description">
            <input className="input" placeholder="Dinner at Candolim" {...register("description")} />
          </Field>
          <Field label="Category">
            <input className="input" placeholder="Food & Dining" {...register("category")} />
          </Field>
          <Field label="Payer">
            <select className="select" {...register("payer_id")}>
              <option value="">Select payer</option>
              {allowedParticipants.map((participant) => (
                <option key={participant.id} value={participant.id}>
                  {participant.name}
                  {!participant.is_active ? " (inactive)" : ""}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Split mode">
            <select className="select" {...register("split_mode")}>
              <option value="equal">Equal</option>
              <option value="custom">Custom amount</option>
              <option value="percentage">Percentage</option>
            </select>
          </Field>
        </div>

        <div className="field">
          <label>Participants</label>
          <div className="checkbox-grid">
            {allowedParticipants.map((participant) => {
              const selected = selectedParticipantIds.includes(participant.id);
              return (
                <label key={participant.id} className="checkbox-card">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={(event) => {
                      setSelectedParticipantIds((currentValue) => {
                        if (event.target.checked) {
                          return [...currentValue, participant.id];
                        }
                        return currentValue.filter((value) => value !== participant.id);
                      });
                    }}
                  />
                  <span>{participant.name}</span>
                </label>
              );
            })}
          </div>
        </div>

        {splitMode !== "equal" ? (
          <div className="stack">
            {selectedParticipantIds.map((participantId) => {
              const participant = allowedParticipants.find((item) => item.id === participantId);
              return (
                <Field
                  key={participantId}
                  label={`${participant?.name ?? "Participant"} ${splitMode === "custom" ? "amount" : "percentage"}`}
                >
                  <input
                    className="input"
                    inputMode="decimal"
                    value={splitValues[participantId] ?? ""}
                    onChange={(event) =>
                      setSplitValues((currentValue) => ({
                        ...currentValue,
                        [participantId]: event.target.value,
                      }))
                    }
                    placeholder={splitMode === "custom" ? "0.00" : "0.0000"}
                  />
                </Field>
              );
            })}
          </div>
        ) : null}

        <div className="button-row">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : isEditing ? "Save changes" : "Add expense"}
          </Button>
          {isEditing ? (
            <Button variant="ghost" onClick={onCancelEdit}>
              Stop editing
            </Button>
          ) : null}
        </div>
      </form>
    </section>
  );
}
