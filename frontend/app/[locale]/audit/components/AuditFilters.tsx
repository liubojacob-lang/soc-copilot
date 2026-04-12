"use client";

import { useTranslations } from "next-intl";

interface AuditFiltersProps {
  filterAction: string;
  filterPath: string;
  filterStatusCode: string;
  filterDateFrom: string;
  filterDateTo: string;
  filterUserId: string;
  filterIpAddress: string;
  onFilterChange: (filters: {
    action: string;
    path: string;
    statusCode: string;
    dateFrom: string;
    dateTo: string;
    userId: string;
    ipAddress: string;
  }) => void;
  onReset: () => void;
}

export function AuditFilters({
  filterAction,
  filterPath,
  filterStatusCode,
  filterDateFrom,
  filterDateTo,
  filterUserId,
  filterIpAddress,
  onFilterChange,
  onReset,
}: AuditFiltersProps) {
  const t = useTranslations("audit");
  const tAuditPage = useTranslations("auditPage");

  const handleActionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({
      action: e.target.value,
      path: filterPath,
      statusCode: filterStatusCode,
      dateFrom: filterDateFrom,
      dateTo: filterDateTo,
      userId: filterUserId,
      ipAddress: filterIpAddress,
    });
  };

  const handlePathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      action: filterAction,
      path: e.target.value,
      statusCode: filterStatusCode,
      dateFrom: filterDateFrom,
      dateTo: filterDateTo,
      userId: filterUserId,
      ipAddress: filterIpAddress,
    });
  };

  const handleStatusCodeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({
      action: filterAction,
      path: filterPath,
      statusCode: e.target.value,
      dateFrom: filterDateFrom,
      dateTo: filterDateTo,
      userId: filterUserId,
      ipAddress: filterIpAddress,
    });
  };

  const handleDateFromChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      action: filterAction,
      path: filterPath,
      statusCode: filterStatusCode,
      dateFrom: e.target.value,
      dateTo: filterDateTo,
      userId: filterUserId,
      ipAddress: filterIpAddress,
    });
  };

  const handleDateToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      action: filterAction,
      path: filterPath,
      statusCode: filterStatusCode,
      dateFrom: filterDateFrom,
      dateTo: e.target.value,
      userId: filterUserId,
      ipAddress: filterIpAddress,
    });
  };

  const handleUserIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      action: filterAction,
      path: filterPath,
      statusCode: filterStatusCode,
      dateFrom: filterDateFrom,
      dateTo: filterDateTo,
      userId: e.target.value,
      ipAddress: filterIpAddress,
    });
  };

  const handleIpAddressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      action: filterAction,
      path: filterPath,
      statusCode: filterStatusCode,
      dateFrom: filterDateFrom,
      dateTo: filterDateTo,
      userId: filterUserId,
      ipAddress: e.target.value,
    });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          {tAuditPage("filters.title")}
        </h3>
        <button
          onClick={onReset}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
        >
          {tAuditPage("filters.reset")}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Action Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {tAuditPage("filters.action")}
          </label>
          <select
            value={filterAction}
            onChange={handleActionChange}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
          >
            <option value="">{tAuditPage("filters.allActions")}</option>
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="PATCH">PATCH</option>
            <option value="DELETE">DELETE</option>
            <option value="LOGIN">LOGIN</option>
            <option value="LOGOUT">LOGOUT</option>
          </select>
        </div>

        {/* Status Code Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {tAuditPage("filters.statusCode")}
          </label>
          <select
            value={filterStatusCode}
            onChange={handleStatusCodeChange}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
          >
            <option value="">{tAuditPage("filters.allStatuses")}</option>
            <option value="200">200 - OK</option>
            <option value="201">201 - Created</option>
            <option value="400">400 - Bad Request</option>
            <option value="401">401 - Unauthorized</option>
            <option value="403">403 - Forbidden</option>
            <option value="404">404 - Not Found</option>
            <option value="500">500 - Server Error</option>
          </select>
        </div>

        {/* Date Range Filters */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {tAuditPage("filters.dateFrom")}
          </label>
          <input
            type="date"
            value={filterDateFrom}
            onChange={handleDateFromChange}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {tAuditPage("filters.dateTo")}
          </label>
          <input
            type="date"
            value={filterDateTo}
            onChange={handleDateToChange}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>

        {/* Path Filter */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {tAuditPage("filters.path")}
          </label>
          <input
            type="text"
            value={filterPath}
            onChange={handlePathChange}
            placeholder={tAuditPage("filters.pathPlaceholder")}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>

        {/* User ID Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {tAuditPage("filters.userId")}
          </label>
          <input
            type="text"
            value={filterUserId}
            onChange={handleUserIdChange}
            placeholder={tAuditPage("filters.userIdPlaceholder")}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>

        {/* IP Address Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {tAuditPage("filters.ipAddress")}
          </label>
          <input
            type="text"
            value={filterIpAddress}
            onChange={handleIpAddressChange}
            placeholder={tAuditPage("filters.ipAddressPlaceholder")}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
          />
        </div>
      </div>
    </div>
  );
}
