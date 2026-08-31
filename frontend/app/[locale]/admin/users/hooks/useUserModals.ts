"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { authFetch } from "@/lib/auth";
import { useToast } from "@/components/Toast";
import { generatePassword, type User } from "./useUsers";

interface FormErrors {
  username?: string;
  email?: string;
  password?: string;
}

interface SuccessData {
  username: string;
  password: string;
}

export function useUserModals(fetchUsers: (page?: number) => Promise<void>, currentPage: number) {
  const t = useTranslations("users");
  const { showToast } = useToast();

  // Modal visibility
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);

  // Shared state
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [successData, setSuccessData] = useState<SuccessData | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [isResetPassword, setIsResetPassword] = useState(false);

  // Form fields
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"admin" | "analyst" | "auditor">("analyst");
  const [isActive, setIsActive] = useState(true);
  const [generatedPassword, setGeneratedPassword] = useState("");
  const [resetNewPassword, setResetNewPassword] = useState("");
  const [showResetNewPassword, setShowResetNewPassword] = useState(false);

  // Loading states
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  const resetForm = useCallback(() => {
    setUsername("");
    setEmail("");
    setRole("analyst");
    setIsActive(true);
    setGeneratedPassword("");
    setFormErrors({});
  }, []);

  const closeSuccess = useCallback(() => {
    setSuccessData(null);
    setIsResetPassword(false);
    setShowPassword(false);
  }, []);

  const handleCreateUser = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      const errors: FormErrors = {};
      if (!username || username.length < 3) {
        errors.username = "Username must be at least 3 characters";
      } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        errors.username = "Username can only contain letters, numbers, and underscores";
      }
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        errors.email = "Please enter a valid email address";
      }
      if (!generatedPassword) {
        errors.password = "Password is required";
      } else if (generatedPassword.length < 8) {
        errors.password = "Password must be at least 8 characters";
      }
      if (Object.keys(errors).length > 0) {
        setFormErrors(errors);
        return;
      }

      setFormErrors({});
      setCreating(true);

      try {
        const password = generatedPassword || generatePassword();
        const response = await authFetch("/api/users", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email, password, role, is_active: isActive }),
        });

        if (response.ok) {
          const data = await response.json();
          setIsResetPassword(false);
          setSuccessData({ username: data.username, password });
          setShowCreateModal(false);
          resetForm();
          fetchUsers(currentPage);
        }
      } catch {
        // Error handled by UI state
      } finally {
        setCreating(false);
      }
    },
    [username, email, generatedPassword, role, isActive, resetForm, fetchUsers, currentPage]
  );

  const handleEditUser = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!selectedUser) return;
      setSaving(true);

      try {
        const response = await authFetch(`/api/users/${selectedUser.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, role, is_active: isActive }),
        });

        if (response.ok) {
          setShowEditModal(false);
          setSelectedUser(null);
          fetchUsers(currentPage);
          showToast(t("updateSuccess"), "success");
        } else {
          showToast(t("updateFailed"), "error");
        }
      } catch {
        showToast(t("updateFailed"), "error");
      } finally {
        setSaving(false);
      }
    },
    [selectedUser, email, role, isActive, fetchUsers, currentPage, showToast, t]
  );

  const handleDeleteUser = useCallback(async () => {
    if (!selectedUser) return;
    setDeleting(true);
    try {
      const response = await authFetch(`/api/users/${selectedUser.id}`, {
        method: "DELETE",
      });
      if (response.ok) {
        setShowDeleteModal(false);
        setSelectedUser(null);
        fetchUsers(currentPage);
        showToast(t("deleteSuccess"), "success");
      } else {
        showToast(t("deleteFailed"), "error");
      }
    } catch {
      showToast(t("deleteFailed"), "error");
    } finally {
      setDeleting(false);
    }
  }, [selectedUser, fetchUsers, currentPage, showToast, t]);

  const handleResetPassword = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!selectedUser || !resetNewPassword) return;
      setResetting(true);

      try {
        const response = await authFetch(`/api/users/${selectedUser.id}/reset-password`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ new_password: resetNewPassword }),
        });

        if (response.ok) {
          setIsResetPassword(true);
          setSuccessData({ username: selectedUser.username, password: resetNewPassword });
          setShowResetModal(false);
        }
      } catch {
        // Error handled by UI state
      } finally {
        setResetting(false);
      }
    },
    [selectedUser, resetNewPassword]
  );

  const openEditModal = useCallback((user: User) => {
    setSelectedUser(user);
    setEmail(user.email);
    setRole(user.role);
    setIsActive(user.is_active);
    setShowEditModal(true);
  }, []);

  const openDeleteModal = useCallback((user: User) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
  }, []);

  const openResetModal = useCallback((user: User) => {
    setSelectedUser(user);
    setResetNewPassword(generatePassword());
    setIsResetPassword(true);
    setShowResetModal(true);
  }, []);

  return {
    // Modal visibility
    showCreateModal,
    setShowCreateModal,
    showEditModal,
    setShowEditModal,
    showDeleteModal,
    setShowDeleteModal,
    showResetModal,
    setShowResetModal,

    // Shared state
    selectedUser,
    setSelectedUser,
    successData,
    showPassword,
    setShowPassword,
    isResetPassword,
    closeSuccess,

    // Form fields
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

    // Loading states
    creating,
    saving,
    deleting,
    resetting,
    formErrors,

    // Actions
    handleCreateUser,
    handleEditUser,
    handleDeleteUser,
    handleResetPassword,
    handleGeneratePassword: () => setGeneratedPassword(generatePassword()),
    resetForm,
    openEditModal,
    openDeleteModal,
    openResetModal,
  };
}
