import { useMemo } from "react";

import { normalizeAuthSession, useAuth } from "./auth";
import type {
  ApiFailure,
  ApiSuccess,
  BackendAuthSession,
  Expense,
  ExpenseFilters,
  ExpenseList,
  ExpensePayload,
  Group,
  GroupListItem,
  MintSenseParseResponse,
  MintSenseSummary,
  Participant,
} from "./types";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/+$/, "");

function extractErrorMessage(payload: ApiFailure["error"] | undefined) {
  const validationErrors = payload?.details?.errors;
  if (Array.isArray(validationErrors) && validationErrors.length > 0) {
    const firstError = validationErrors[0];
    if (
      firstError &&
      typeof firstError === "object" &&
      "message" in firstError &&
      typeof firstError.message === "string"
    ) {
      return firstError.message;
    }
  }
  return payload?.message ?? "Request failed";
}

export class ApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown>;

  constructor(status: number, payload: ApiFailure["error"] | undefined) {
    super(extractErrorMessage(payload));
    this.status = status;
    this.code = payload?.code ?? "request_failed";
    this.details = payload?.details;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  const rawText = await response.text();
  if (!rawText) {
    return undefined as T;
  }

  let payload: ApiSuccess<T> | ApiFailure;
  try {
    payload = JSON.parse(rawText) as ApiSuccess<T> | ApiFailure;
  } catch {
    throw new ApiError(response.status, {
      code: "invalid_response",
      message: "The server returned an unreadable response.",
    });
  }

  if (!response.ok || payload.status === "error") {
    throw new ApiError(response.status, payload.status === "error" ? payload.error : undefined);
  }
  return payload.data;
}

function buildQuery(filters: ExpenseFilters & { groupId?: string }) {
  const searchParams = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    const queryKey = key.replace(/[A-Z]/g, (match) => `_${match.toLowerCase()}`);
    searchParams.set(queryKey, String(value));
  });
  return searchParams.toString();
}

export function useApiClient() {
  const { session, setSession, clearSession } = useAuth();

  const client = useMemo(() => {
    const request = async <T,>(
      path: string,
      init: RequestInit = {},
      allowRefresh = true,
    ): Promise<T> => {
      const headers = new Headers(init.headers);
      headers.set("Accept", "application/json");
      if (!(init.body instanceof FormData)) {
        headers.set("Content-Type", "application/json");
      }

      if (session?.accessToken) {
        headers.set("Authorization", `Bearer ${session.accessToken}`);
      }

      let response: Response;
      try {
        response = await fetch(`${API_BASE_URL}${path}`, {
          ...init,
          headers,
        });
      } catch {
        throw new ApiError(0, {
          code: "network_error",
          message: "Unable to reach the API. Verify backend connectivity and API URL.",
        });
      }

      if (
        response.status === 401 &&
        allowRefresh &&
        session?.refreshToken &&
        !path.startsWith("/auth/")
      ) {
        try {
          const refreshed = await request<BackendAuthSession>(
            "/auth/refresh",
            {
              method: "POST",
              body: JSON.stringify({ refresh_token: session.refreshToken }),
            },
            false,
          );
          const normalized = normalizeAuthSession(refreshed);
          setSession(normalized);
          return request<T>(path, init, false);
        } catch {
          clearSession();
          throw new ApiError(401, {
            code: "unauthorized",
            message: "Your session expired. Please log in again.",
          });
        }
      }

      return parseResponse<T>(response);
    };

    return {
      async register(payload: { email: string; password: string; display_name?: string }) {
        const data = await request<BackendAuthSession>("/auth/register", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        const normalized = normalizeAuthSession(data);
        setSession(normalized);
        return normalized;
      },
      async login(payload: { email: string; password: string }) {
        const data = await request<BackendAuthSession>("/auth/login", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        const normalized = normalizeAuthSession(data);
        setSession(normalized);
        return normalized;
      },
      async logout() {
        if (session?.refreshToken) {
          try {
            await request<{ logged_out: boolean }>("/auth/logout", {
              method: "POST",
              body: JSON.stringify({ refresh_token: session.refreshToken }),
            });
          } finally {
            clearSession();
          }
        } else {
          clearSession();
        }
      },
      getGroups() {
        return request<GroupListItem[]>("/groups");
      },
      createGroup(name: string) {
        return request<Group>("/groups", {
          method: "POST",
          body: JSON.stringify({ name }),
        });
      },
      getGroup(groupId: string) {
        return request<Group>(`/groups/${groupId}`);
      },
      updateGroup(groupId: string, name: string) {
        return request<Group>(`/groups/${groupId}`, {
          method: "PUT",
          body: JSON.stringify({ name }),
        });
      },
      deleteGroup(groupId: string) {
        return request<void>(`/groups/${groupId}`, { method: "DELETE" });
      },
      addParticipant(groupId: string, payload: { name: string; color_hex?: string }) {
        return request<Participant>(`/groups/${groupId}/participants`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
      },
      updateParticipant(participantId: string, payload: { name?: string; color_hex?: string }) {
        return request<Participant>(`/participants/${participantId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      },
      deleteParticipant(participantId: string) {
        return request<void>(`/participants/${participantId}`, { method: "DELETE" });
      },
      getExpenses(groupId: string, filters: ExpenseFilters) {
        const query = buildQuery({ groupId, ...filters });
        return request<ExpenseList>(`/expenses?${query}`);
      },
      getExpense(expenseId: string) {
        return request<Expense>(`/expenses/${expenseId}`);
      },
      createExpense(payload: ExpensePayload) {
        return request<Expense>("/expenses", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      },
      updateExpense(expenseId: string, payload: ExpensePayload) {
        return request<Expense>(`/expenses/${expenseId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      },
      deleteExpense(expenseId: string) {
        return request<void>(`/expenses/${expenseId}`, { method: "DELETE" });
      },
      parseExpense(payload: { group_id?: string; text: string }) {
        return request<MintSenseParseResponse>("/ai/parse-expense", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      },
      summarizeGroup(groupId: string, maxHighlights = 3) {
        return request<MintSenseSummary>(`/ai/groups/${groupId}/summary`, {
          method: "POST",
          body: JSON.stringify({ max_highlights: maxHighlights }),
        });
      },
    };
  }, [clearSession, session, setSession]);

  return client;
}

export function formatCurrency(value: string | number) {
  const numericValue = typeof value === "number" ? value : Number.parseFloat(value);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(Number.isFinite(numericValue) ? numericValue : 0);
}
