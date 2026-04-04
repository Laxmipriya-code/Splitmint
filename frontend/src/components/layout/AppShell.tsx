import type { PropsWithChildren } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useApiClient } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { Button } from "../ui/Button";

export function AppShell({ children }: PropsWithChildren) {
  const navigate = useNavigate();
  const { session } = useAuth();
  const api = useApiClient();

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/groups" className="brand">
          <div className="brand-mark">SM</div>
          <div className="brand-copy">
            <p className="brand-title">SplitMint</p>
            <p className="brand-subtitle">
              Exact balances, clean settlements, and safe AI-assisted entry.
            </p>
          </div>
        </Link>

        <div className="inline-actions">
          <span className="badge">{session?.user.display_name ?? session?.user.email}</span>
          <Button
            variant="ghost"
            onClick={async () => {
              await api.logout();
              navigate("/login", { replace: true });
            }}
          >
            Logout
          </Button>
        </div>
      </header>

      <main className="content">{children}</main>
    </div>
  );
}
