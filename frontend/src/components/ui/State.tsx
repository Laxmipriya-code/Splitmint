type MessageProps = {
  title: string;
  detail?: string;
};

export function EmptyState({ title, detail }: MessageProps) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {detail ? <div>{detail}</div> : null}
    </div>
  );
}

export function ErrorState({ title, detail }: MessageProps) {
  return (
    <div className="error-box">
      <strong>{title}</strong>
      {detail ? <div>{detail}</div> : null}
    </div>
  );
}

export function LoadingState({ title = "Loading..." }: { title?: string }) {
  return <div className="notice">{title}</div>;
}
