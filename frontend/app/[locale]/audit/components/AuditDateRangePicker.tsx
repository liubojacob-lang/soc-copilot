/** Date range picker component with presets */

import { useFormatter } from "next-intl";

import { datePresets, formatDateForInput } from "../utils";
import type { AuditFilters } from "../types";

interface AuditDateRangePickerProps {
  filters: Pick<AuditFilters, "dateFrom" | "dateTo">;
  onChange: (from: string, to: string) => void;
  onClear: () => void;
}

export function AuditDateRangePicker({ filters, onChange, onClear }: AuditDateRangePickerProps) {
  const { dateFrom, dateTo } = filters;
  const format = useFormatter();

  const applyDatePreset = (preset: (typeof datePresets)[0]) => {
    const range = preset.getRange();
    // Check if this preset is already selected - if so, toggle it off
    const isSelected = range.from === dateFrom && range.to === dateTo;

    if (isSelected) {
      // Toggle off - clear date filter
      onChange("", "");
    } else {
      // Apply the preset
      onChange(range.from, range.to);
    }
  };

  const getSelectedDateDisplay = () => {
    if (!dateFrom && !dateTo) return null;

    // Check if matches a preset
    const matchingPreset = datePresets.find((preset) => {
      const range = preset.getRange();
      return range.from === dateFrom && range.to === dateTo;
    });

    if (matchingPreset) {
      return matchingPreset.name + " " + matchingPreset.label;
    }

    // Custom range display
    if (dateFrom && dateTo) {
      const fromDate = new Date(dateFrom);
      const toDate = new Date(dateTo);
      return `Custom: ${format.dateTime(fromDate, { dateStyle: "medium" })} - ${format.dateTime(toDate, { dateStyle: "medium" })}`;
    }
    if (dateFrom) {
      return `From ${format.dateTime(new Date(dateFrom), { dateStyle: "medium" })}`;
    }
    if (dateTo) {
      return `To ${format.dateTime(new Date(dateTo), { dateStyle: "medium" })}`;
    }
    return null;
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          Date Range
        </h4>
        {(dateFrom || dateTo) && (
          <button
            onClick={onClear}
            className="text-xs text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 flex items-center gap-1 transition-colors"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
            Clear
          </button>
        )}
      </div>

      {/* Selected Range Display */}
      {getSelectedDateDisplay() && (
        <div className="mb-3 px-3 py-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
          <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
            {getSelectedDateDisplay()}
          </span>
        </div>
      )}

      {/* Date Presets - Compact */}
      <div className="grid grid-cols-4 md:grid-cols-7 gap-2 mb-3">
        {datePresets.slice(0, 7).map((preset) => {
          const range = preset.getRange();
          const isSelected = range.from === dateFrom && range.to === dateTo;
          return (
            <button
              key={preset.id}
              onClick={() => applyDatePreset(preset)}
              className={`px-2 py-2 text-xs font-medium rounded-lg transition-all ${
                isSelected
                  ? "bg-blue-600 text-white shadow-md"
                  : "bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600"
              }`}
              title={preset.label}
            >
              {preset.name}
            </button>
          );
        })}
      </div>

      {/* Custom Date Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label
            htmlFor="filterDateFrom"
            className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            From
          </label>
          <input
            id="filterDateFrom"
            type="datetime-local"
            value={dateFrom}
            onChange={(e) => onChange(e.target.value, dateTo)}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>
        <div>
          <label
            htmlFor="filterDateTo"
            className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            To
          </label>
          <input
            id="filterDateTo"
            type="datetime-local"
            value={dateTo}
            onChange={(e) => onChange(dateFrom, e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>
      </div>
    </div>
  );
}
