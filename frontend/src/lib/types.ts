export type ApiSuccess<T> = {
  status: "success";
  data: T;
  message?: string;
  meta?: Record<string, unknown>;
};

export type ApiFailure = {
  status: "error";
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};

export type User = {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
  updated_at: string;
  version: number;
};

export type BackendAuthSession = {
  user: User;
  tokens: {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in_seconds: number;
  };
};

export type AuthSession = {
  user: User;
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresInSeconds: number;
};

export type Participant = {
  id: string;
  group_id: string;
  name: string;
  avatar_url: string | null;
  color_hex: string | null;
  is_active: boolean;
  is_owner: boolean;
  created_at: string;
  updated_at: string;
  version: number;
};

export type ParticipantBalance = {
  participant_id: string;
  name: string;
  color_hex: string | null;
  is_active: boolean;
  is_owner: boolean;
  paid_total: string;
  owed_total: string;
  net_balance: string;
};

export type Settlement = {
  from_participant_id: string;
  from_name: string;
  to_participant_id: string;
  to_name: string;
  amount: string;
};

export type BalanceSnapshot = {
  total_spent: string;
  you_owe: string;
  you_are_owed: string;
  balances: ParticipantBalance[];
  settlements: Settlement[];
};

export type GroupListItem = {
  id: string;
  name: string;
  active_participant_count: number;
  total_spent: string;
  you_owe: string;
  you_are_owed: string;
  created_at: string;
  updated_at: string;
  version: number;
};

export type Group = {
  id: string;
  name: string;
  owner_participant_id: string;
  participants: Participant[];
  summary: BalanceSnapshot;
  created_at: string;
  updated_at: string;
  version: number;
};

export type ExpenseSplit = {
  participant_id: string;
  participant_name: string;
  owed_amount: string;
  input_value: string | null;
  position: number;
};

export type Expense = {
  id: string;
  group_id: string;
  payer_id: string;
  payer_name: string;
  amount: string;
  description: string;
  category: string | null;
  split_mode: "equal" | "custom" | "percentage";
  date: string;
  splits: ExpenseSplit[];
  created_at: string;
  updated_at: string;
  version: number;
};

export type ExpenseList = {
  items: Expense[];
  total: number;
  page: number;
  size: number;
};

export type MintSenseResolvedParty = {
  participant_id: string;
  participant_name: string;
};

export type MintSenseDraft = {
  description: string | null;
  amount: string | null;
  category: string | null;
  date: string | null;
  payer_name: string | null;
  participant_names: string[];
  split_mode: "equal" | "custom" | "percentage" | null;
  splits: Array<{ participant_name: string; value: string }>;
  ambiguities: string[];
  needs_confirmation: boolean;
};

export type MintSenseParseResponse = {
  draft: MintSenseDraft;
  resolved_payer: MintSenseResolvedParty | null;
  resolved_participants: MintSenseResolvedParty[];
  validation_issues: string[];
};

export type MintSenseSummary = {
  summary: string;
  highlights: string[];
};

export type ExpensePayload = {
  group_id: string;
  amount: string;
  description: string;
  category: string | null;
  date: string;
  payer_id: string;
  participants: string[];
  split_mode: "equal" | "custom" | "percentage";
  splits: Array<{ participant_id: string; value: string }>;
};

export type ExpenseFilters = {
  search?: string;
  participantId?: string;
  dateFrom?: string;
  dateTo?: string;
  minAmount?: string;
  maxAmount?: string;
  page?: number;
  size?: number;
};
