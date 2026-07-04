interface IconProps {
  className?: string;
}

// Small hand-rolled inline SVG icons — no icon-library dependency, no emoji. Keeps the tool's
// internal/professional visual register (docs/safety.md). Each icon is paired with a text label
// wherever it's used; icons never carry meaning on their own.

export function WarningIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" className={className} aria-hidden="true">
      <path d="M10 1.5 19 17H1L10 1.5Z M10 7v4.5 M10 14.2h.01" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" strokeLinecap="round" fill="none" />
    </svg>
  );
}

export function InfoIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" className={className} aria-hidden="true">
      <circle cx="10" cy="10" r="8.5" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <path d="M10 9v5 M10 6.2h.01" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function CheckIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" className={className} aria-hidden="true">
      <circle cx="10" cy="10" r="8.5" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <path d="m6.5 10.2 2.4 2.4 4.6-5.2" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ChevronIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" className={className} aria-hidden="true">
      <path d="m7 5 6 5-6 5" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function DotIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 20 20" width="10" height="10" className={className} aria-hidden="true">
      <circle cx="10" cy="10" r="6" fill="currentColor" />
    </svg>
  );
}
