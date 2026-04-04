import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";

import { ApiError, useApiClient } from "../lib/api";
import { Button } from "../components/ui/Button";
import { ErrorState } from "../components/ui/State";
import { Field } from "../components/ui/Field";

const loginSchema = z.object({
  email: z.email(),
  password: z.string().min(8),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const api = useApiClient();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      setErrorMessage(null);
      await api.login(values);
      navigate("/groups", { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Unable to sign in.");
    }
  });

  return (
    <div className="auth-page">
      <div className="auth-card stack">
        <div className="brand-copy">
          <p className="brand-title">Welcome back</p>
          <p className="brand-subtitle">
            Log in to manage groups, expenses, and settlements from the same ledger.
          </p>
        </div>

        {errorMessage ? <ErrorState title="Sign-in failed" detail={errorMessage} /> : null}

        <form className="field-grid" onSubmit={onSubmit}>
          <Field label="Email" error={errors.email?.message}>
            <input className="input" type="email" {...register("email")} />
          </Field>

          <Field label="Password" error={errors.password?.message}>
            <input className="input" type="password" {...register("password")} />
          </Field>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        <p className="muted tiny">
          New to SplitMint? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
