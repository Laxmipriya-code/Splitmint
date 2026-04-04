import { Children, cloneElement, isValidElement, useId } from "react";
import type { PropsWithChildren, ReactElement, ReactNode } from "react";

type FieldProps = PropsWithChildren<{
  label: string;
  hint?: string;
  error?: string;
}>;

export function Field({ children, label, hint, error }: FieldProps) {
  const generatedId = useId();
  let controlId = generatedId;

  let control: ReactNode = children;
  if (Children.count(children) === 1) {
    const child = Children.only(children);
    if (isValidElement(child)) {
      const childProps = child.props as { id?: string };
      controlId = childProps.id ?? generatedId;
      control = cloneElement(child as ReactElement<{ id?: string }>, { id: controlId });
    }
  }

  return (
    <div className="field">
      <label htmlFor={controlId}>{label}</label>
      {control}
      {hint ? <span className="tiny muted">{hint}</span> : null}
      {error ? <span className="tiny" style={{ color: "var(--danger)" }}>{error}</span> : null}
    </div>
  );
}
