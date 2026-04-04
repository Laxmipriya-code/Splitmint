import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";

import { ApiError, useApiClient } from "../lib/api";
import { Button } from "../components/ui/Button";
import { ErrorState } from "../components/ui/State";
import { Field } from "../components/ui/Field";

const registerSchema = z.object({
  display_name: z.string().trim().min(1, "Display name is required."),
  email: z.email(),
  password: z.string().min(8, "Use at least 8 characters."),
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const api = useApiClient();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { display_name: "", email: "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      setErrorMessage(null);
      await api.register(values);
      navigate("/groups", { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Unable to create the account.");
    }
  });

  return (
    <div className="auth-page">
      <div className="auth-card stack">
        <div className="brand-copy">
          <p className="brand-title">Create your ledger</p>
          <p className="brand-subtitle">
            Register once, then keep every group, split, and settlement in one place.
          </p>
        </div>

        {errorMessage ? <ErrorState title="Registration failed" detail={errorMessage} /> : null}

        <form className="field-grid" onSubmit={onSubmit}>
          <Field label="Display name" error={errors.display_name?.message}>
            <input className="input" type="text" {...register("display_name")} />
          </Field>

          <Field label="Email" error={errors.email?.message}>
            <input className="input" type="email" {...register("email")} />
          </Field>

          <Field label="Password" error={errors.password?.message}>
            <input className="input" type="password" {...register("password")} />
          </Field>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>
        </form>

        <p className="muted tiny">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
