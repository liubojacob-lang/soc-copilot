"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface TimelineStep {
  label: string;
  status: "completed" | "current" | "pending";
}

interface StatusTimelineProps {
  steps: TimelineStep[];
  className?: string;
}

/**
 * 状态流转步骤条
 * - 已完成：slate-900 背景 + 对勾图标
 * - 进行中：slate-500 背景 + 当前白点
 * - 未开始：slate-300 空心圆
 */
export function StatusTimeline({ steps, className }: StatusTimelineProps) {
  return (
    <div className={cn("flex items-start", className)}>
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1;

        return (
          <div key={step.label} className="flex items-center">
            <div className="flex flex-col items-center">
              {/* 节点 */}
              <div
                className={cn("w-6 h-6 rounded-full flex items-center justify-center border-2", {
                  "bg-slate-900 border-slate-900 text-white": step.status === "completed",
                  "bg-slate-500 border-slate-500 text-white": step.status === "current",
                  "bg-transparent border-slate-300 dark:border-slate-600":
                    step.status === "pending",
                })}
              >
                {step.status === "completed" && <Check className="w-3.5 h-3.5" strokeWidth={2.5} />}
                {step.status === "current" && <div className="w-2 h-2 rounded-full bg-white" />}
              </div>

              {/* 标签 */}
              <span
                className={cn("mt-1.5 text-[11px] font-medium whitespace-nowrap", {
                  "text-slate-900 dark:text-slate-100": step.status === "completed",
                  "text-slate-500 dark:text-slate-400": step.status === "current",
                  "text-slate-300 dark:text-slate-600": step.status === "pending",
                })}
              >
                {step.label}
              </span>
            </div>

            {/* 连线 */}
            {!isLast && (
              <div
                className={cn(
                  "w-8 h-px mx-2 mt-3",
                  step.status === "completed" ? "bg-slate-900" : "bg-slate-300 dark:bg-slate-600"
                )}
                style={
                  step.status !== "completed"
                    ? { borderTop: "1px dashed", borderColor: "inherit" }
                    : undefined
                }
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
