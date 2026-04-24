import { Loader2 } from "lucide-react";

const SIZES = { sm: 16, md: 24, lg: 48 };

export function LoadingSpinner({
  size = "md",
  text = "",
}: {
  size?: "sm" | "md" | "lg";
  text?: string;
}) {
  const px = SIZES[size];
  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <Loader2
        className="animate-spin text-blue-400"
        style={{ width: px, height: px }}
      />
      {text && <p className="text-sm text-slate-400">{text}</p>}
    </div>
  );
}
