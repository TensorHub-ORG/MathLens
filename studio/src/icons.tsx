import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function IconFrame({ children, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export const PointerIcon = (props: IconProps) => (
  <IconFrame {...props}><path d="m5 3 13 9-6 1.5L9 19Z" /></IconFrame>
);
export const BoxIcon = (props: IconProps) => (
  <IconFrame {...props}><rect x="4" y="4" width="16" height="16" rx="1" /><path d="M8 4v4H4m12-4v4h4M8 20v-4H4m12 4v-4h4" /></IconFrame>
);
export const UndoIcon = (props: IconProps) => (
  <IconFrame {...props}><path d="M9 7 4 12l5 5" /><path d="M5 12h8a6 6 0 0 1 6 6" /></IconFrame>
);
export const RedoIcon = (props: IconProps) => (
  <IconFrame {...props}><path d="m15 7 5 5-5 5" /><path d="M19 12h-8a6 6 0 0 0-6 6" /></IconFrame>
);
export const ChevronIcon = (props: IconProps) => (
  <IconFrame {...props}><path d="m9 6 6 6-6 6" /></IconFrame>
);
export const TrashIcon = (props: IconProps) => (
  <IconFrame {...props}><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5" /></IconFrame>
);
export const GripIcon = (props: IconProps) => (
  <IconFrame {...props}><path d="M9 7h.01M15 7h.01M9 12h.01M15 12h.01M9 17h.01M15 17h.01" strokeWidth="3" /></IconFrame>
);
export const CheckIcon = (props: IconProps) => (
  <IconFrame {...props}><path d="m5 12 4 4L19 6" /></IconFrame>
);
export const SaveIcon = (props: IconProps) => (
  <IconFrame {...props}><path d="M5 4h12l2 2v14H5Z" /><path d="M8 4v6h8V4M8 20v-6h8v6" /></IconFrame>
);
