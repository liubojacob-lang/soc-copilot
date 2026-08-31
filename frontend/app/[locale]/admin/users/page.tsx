"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "@/i18n/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { PageHeader } from "@/components/common/PageHeader";
import { ConfirmDialog } from "@/components/common";
import { useUsers, generatePassword, type User, type PaginationInfo } from "./hooks/useUsers";
import { useUserModals } from "./hooks/useUserModals";
import {
  Search,
  RefreshCw,
  X,
  XCircle,
  Edit2,
  Trash2,
  Eye,
  EyeOff,
  Check,
  UserPlus,
  AlertCircle,
  CheckCircle,
  Key,
  ChevronLeft,
  ChevronRight,
  Shield,
} from "lucide-react";

export default function UsersPage() {
  const format = useFormatter();
  const router = useRouter();
  const t = useTranslations("users");
  const tCommon = useTranslations("common");

  const { users, loading, error, pagination, filters, fetchUsers, handleFilterChange } = useUsers();

  const {
    showCreateModal,
    setShowCreateModal,
    showEditModal,
    setShowEditModal,
    showDeleteModal,
    setShowDeleteModal,
    showResetModal,
    setShowResetModal,
    selectedUser,
    setSelectedUser,
    successData,
    showPassword,
    setShowPassword,
    isResetPassword,
    closeSuccess,
    username,
    setUsername,
    email,
    setEmail,
    role,
    setRole,
    isActive,
    setIsActive,
    generatedPassword,
    setGeneratedPassword,
    resetNewPassword,
    setResetNewPassword,
    showResetNewPassword,
    setShowResetNewPassword,
    creating,
    saving,
    deleting,
    resetting,
    formErrors,
    handleCreateUser,
    handleEditUser,
    handleDeleteUser,
    handleResetPassword,
    handleGeneratePassword,
    resetForm,
    openEditModal,
    openDeleteModal,
    openResetModal,
  } = useUserModals(fetchUsers, pagination.page);

  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchUsers(pagination.page);
    setRefreshing(false);
  }, [fetchUsers, pagination.page]);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      fetchUsers(newPage);
    }
  };

  const handleSearchChange = (value: string) => {
    handleFilterChange({ search: value });
  };

  const handleRoleChange = (value: string) => {
    handleFilterChange({ role: value as "admin" | "analyst" | "auditor" | "" });
  };

  const handleStatusChange = (value: string) => {
    handleFilterChange({ status: value as "active" | "inactive" | "" });
  };

  const getRoleBadgeClass = (userRole: string) => {
    switch (userRole) {
      case "admin":
        return "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300";
      case "analyst":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300";
      case "auditor":
        return "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300";
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
    }
  };

  const getRoleIcon = (userRole: string) => {
    switch (userRole) {
      case "admin":
        return <Shield className="w-3 h-3" />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t("title")}</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {pagination.total} {pagination.total === 1 ? "user" : "users"}
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg flex items-center gap-2 hover:bg-blue-700"
          >
            <UserPlus className="w-4 h-4" />
            {t("createUser")}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{error}</span>
          </div>
        )}

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder={t("searchPlaceholder")}
                  value={filters.search}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div className="flex gap-2">
                <select
                  value={filters.role}
                  onChange={(e) => handleRoleChange(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">{t("allRoles")}</option>
                  <option value="admin">{t("admin")}</option>
                  <option value="analyst">{t("analyst")}</option>
                  <option value="auditor">{t("auditor")}</option>
                </select>
                <select
                  value={filters.status}
                  onChange={(e) => handleStatusChange(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">{t("allStatus")}</option>
                  <option value="active">{t("active")}</option>
                  <option value="inactive">{t("inactive")}</option>
                </select>
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                </button>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="p-6">
              <div className="animate-pulse">
                <div className="flex gap-4 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded flex-1"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded flex-1"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                </div>
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="flex gap-4 py-3 border-b border-gray-100 dark:border-gray-800"
                  >
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded flex-1"></div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded flex-1"></div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                  </div>
                ))}
              </div>
            </div>
          ) : users.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                <UserPlus className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                {t("noUsers")}
              </h3>
              <p className="text-gray-500 dark:text-gray-400">
                {filters.search || filters.role || filters.status
                  ? t("noUsersFilter")
                  : t("noUsersEmpty")}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("username")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("email")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("role")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("status")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {t("lastLogin")}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      {tCommon("actions")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {users.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                              {user.username.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <span className="font-medium text-gray-900 dark:text-white">
                            {user.username}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-gray-600 dark:text-gray-300">
                        {user.email}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleBadgeClass(user.role)}`}
                        >
                          {getRoleIcon(user.role)}
                          {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {user.is_active ? (
                          <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400">
                            <CheckCircle className="w-4 h-4" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400">
                            <XCircle className="w-4 h-4" />
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {user.last_login_at ? (
                          format.dateTime(new Date(user.last_login_at), {
                            dateStyle: "medium",
                            timeStyle: "short",
                          })
                        ) : (
                          <span className="text-gray-400">Never</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => openResetModal(user)}
                            className="p-2 text-gray-500 hover:text-orange-600 dark:text-gray-400 dark:hover:text-orange-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                            title={t("resetPassword")}
                          >
                            <Key className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => openEditModal(user)}
                            className="p-2 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                            title={t("edit")}
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => openDeleteModal(user)}
                            className="p-2 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                            title={t("delete")}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              {pagination.totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Showing {(pagination.page - 1) * pagination.limit + 1} to{" "}
                    {Math.min(pagination.page * pagination.limit, pagination.total)} of{" "}
                    {pagination.total} results
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePageChange(pagination.page - 1)}
                      disabled={pagination.page === 1}
                      className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Page {pagination.page} of {pagination.totalPages}
                    </span>
                    <button
                      onClick={() => handlePageChange(pagination.page + 1)}
                      disabled={pagination.page === pagination.totalPages}
                      className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Create User Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {t("createUser")}
                </h2>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    resetForm();
                  }}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
              <form onSubmit={handleCreateUser} className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t("username")}
                  </label>
                  <input
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value);
                    }}
                    className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 ${
                      formErrors.username
                        ? "border-red-500 focus:ring-red-500"
                        : "border-gray-300 dark:border-gray-600"
                    }`}
                    minLength={3}
                    maxLength={50}
                    pattern="[a-zA-Z0-9_]+"
                  />
                  {formErrors.username ? (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                      {formErrors.username}
                    </p>
                  ) : (
                    <p className="mt-1 text-xs text-gray-500">
                      3-50 characters, letters, numbers, underscores only
                    </p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t("email")}
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                    }}
                    className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 ${
                      formErrors.email
                        ? "border-red-500 focus:ring-red-500"
                        : "border-gray-300 dark:border-gray-600"
                    }`}
                  />
                  {formErrors.email && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                      {formErrors.email}
                    </p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Password
                  </label>
                  <div className="flex gap-2">
                    <div className="flex-1 relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        value={generatedPassword}
                        onChange={(e) => {
                          setGeneratedPassword(e.target.value);
                        }}
                        placeholder={t("enterPassword")}
                        className={`w-full px-3 py-2 pr-10 border rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 ${
                          formErrors.password
                            ? "border-red-500 focus:ring-red-500"
                            : "border-gray-300 dark:border-gray-600"
                        }`}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showPassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                    <button
                      type="button"
                      onClick={handleGeneratePassword}
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      {t("generate")}
                    </button>
                  </div>
                  {formErrors.password && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                      {formErrors.password}
                    </p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t("role")}
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as "admin" | "analyst" | "auditor")}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="analyst">{t("analyst")}</option>
                    <option value="auditor">{t("auditor")}</option>
                    <option value="admin">{t("admin")}</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="isActive"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <label htmlFor="isActive" className="text-sm text-gray-700 dark:text-gray-300">
                    Active
                  </label>
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={creating || !username || !email}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {creating ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        {t("common.loading")}
                      </>
                    ) : (
                      <>
                        <Check className="w-4 h-4" />
                        {t("create")}
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateModal(false);
                      resetForm();
                    }}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    {t("cancel")}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit User Modal */}
        {showEditModal && selectedUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Edit User</h2>
                <button
                  onClick={() => {
                    setShowEditModal(false);
                    setSelectedUser(null);
                  }}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
              <form onSubmit={handleEditUser} className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Username
                  </label>
                  <input
                    value={selectedUser.username}
                    disabled
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-100 dark:bg-gray-600 cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t("email")}
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t("role")}
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as "admin" | "analyst" | "auditor")}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="analyst">{t("analyst")}</option>
                    <option value="auditor">{t("auditor")}</option>
                    <option value="admin">{t("admin")}</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="editIsActive"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <label
                    htmlFor="editIsActive"
                    className="text-sm text-gray-700 dark:text-gray-300"
                  >
                    Active
                  </label>
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {saving ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        {t("common.loading")}
                      </>
                    ) : (
                      <>
                        <Check className="w-4 h-4" />
                        {t("saveChanges")}
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditModal(false);
                      setSelectedUser(null);
                    }}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    {t("cancel")}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Confirmation Dialog */}
        <ConfirmDialog
          open={showDeleteModal && !!selectedUser}
          title={t("deleteUserTitle")}
          description={t("confirmDelete")}
          confirmText={t("delete")}
          cancelText={t("cancel")}
          variant="danger"
          loading={deleting}
          onConfirm={handleDeleteUser}
          onCancel={() => {
            setShowDeleteModal(false);
            setSelectedUser(null);
          }}
        />

        {/* Reset Password Modal */}
        {showResetModal && selectedUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {t("resetPasswordTitle")}
                </h2>
                <button
                  onClick={() => {
                    setShowResetModal(false);
                    setSelectedUser(null);
                  }}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
              <form onSubmit={handleResetPassword} className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t("username")}
                  </label>
                  <input
                    value={selectedUser.username}
                    disabled
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-100 dark:bg-gray-600 cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t("newPassword")}
                  </label>
                  <div className="flex gap-2">
                    <div className="flex-1 relative">
                      <input
                        type={showResetNewPassword ? "text" : "password"}
                        value={resetNewPassword}
                        onChange={(e) => setResetNewPassword(e.target.value)}
                        className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500"
                        required
                        minLength={8}
                      />
                      <button
                        type="button"
                        onClick={() => setShowResetNewPassword(!showResetNewPassword)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showResetNewPassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                    <button
                      type="button"
                      onClick={() => setResetNewPassword(generatePassword())}
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      {t("generate")}
                    </button>
                  </div>
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={resetting || !resetNewPassword}
                    className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {resetting ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        {t("common.loading")}
                      </>
                    ) : (
                      <>
                        <Key className="w-4 h-4" />
                        {t("resetPassword")}
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowResetModal(false);
                      setSelectedUser(null);
                    }}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    {t("cancel")}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Success Modal */}
        {successData && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-sm w-full">
              <div className="p-6">
                <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white text-center mb-4">
                  {isResetPassword ? t("resetSuccess") : t("createSuccess")}
                </h3>
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4">
                  <div className="mb-2">
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {t("username")}:
                    </span>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {successData.username}
                    </p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {t("password")}:
                    </span>
                    <div className="flex items-center gap-2">
                      <p className="font-mono text-gray-900 dark:text-white break-all">
                        {successData.password}
                      </p>
                      <button
                        onClick={() => navigator.clipboard.writeText(successData.password)}
                        className="text-blue-600 hover:text-blue-700"
                        title={t("copyPassword")}
                      >
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-sm text-yellow-800 dark:text-yellow-200">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{t("passwordWarning")}</span>
                </div>
                <button
                  onClick={() => closeSuccess()}
                  className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  I Understand
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
