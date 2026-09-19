"use client";

/**
 * 现代日期范围选择器（antd RangePicker / shadcn 风格）：
 * - 触发器按钮展示当前范围（预设名或 "MM-DD HH:mm → MM-DD HH:mm"）
 * - 弹出面板：快捷预设 + 自定义范围
 * - 自定义范围为「双月历 range 联动 + 起止时间微调」：
 *   点起点 → 悬停预览 → 点终点，区间自动高亮；时间输入与日历联动，
 *   起 > 止 时禁用应用并提示；未来日期不可选
 * - 点击外部 / Esc 关闭，主题经 globals.css 中 --rdp-* 变量挂到全站 token
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { DayPicker, type DateRange } from "react-day-picker";
import { format, isAfter, startOfDay } from "date-fns";
import { enUS, zhCN } from "date-fns/locale";
import { Calendar, Check, ChevronDown, X } from "lucide-react";

import "react-day-picker/style.css";

import { cn } from "@/lib/utils";
import { formatDateForInput } from "../utils";

interface AuditDateRangePickerProps {
  dateFrom: string;
  dateTo: string;
  onChange: (from: string, to: string) => void;
}

interface RangePreset {
  id: string;
  getRange: () => { from: string; to: string };
}

/** 快捷预设（id 与 messages 中 auditPage.dateRange.* 一一对应） */
const RANGE_PRESETS: RangePreset[] = [
  {
    id: "last15Minutes",
    getRange: () => {
      const now = new Date();
      return {
        from: formatDateForInput(new Date(now.getTime() - 15 * 60 * 1000)),
        to: formatDateForInput(now),
      };
    },
  },
  {
    id: "lastHour",
    getRange: () => {
      const now = new Date();
      return {
        from: formatDateForInput(new Date(now.getTime() - 60 * 60 * 1000)),
        to: formatDateForInput(now),
      };
    },
  },
  {
    id: "today",
    getRange: () => {
      const now = new Date();
      const from = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
      return { from: formatDateForInput(from), to: formatDateForInput(now) };
    },
  },
  {
    id: "yesterday",
    getRange: () => {
      const now = new Date();
      const y = now.getDate() - 1;
      const from = new Date(now.getFullYear(), now.getMonth(), y, 0, 0, 0);
      const to = new Date(now.getFullYear(), now.getMonth(), y, 23, 59, 59);
      return { from: formatDateForInput(from), to: formatDateForInput(to) };
    },
  },
  {
    id: "last7Days",
    getRange: () => {
      const now = new Date();
      return {
        from: formatDateForInput(new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)),
        to: formatDateForInput(now),
      };
    },
  },
  {
    id: "last30Days",
    getRange: () => {
      const now = new Date();
      return {
        from: formatDateForInput(new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)),
        to: formatDateForInput(now),
      };
    },
  },
  {
    id: "thisWeek",
    getRange: () => {
      const now = new Date();
      const mondayOffset = (now.getDay() + 6) % 7; // 周一为一周起点
      const from = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate() - mondayOffset,
        0,
        0,
        0
      );
      return { from: formatDateForInput(from), to: formatDateForInput(now) };
    },
  },
  {
    id: "thisMonth",
    getRange: () => {
      const now = new Date();
      const from = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0);
      return { from: formatDateForInput(from), to: formatDateForInput(now) };
    },
  },
];

/** "2026-09-15T10:30" -> "09-15 10:30"（datetime-local 值无需时区解析） */
function shortLabel(value: string): string {
  return value.length >= 16 ? `${value.slice(5, 10)} ${value.slice(11, 16)}` : value;
}

/** 解析 datetime-local 字符串为「日期 + HH:mm」 */
function parseInputValue(value: string): { date: Date; time: string } | null {
  if (!value) return null;
  const [d, t] = value.split("T");
  const date = new Date(`${d}T00:00`);
  if (Number.isNaN(date.getTime())) return null;
  return { date, time: t ? t.slice(0, 5) : "00:00" };
}

/** 日期 + HH:mm 组装回 datetime-local 字符串 */
function composeInputValue(date: Date, time: string): string {
  return `${formatDateForInput(date).slice(0, 10)}T${time}`;
}

export function AuditDateRangePicker({ dateFrom, dateTo, onChange }: AuditDateRangePickerProps) {
  const t = useTranslations("auditPage");
  const locale = useLocale();
  const dateFnsLocale = locale.startsWith("zh") ? zhCN : enUS;

  const [open, setOpen] = useState(false);
  const [activePresetId, setActivePresetId] = useState<string | null>(null);

  // 自定义范围草稿：月历选日期、time input 调时分
  const [draftRange, setDraftRange] = useState<DateRange | undefined>(undefined);
  const [draftStartTime, setDraftStartTime] = useState("00:00");
  const [draftEndTime, setDraftEndTime] = useState("23:59");

  const rootRef = useRef<HTMLDivElement>(null);

  const hasValue = Boolean(dateFrom || dateTo);
  const selectedPresetLabel = activePresetId
    ? RANGE_PRESETS.find((p) => p.id === activePresetId)?.id
    : undefined;

  // 外部清空时同步移除预设高亮
  useEffect(() => {
    if (!dateFrom && !dateTo) setActivePresetId(null);
  }, [dateFrom, dateTo]);

  // 点击外部 / Esc 关闭
  useEffect(() => {
    if (!open) return;
    const handleMouseDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  /** 打开面板时，把当前值拆成日历草稿 */
  const toggleOpen = () => {
    setOpen((v) => {
      if (!v) {
        const f = parseInputValue(dateFrom);
        const to = parseInputValue(dateTo);
        setDraftRange(f || to ? { from: f?.date, to: to?.date } : undefined);
        setDraftStartTime(f?.time ?? "00:00");
        setDraftEndTime(to?.time ?? "23:59");
      }
      return !v;
    });
  };

  const applyPreset = (preset: RangePreset) => {
    const range = preset.getRange();
    onChange(range.from, range.to);
    setActivePresetId(preset.id);
    setOpen(false);
  };

  // ---- 草稿合成与校验（datetime-local 同格式，字符串比较即可）----
  const fromDraft = draftRange?.from ? composeInputValue(draftRange.from, draftStartTime) : "";
  const toDraft = draftRange?.to ? composeInputValue(draftRange.to, draftEndTime) : "";
  const invalidRange = Boolean(fromDraft && toDraft && fromDraft > toDraft);
  const canApply = Boolean(fromDraft) && !invalidRange;

  /** 已选时长摘要，如 "7 天 3 小时" */
  const durationSummary = useMemo(() => {
    if (!fromDraft || !toDraft || invalidRange) return null;
    let mins = Math.max(
      0,
      Math.round((new Date(toDraft).getTime() - new Date(fromDraft).getTime()) / 60000)
    );
    const d = Math.floor(mins / 1440);
    mins -= d * 1440;
    const h = Math.floor(mins / 60);
    mins -= h * 60;
    const parts: string[] = [];
    if (d) parts.push(t("filters.durationDays", { count: d }));
    if (h) parts.push(t("filters.durationHours", { count: h }));
    if (!d && !h) parts.push(t("filters.durationMinutes", { count: Math.max(1, mins) }));
    return parts.join(" ");
  }, [fromDraft, toDraft, invalidRange, t]);

  const applyCustom = () => {
    onChange(fromDraft, toDraft);
    setActivePresetId(null);
    setOpen(false);
  };

  const clearRange = () => {
    onChange("", "");
    setActivePresetId(null);
    setDraftRange(undefined);
    setOpen(false);
  };

  const triggerLabel = () => {
    if (selectedPresetLabel) return t(`dateRange.${selectedPresetLabel}`);
    if (dateFrom && dateTo) return `${shortLabel(dateFrom)} → ${shortLabel(dateTo)}`;
    if (dateFrom) return `${t("dateRange.from")} ${shortLabel(dateFrom)} →`;
    if (dateTo) return `→ ${t("dateRange.to")} ${shortLabel(dateTo)}`;
    return t("filters.allTime");
  };

  const timeInputClass =
    "px-2 py-1 text-sm bg-surface-input border border-border-default rounded-md focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-600 text-text-primary transition-all disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div ref={rootRef} className="relative">
      {/* 触发器 */}
      <button
        type="button"
        onClick={toggleOpen}
        aria-haspopup="dialog"
        aria-expanded={open}
        className={cn(
          "flex w-full items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-all duration-150",
          hasValue
            ? "border-accent-500/40 bg-accent-500/10 text-accent-700 dark:text-accent-300 font-medium"
            : "border-border-default bg-surface-input text-text-secondary hover:border-border-strong hover:text-text-primary"
        )}
      >
        <Calendar
          className={cn(
            "w-4 h-4 shrink-0",
            hasValue ? "text-accent-600 dark:text-accent-400" : "text-text-muted"
          )}
        />
        <span className={cn("truncate", !hasValue && "text-text-tertiary font-normal")}>
          {triggerLabel()}
        </span>
        <ChevronDown
          className={cn(
            "w-3.5 h-3.5 ml-auto shrink-0 text-text-muted transition-transform",
            open && "rotate-180"
          )}
        />
      </button>

      {/* 弹出面板 */}
      {open && (
        <div
          role="dialog"
          aria-label={t("filters.customRange")}
          className="absolute right-0 z-30 mt-2 w-[min(600px,calc(100vw-2rem))] rounded-xl border border-border-subtle bg-surface-card shadow-elevated p-4"
        >
          {/* 快捷预设 */}
          <div className="mb-3">
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">
              {t("filters.quickRanges")}
            </h4>
            <div className="grid grid-cols-4 gap-1.5">
              {RANGE_PRESETS.map((preset) => {
                const isSelected = activePresetId === preset.id;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => applyPreset(preset)}
                    className={cn(
                      "flex items-center justify-center gap-1 px-2 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150",
                      isSelected
                        ? "border-accent-600 bg-accent-600 text-white shadow-sm"
                        : "border-border-subtle bg-surface-input text-text-secondary hover:border-border-default hover:text-text-primary"
                    )}
                  >
                    {isSelected && <Check className="w-3 h-3" />}
                    {t(`dateRange.${preset.id}`)}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 自定义范围：双月历 range 联动 + 时间微调 */}
          <div className="border-t border-border-subtle pt-3">
            <h4 className="mb-1 text-xs font-medium uppercase tracking-wide text-text-muted">
              {t("filters.customRange")}
            </h4>

            <DayPicker
              mode="range"
              numberOfMonths={2}
              selected={draftRange}
              onSelect={(range) => setDraftRange(range)}
              captionLayout="dropdown"
              defaultMonth={draftRange?.from ?? new Date()}
              disabled={(day) => isAfter(startOfDay(day), startOfDay(new Date()))}
              locale={dateFnsLocale}
            />

            {/* 起止时间（与日历联动：起点未选禁用开始，终点未选禁用结束） */}
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-text-secondary">
                  {t("filters.startTime")}
                </span>
                {draftRange?.from && (
                  <span className="font-mono text-xs text-text-muted">
                    {format(draftRange.from, "yyyy-MM-dd EEE", { locale: dateFnsLocale })}
                  </span>
                )}
                <input
                  type="time"
                  value={draftStartTime}
                  disabled={!draftRange?.from}
                  onChange={(e) => setDraftStartTime(e.target.value || "00:00")}
                  aria-label={t("filters.startTime")}
                  className={timeInputClass}
                />
              </div>

              <span className="text-text-muted">→</span>

              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-text-secondary">
                  {t("filters.endTime")}
                </span>
                {draftRange?.to && (
                  <span className="font-mono text-xs text-text-muted">
                    {format(draftRange.to, "yyyy-MM-dd EEE", { locale: dateFnsLocale })}
                  </span>
                )}
                <input
                  type="time"
                  value={draftEndTime}
                  disabled={!draftRange?.to}
                  onChange={(e) => setDraftEndTime(e.target.value || "23:59")}
                  aria-label={t("filters.endTime")}
                  className={timeInputClass}
                />
              </div>

              {durationSummary && (
                <span className="ml-auto text-xs text-text-muted">
                  {t("filters.totalDuration")}{" "}
                  <span className="font-medium text-text-secondary">{durationSummary}</span>
                </span>
              )}
            </div>

            {invalidRange && (
              <p role="alert" className="mt-2 text-xs text-danger-600 dark:text-danger-400">
                {t("filters.startAfterEnd")}
              </p>
            )}

            {/* 操作按钮 */}
            <div className="mt-3 flex items-center justify-between">
              {hasValue ? (
                <button
                  type="button"
                  onClick={clearRange}
                  className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-text-muted hover:text-danger-600 dark:hover:text-danger-400 rounded-md transition-colors"
                >
                  <X className="w-3 h-3" />
                  {t("filters.clear")}
                </button>
              ) : (
                <span />
              )}
              <button
                type="button"
                onClick={applyCustom}
                disabled={!canApply}
                className="px-3 py-1.5 text-xs font-medium text-white bg-accent-600 hover:bg-accent-700 rounded-lg shadow-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {t("filters.apply")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
