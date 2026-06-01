import { useId } from "react";

type CanaryMarkProps = {
  size?: number;
  className?: string;
};

export function CanaryMark({ size = 36, className }: CanaryMarkProps) {
  const gradientId = useId();

  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 36 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="1" y="1" width="34" height="34" rx="9" fill={`url(#${gradientId})`} />
      <rect
        x="1"
        y="1"
        width="34"
        height="34"
        rx="9"
        stroke="currentColor"
        strokeOpacity="0.22"
      />
      <rect x="10" y="8" width="16" height="22" rx="3" stroke="currentColor" strokeWidth="1.5" />
      <rect x="15.25" y="5" width="5.5" height="3.5" rx="1.25" fill="currentColor" />
      <path d="M13 14h10M13 18h10M13 22h10" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
      <path
        d="M8 27c1.6-2.2 3.2-3.3 5-3.3s3.4 1.1 5 3.3"
        stroke="hsl(var(--accent))"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M6 30.5c2.4-3.4 4.8-5.1 7.5-5.1s5.1 1.7 7.5 5.1"
        stroke="hsl(var(--accent))"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeOpacity="0.55"
      />
      <defs>
        <linearGradient id={gradientId} x1="4" y1="4" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="hsl(var(--primary) / 0.18)" />
          <stop offset="1" stopColor="hsl(222 16% 11%)" />
        </linearGradient>
      </defs>
    </svg>
  );
}
