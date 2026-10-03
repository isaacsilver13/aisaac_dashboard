import { WifiOff } from "iconoir-react";

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
  retrying?: boolean;
}

export function ErrorState({ message, onRetry, retrying = false }: ErrorStateProps) {
  return (
    <div className="ui-error-state" role="alert">
      <WifiOff width={18} height={18} aria-hidden="true" />
      <span>{message}</span>
      <button type="button" onClick={onRetry} disabled={retrying}>
        {retrying ? "Retrying…" : "Try again"}
      </button>
    </div>
  );
}
