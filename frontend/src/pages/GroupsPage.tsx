import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ApiError, formatCurrency, useApiClient } from "../lib/api";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/State";
import { Field } from "../components/ui/Field";

export function GroupsPage() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const [groupName, setGroupName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  const groupsQuery = useQuery({
    queryKey: ["groups"],
    queryFn: api.getGroups,
  });

  const createGroupMutation = useMutation({
    mutationFn: () => api.createGroup(groupName.trim()),
    onSuccess: async () => {
      setGroupName("");
      setCreateError(null);
      await queryClient.invalidateQueries({ queryKey: ["groups"] });
    },
    onError(error) {
      setCreateError(error instanceof ApiError ? error.message : "Unable to create the group.");
    },
  });

  return (
    <div className="stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="page-title">Your groups</h2>
            <p className="panel-copy">
              Create a group, invite up to three additional participants, and keep the backend in
              charge of every balance.
            </p>
          </div>
        </div>

        <form
          className="field-grid"
          onSubmit={(event) => {
            event.preventDefault();
            if (!groupName.trim()) {
              setCreateError("Group name is required.");
              return;
            }
            createGroupMutation.mutate();
          }}
        >
          <Field label="New group name" error={createError ?? undefined}>
            <input
              className="input"
              value={groupName}
              onChange={(event) => setGroupName(event.target.value)}
              placeholder="Weekend trip"
            />
          </Field>

          <Button type="submit" disabled={createGroupMutation.isPending}>
            {createGroupMutation.isPending ? "Creating..." : "Create group"}
          </Button>
        </form>
      </section>

      {groupsQuery.isLoading ? <LoadingState title="Loading your groups..." /> : null}
      {groupsQuery.isError ? (
        <ErrorState title="Could not load groups" detail={String(groupsQuery.error)} />
      ) : null}

      {!groupsQuery.isLoading && groupsQuery.data?.length === 0 ? (
        <EmptyState
          title="No groups yet"
          detail="Start with one group, then add participants and expenses from the dashboard."
        />
      ) : null}

      <div className="grid grid-3">
        {groupsQuery.data?.map((group) => (
          <Link key={group.id} to={`/groups/${group.id}`} className="group-card">
            <div>
              <p className="group-title">{group.name}</p>
              <div className="group-meta">
                <span>{group.active_participant_count} active participants</span>
                <span>{new Date(group.created_at).toLocaleDateString()}</span>
              </div>
            </div>

            <div className="grid grid-3">
              <div>
                <p className="summary-label">Total spent</p>
                <p className="summary-value">{formatCurrency(group.total_spent)}</p>
              </div>
              <div>
                <p className="summary-label">You owe</p>
                <p className="summary-value">{formatCurrency(group.you_owe)}</p>
              </div>
              <div>
                <p className="summary-label">You are owed</p>
                <p className="summary-value">{formatCurrency(group.you_are_owed)}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
