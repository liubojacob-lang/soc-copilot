"use client";

import { cn } from "@/lib/utils";
import { Text } from "@/components/ui/Typography";

interface RiskScoreProps {
  score: number;
  className?: string;
}

/**
 * 获取风险评分对应的填充色
 * 0–40: emerald-600（低危）
 * 40–70: amber-600（中危）
 * 70–100: rose-600（高危）
 */
function getScoreFillColor(score: number): string {
  if (score <= 40) return "bg-emerald-600";
  if (score <= 70) return "bg-amber-600";
  return "bg-rose-600";
}

export function RiskScore({ score, className }: RiskScoreProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const fillColor = getScoreFillColor(clampedScore);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Text color="primary" className="text-sm font-medium tabular-nums min-w-[1.5rem]">
        {clampedScore}
      </Text>
      <div className="bg-slate-100 rounded-[3px] overflow-hidden" style={{ width: 120, height: 6 }}>
        <div
          className={cn("h-full rounded-[3px] transition-all duration-300", fillColor)}
          style={{ width: `${clampedScore}%` }}
        />
      </div>
    </div>
  );
}
