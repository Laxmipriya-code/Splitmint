import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { ExpenseForm } from "../components/groups/ExpenseForm";
import { MintSensePanel } from "../components/groups/MintSensePanel";
import { ParticipantPanel } from "../components/groups/ParticipantPanel";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/State";
import { ApiError, formatCurrency, useApiClient } from "../lib/api";
import type {
  Expense,
  ExpenseFilters,
  ExpensePayload,
  MintSenseParseResponse,
} from "../lib/types";

function isPositive(value: string) {
  return Number.parseFloat(value) > 0;
}

export function GroupDetailPage() {
  const navigate = useNavigate();
  const { groupId = "" } = useParams();
  const api = useApiClient();
  const queryClient = useQueryClient();
  const [editingGroupName, setEditingGroupName] = useState("");
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [groupError, setGroupError] = useState<string | null>(null);
  const [participantError, setParticipantError] = useState<string | null>(null);
  const [expenseError, setExpenseError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ExpenseFilters>({
    page: 1,
    size: 20,
  });

  const groupQuery = useQuery({
    queryKey: ["group", groupId],
    queryFn: () => api.getGroup(groupId),
    enabled: Boolean(groupId),
  });

  const expensesQuery = useQuery({
    queryKey: ["expenses", groupId, filters],
    queryFn: () => api.getExpenses(groupId, filters),
    enabled: Boolean(groupId),
  });

  const invalidateGroupScope = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["groups"] }),
      queryClient.invalidateQueries({ queryKey: ["group", groupId] }),
      queryClient.invalidateQueries({ queryKey: ["expenses", groupId] }),
    ]);
  };

  const proposedGroupName = editingGroupName.trim();

  const updateGroupMutation = useMutation({
    mutationFn: () => api.updateGroup(groupId, proposedGroupName || groupQuery.data?.name || ""),
    onSuccess: async () => {
      setGroupError(null);
      setEditingGroupName("");
      await invalidateGroupScope();
    },
    onError(error) {
      setGroupError(error instanceof ApiError ? error.message : "Unable to update the group.");
    },
  });

  const deleteGroupMutation = useMutation({
    mutationFn: () => api.deleteGroup(groupId),
    onSuccess: async () => {
      setGroupError(null);
      await queryClient.invalidateQueries({ queryKey: ["groups"] });
      navigate("/groups", { replace: true });
    },
    onError(error) {
      setGroupError(error instanceof ApiError ? error.message : "Unable to delete the group.");
    },
  });

  const participantMutation = useMutation({
    mutationFn: async ({
      type,
      participantId,
      payload,
    }: {
      type: "add" | "update" | "delete";
      participantId?: string;
      payload?: { name?: string; color_hex?: string };
    }) => {
      if (type === "add") {
        if (!payload?.name) {
          throw new Error("Participant name is required.");
        }
        return api.addParticipant(groupId, {
          name: payload.name,
          color_hex: payload.color_hex,
        });
      }
      if (type === "update" && participantId) {
        return api.updateParticipant(participantId, payload ?? {});
      }
      if (type === "delete" && participantId) {
        return api.deleteParticipant(participantId);
      }
      throw new Error("Unknown participant action");
    },
    onSuccess: async () => {
      setParticipantError(null);
      await invalidateGroupScope();
    },
    onError(error) {
      setParticipantError(
        error instanceof ApiError ? error.message : "Unable to complete participant action.",
      );
    },
  });

  const expenseMutation = useMutation({
    mutationFn: async ({
      payload,
      expenseId,
    }: {
      payload: ExpensePayload;
      expenseId?: string;
    }) => {
      if (expenseId) {
        return api.updateExpense(expenseId, payload);
      }
      return api.createExpense(payload);
    },
    onSuccess: async () => {
      setExpenseError(null);
      setEditingExpense(null);
      await invalidateGroupScope();
    },
    onError(error) {
      setExpenseError(error instanceof ApiError ? error.message : "Unable to save expense changes.");
    },
  });

  const deleteExpenseMutation = useMutation({
    mutationFn: (expenseId: string) => api.deleteExpense(expenseId),
    onSuccess: async () => {
      setExpenseError(null);
      await invalidateGroupScope();
    },
    onError(error) {
      setExpenseError(error instanceof ApiError ? error.message : "Unable to delete expense.");
    },
  });

  const group = groupQuery.data;

  if (groupQuery.isLoading) {
    return <LoadingState title="Loading group dashboard..." />;
  }

  if (groupQuery.isError || !group) {
    return <ErrorState title="Could not load the group" detail={String(groupQuery.error)} />;
  }

  const activeParticipants = group.participants.filter((participant) => participant.is_active);
  const totalPages = expensesQuery.data ? Math.max(1, Math.ceil(expensesQuery.data.total / expensesQuery.data.size)) : 1;

  return (
    <div className="stack">
      <section className="panel stack">
        <div className="panel-header">
          <div>
            <h2 className="page-title">{group.name}</h2>
            <p className="panel-copy">
              Keep the server as the source of truth for totals, shares, balances, and settlements.
            </p>
          </div>
          <div className="inline-actions">
            <Button
              variant="danger"
              onClick={() => {
                if (window.confirm("Delete this group and all linked expenses?")) {
                  deleteGroupMutation.mutate();
                }
              }}
            >
              Delete group
            </Button>
          </div>
        </div>

        {groupError ? <ErrorState title="Group update failed" detail={groupError} /> : null}

        <form
          className="grid grid-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (!(proposedGroupName || group.name)) {
              setGroupError("Group name is required.");
              return;
            }
            updateGroupMutation.mutate();
          }}
        >
          <input
            className="input"
            value={editingGroupName || group.name}
            onChange={(event) => setEditingGroupName(event.target.value)}
          />
          <Button type="submit" disabled={updateGroupMutation.isPending}>
            {updateGroupMutation.isPending ? "Saving..." : "Rename group"}
          </Button>
        </form>
      </section>

      <div className="grid grid-3">
        <div className="summary-card">
          <p className="summary-label">Total spent</p>
          <p className="summary-value">{formatCurrency(group.summary.total_spent)}</p>
        </div>
        <div className="summary-card">
          <p className="summary-label">You owe</p>
          <p className="summary-value">{formatCurrency(group.summary.you_owe)}</p>
        </div>
        <div className="summary-card">
          <p className="summary-label">You are owed</p>
          <p className="summary-value">{formatCurrency(group.summary.you_are_owed)}</p>
        </div>
      </div>

      <div className="grid grid-main">
        <div className="stack">
          {expenseError ? <ErrorState title="Expense action failed" detail={expenseError} /> : null}

          <ExpenseForm
            groupId={group.id}
            participants={group.participants}
            initialExpense={editingExpense}
            onCancelEdit={() => setEditingExpense(null)}
            onSubmit={async (payload, expenseId) => {
              await expenseMutation.mutateAsync({ payload, expenseId });
            }}
          />

          <section className="panel stack">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">History and filters</h3>
                <p className="panel-copy">
                  Search by text, narrow by participant or date, and let the backend paginate the
                  history.
                </p>
              </div>
            </div>

            <div className="grid grid-3">
              <input
                className="input"
                placeholder="Search description or category"
                value={filters.search ?? ""}
                onChange={(event) =>
                  setFilters((currentValue) => ({
                    ...currentValue,
                    page: 1,
                    search: event.target.value,
                  }))
                }
              />
              <select
                className="select"
                value={filters.participantId ?? ""}
                onChange={(event) =>
                  setFilters((currentValue) => ({
                    ...currentValue,
                    page: 1,
                    participantId: event.target.value || undefined,
                  }))
                }
              >
                <option value="">All participants</option>
                {group.participants.map((participant) => (
                  <option key={participant.id} value={participant.id}>
                    {participant.name}
                  </option>
                ))}
              </select>
              <input
                className="input"
                type="date"
                value={filters.dateFrom ?? ""}
                onChange={(event) =>
                  setFilters((currentValue) => ({
                    ...currentValue,
                    page: 1,
                    dateFrom: event.target.value || undefined,
                  }))
                }
              />
              <input
                className="input"
                type="date"
                value={filters.dateTo ?? ""}
                onChange={(event) =>
                  setFilters((currentValue) => ({
                    ...currentValue,
                    page: 1,
                    dateTo: event.target.value || undefined,
                  }))
                }
              />
              <input
                className="input"
                placeholder="Min amount"
                value={filters.minAmount ?? ""}
                onChange={(event) =>
                  setFilters((currentValue) => ({
                    ...currentValue,
                    page: 1,
                    minAmount: event.target.value || undefined,
                  }))
                }
              />
              <input
                className="input"
                placeholder="Max amount"
                value={filters.maxAmount ?? ""}
                onChange={(event) =>
                  setFilters((currentValue) => ({
                    ...currentValue,
                    page: 1,
                    maxAmount: event.target.value || undefined,
                  }))
                }
              />
            </div>

            {expensesQuery.isLoading ? <LoadingState title="Loading expenses..." /> : null}
            {expensesQuery.isError ? (
              <ErrorState title="Could not load expenses" detail={String(expensesQuery.error)} />
            ) : null}

            {expensesQuery.data && expensesQuery.data.items.length === 0 ? (
              <EmptyState
                title="No expenses match these filters"
                detail="Add a new expense or loosen the filters."
              />
            ) : null}

            {expensesQuery.data?.items.length ? (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Payer</th>
                      <th>Amount</th>
                      <th>Split</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {expensesQuery.data.items.map((expense) => (
                      <tr key={expense.id}>
                        <td>{new Date(expense.date).toLocaleDateString()}</td>
                        <td>
                          <strong>{expense.description}</strong>
                          <div className="tiny muted">{expense.category ?? "Uncategorized"}</div>
                        </td>
                        <td>{expense.payer_name}</td>
                        <td>{formatCurrency(expense.amount)}</td>
                        <td>
                          <div className="tiny">
                            {expense.splits.map((split) => `${split.participant_name}: ${split.owed_amount}`).join(" · ")}
                          </div>
                        </td>
                        <td>
                          <div className="inline-actions">
                            <Button variant="ghost" onClick={() => setEditingExpense(expense)}>
                              Edit
                            </Button>
                            <Button
                              variant="danger"
                              onClick={() => deleteExpenseMutation.mutate(expense.id)}
                            >
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            <div className="inline-actions">
              <Button
                variant="ghost"
                disabled={(filters.page ?? 1) <= 1}
                onClick={() =>
                  setFilters((currentValue) => ({
                    ...currentValue,
                    page: Math.max(1, (currentValue.page ?? 1) - 1),
                  }))
                }
              >
                Previous
              </Button>
              <span className="badge">
                Page {filters.page ?? 1} of {totalPages}
              </span>
              <Button
                variant="ghost"
                disabled={(filters.page ?? 1) >= totalPages}
                onClick={() =>
                  setFilters((currentValue) => ({
                    ...currentValue,
                    page: Math.min(totalPages, (currentValue.page ?? 1) + 1),
                  }))
                }
              >
                Next
              </Button>
            </div>
          </section>
        </div>

        <div className="stack">
          {participantError ? (
            <ErrorState title="Participant action failed" detail={participantError} />
          ) : null}

          <ParticipantPanel
            participants={group.participants}
            onAdd={async (payload) => {
              await participantMutation.mutateAsync({ type: "add", payload });
            }}
            onUpdate={async (participantId, payload) => {
              await participantMutation.mutateAsync({ type: "update", participantId, payload });
            }}
            onDelete={async (participantId) => {
              if (window.confirm("Remove this participant from future expenses?")) {
                await participantMutation.mutateAsync({ type: "delete", participantId });
              }
            }}
          />

          <MintSensePanel
            groupId={group.id}
            participants={activeParticipants}
            onApplyDraft={(draft: MintSenseParseResponse) => {
              const resolvedIds = draft.resolved_participants.map((participant) => participant.participant_id);
              const payerId =
                draft.resolved_payer?.participant_id ?? group.owner_participant_id;
              const expenseToEdit: Expense = {
                id: editingExpense?.id ?? "",
                group_id: group.id,
                payer_id: payerId,
                payer_name: draft.resolved_payer?.participant_name ?? "Owner",
                amount: draft.draft.amount ?? "0.00",
                description: draft.draft.description ?? "",
                category: draft.draft.category ?? null,
                split_mode: draft.draft.split_mode ?? "equal",
                date: draft.draft.date ?? new Date().toISOString().slice(0, 10),
                splits: resolvedIds.map((participantId, position) => ({
                  participant_id: participantId,
                  participant_name:
                    draft.resolved_participants.find((item) => item.participant_id === participantId)
                      ?.participant_name ?? "",
                  owed_amount: "0.00",
                  input_value:
                    draft.draft.splits.find(
                      (split) =>
                        split.participant_name ===
                        draft.resolved_participants.find(
                          (item) => item.participant_id === participantId,
                        )?.participant_name,
                    )?.value ?? null,
                  position,
                })),
                created_at: "",
                updated_at: "",
                version: 1,
              };
              setEditingExpense(expenseToEdit);
            }}
          />

          <section className="panel stack">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Balances</h3>
                <p className="panel-copy">
                  Positive balances mean the participant should receive money. Negative balances
                  mean they owe.
                </p>
              </div>
            </div>

            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Participant</th>
                    <th>Paid</th>
                    <th>Share</th>
                    <th>Net</th>
                  </tr>
                </thead>
                <tbody>
                  {group.summary.balances.map((balance) => (
                    <tr key={balance.participant_id}>
                      <td>
                        <strong>{balance.name}</strong>
                        <div className="tiny muted">
                          {balance.is_owner ? "Owner" : balance.is_active ? "Active" : "Inactive"}
                        </div>
                      </td>
                      <td>{formatCurrency(balance.paid_total)}</td>
                      <td>{formatCurrency(balance.owed_total)}</td>
                      <td className={isPositive(balance.net_balance) ? "ledger-positive" : balance.net_balance.startsWith("-") ? "ledger-negative" : ""}>
                        {formatCurrency(balance.net_balance)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel stack">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Settlement suggestions</h3>
                <p className="panel-copy">
                  These are deterministic suggestions generated on the backend from the net
                  balances.
                </p>
              </div>
            </div>

            {group.summary.settlements.length ? (
              <div className="stack">
                {group.summary.settlements.map((settlement) => (
                  <div key={`${settlement.from_participant_id}-${settlement.to_participant_id}`} className="notice">
                    {settlement.from_name} pays {settlement.to_name}{" "}
                    <strong>{formatCurrency(settlement.amount)}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No settlements needed"
                detail="The group is currently balanced."
              />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
