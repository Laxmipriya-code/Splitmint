import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../lib/auth";
import { GroupDetailPage } from "../pages/GroupDetailPage";
import { GroupsPage } from "../pages/GroupsPage";
import { LoginPage } from "../pages/LoginPage";
import { RegisterPage } from "../pages/RegisterPage";

function RequireAuth() {
  const { session } = useAuth();

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

function PublicIndex() {
  const { session } = useAuth();
  return <Navigate to={session ? "/groups" : "/login"} replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<PublicIndex />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/groups" element={<GroupsPage />} />
        <Route path="/groups/:groupId" element={<GroupDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
