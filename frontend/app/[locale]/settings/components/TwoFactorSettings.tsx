"use client";

import { useState, useEffect } from "react";
import { useLocale, useTranslations } from "next-intl";
import {
  ShieldCheck,
  Shield,
  KeyRound,
  Copy,
  Check,
  Lock,
  AlertCircle,
  Download,
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/common/Button";
import { Input } from "@/components/common/Input";
import { Modal } from "@/components/common/Modal";
import { OtpInput } from "@/components/common/OtpInput";
import { useToast } from "@/components/Toast";
import { authFetchJSON, loadAuthState } from "@/lib/auth";

interface TOTPStatus {
  is_enabled: boolean;
  policy: "sudo" | "login";
}

interface TOTPSetupData {
  secret: string;
  qr_code: string;
  provisioning_uri: string;
  backup_codes: string[];
}

export function TwoFactorSettings() {
  const locale = useLocale();
  const isZh = locale.startsWith("zh");
  const t = useTranslations("twoFactor");
  const { showToast } = useToast();

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<TOTPStatus>(() => {
    if (typeof window !== "undefined") {
      const authUser = loadAuthState()?.user;
      if (authUser) {
        return {
          is_enabled: Boolean(authUser.is_totp_enabled),
          policy: (authUser.totp_policy as "sudo" | "login") || "sudo",
        };
      }
    }
    return { is_enabled: false, policy: "sudo" };
  });

  // Setup Modal Wizard State
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [setupStep, setSetupStep] = useState<1 | 2 | 3>(1);
  const [setupData, setSetupData] = useState<TOTPSetupData | null>(null);
  const [setupPolicy, setSetupPolicy] = useState<"sudo" | "login">("sudo");
  const [setupCode, setSetupCode] = useState("");
  const [setupLoading, setSetupLoading] = useState(false);
  const [setupError, setSetupError] = useState("");
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedBackup, setCopiedBackup] = useState(false);
  const [showManualKey, setShowManualKey] = useState(false);

  // Policy Switch Modal State
  const [showPolicyModal, setShowPolicyModal] = useState(false);
  const [targetPolicy, setTargetPolicy] = useState<"sudo" | "login">("sudo");
  const [policyCode, setPolicyCode] = useState("");
  const [policyLoading, setPolicyLoading] = useState(false);
  const [policyError, setPolicyError] = useState("");

  // Disable Modal State
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [disableLoading, setDisableLoading] = useState(false);
  const [disableError, setDisableError] = useState("");

  const fetchStatus = async () => {
    try {
      const data = await authFetchJSON<TOTPStatus>("/api/v1/auth/2fa/status");
      setStatus(data);
    } catch (err: unknown) {
      console.error("Failed to fetch 2FA status:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  // Initiate Setup Wizard
  const handleStartSetup = async () => {
    setSetupError("");
    setSetupCode("");
    setSetupStep(1);
    setSetupPolicy("sudo");
    setShowManualKey(false);
    setSetupLoading(true);
    try {
      const data = await authFetchJSON<TOTPSetupData>("/api/v1/auth/2fa/setup", {
        method: "POST",
      });
      setSetupData(data);
      setShowSetupModal(true);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : t("errorGeneric"), "error");
    } finally {
      setSetupLoading(false);
    }
  };

  // Submit Enable (Step 3)
  const handleEnable2FA = async (submittedCode?: string) => {
    const codeToVerify = (submittedCode || setupCode).trim();
    if (!setupData || !codeToVerify) return;

    setSetupError("");
    setSetupLoading(true);
    try {
      const res = await authFetchJSON<TOTPStatus>("/api/v1/auth/2fa/enable", {
        method: "POST",
        body: JSON.stringify({
          secret: setupData.secret,
          code: codeToVerify,
          policy: setupPolicy,
          backup_codes: setupData.backup_codes,
        }),
      });
      setStatus(res);
      setShowSetupModal(false);
      showToast(t("setupSuccess"), "success");
    } catch (err: unknown) {
      setSetupError(err instanceof Error ? err.message : t("errorGeneric"));
    } finally {
      setSetupLoading(false);
    }
  };

  // Policy selection
  const handleSelectPolicy = (newPolicy: "sudo" | "login") => {
    if (newPolicy === status.policy) return;
    setTargetPolicy(newPolicy);
    setPolicyCode("");
    setPolicyError("");
    setShowPolicyModal(true);
  };

  // Submit Policy Switch
  const handleConfirmPolicySwitch = async (submittedCode?: string) => {
    const code = (submittedCode || policyCode).trim();
    if (!code) return;

    setPolicyError("");
    setPolicyLoading(true);
    try {
      const res = await authFetchJSON<TOTPStatus>("/api/v1/auth/2fa/policy", {
        method: "POST",
        body: JSON.stringify({
          policy: targetPolicy,
          code: code,
        }),
      });
      setStatus(res);
      setShowPolicyModal(false);
      showToast(
        t("policySwitchedSuccess", {
          policy: targetPolicy === "sudo" ? t("sudoMode") : t("loginMode"),
        }),
        "success"
      );
    } catch (err: unknown) {
      setPolicyError(err instanceof Error ? err.message : t("errorGeneric"));
    } finally {
      setPolicyLoading(false);
    }
  };

  // Submit Disable
  const handleDisable2FA = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!disablePassword || !disableCode.trim()) return;

    setDisableError("");
    setDisableLoading(true);
    try {
      const res = await authFetchJSON<TOTPStatus>("/api/v1/auth/2fa/disable", {
        method: "POST",
        body: JSON.stringify({
          password: disablePassword,
          code: disableCode.trim(),
        }),
      });
      setStatus(res);
      setShowDisableModal(false);
      setDisablePassword("");
      setDisableCode("");
      showToast(t("disableSuccess"), "success");
    } catch (err: unknown) {
      setDisableError(err instanceof Error ? err.message : t("errorGeneric"));
    } finally {
      setDisableLoading(false);
    }
  };

  // Copy helper
  const copyToClipboard = (text: string, isSecret = false) => {
    navigator.clipboard.writeText(text);
    if (isSecret) {
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
      showToast(t("secretCopied"), "success");
    } else {
      setCopiedBackup(true);
      setTimeout(() => setCopiedBackup(false), 2000);
      showToast(t("backupCodesCopied"), "success");
    }
  };

  // Download backup codes file
  const downloadBackupCodes = () => {
    if (!setupData?.backup_codes) return;
    const content = [
      "============================================================",
      "SOC Copilot - Two-Factor Authentication Emergency Backup Codes",
      `Generated on: ${new Date().toLocaleString()}`,
      "============================================================",
      "",
      "IMPORTANT NOTICE:",
      "- Each code can be used ONCE to log in if you lose your authenticator.",
      "- Store this file securely in a password manager or secure vault.",
      "",
      ...setupData.backup_codes.map((code, idx) => `  [${idx + 1}]  ${code}`),
      "",
      "============================================================",
    ].join("\n");

    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `soc-copilot-backup-codes-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(isZh ? "备用恢复码文件已下载" : "Backup codes file downloaded", "success");
  };

  if (loading) {
    return (
      <div className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-8 animate-pulse space-y-4 shadow-subtle">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gray-200 dark:bg-gray-800" />
          <div className="space-y-2 flex-1">
            <div className="h-5 w-48 bg-gray-200 dark:bg-gray-800 rounded-md" />
            <div className="h-4 w-72 bg-gray-100 dark:bg-gray-800/60 rounded-md" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-gray-200/90 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm overflow-hidden transition-colors duration-150">
      {/* 2FA Main Banner */}
      {!status.is_enabled ? (
        /* ================= UNPROTECTED / DISABLED STATE ================= */
        <div className="divide-y divide-gray-100 dark:divide-gray-800/80">
          {/* Top Hero Banner */}
          <div className="p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5 min-w-0">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 border border-amber-200/80 dark:border-amber-800/60">
                <Shield className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                    {t("badgeSecurity")}
                  </span>
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100/90 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300 border border-amber-200/80 dark:border-amber-800/80">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                    {t("statusDisabled")}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white tracking-tight">
                  {t("title")}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                  {t("description")}
                </p>
              </div>
            </div>

            {/* Primary Action Button */}
            <button
              type="button"
              onClick={handleStartSetup}
              disabled={setupLoading}
              className="shrink-0 inline-flex items-center justify-center gap-2 px-4 h-10 rounded-lg text-sm font-semibold text-white bg-accent-600 hover:bg-accent-700 transition-colors duration-150 disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900"
            >
              {setupLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <KeyRound className="w-4 h-4" />
              )}
              <span className="whitespace-nowrap">
                {setupLoading ? (isZh ? "正在初始化..." : "Initializing...") : t("enableButton")}
              </span>
            </button>
          </div>

          {/* Feature highlights now live inside the setup wizard to keep this surface compact */}
        </div>
      ) : (
        /* ================= ACTIVE / ENABLED STATE ================= */
        <div className="divide-y divide-gray-100 dark:divide-gray-800/80">
          {/* Top Hero Banner */}
          <div className="p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5 min-w-0">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200/80 dark:border-emerald-800/60">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                    {t("badgeSecurity")}
                  </span>
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    {t("statusProtected")}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white tracking-tight">
                  {t("title")}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                  {t("description")}
                </p>
              </div>
            </div>

            {/* Enabled Actions */}
            <div className="shrink-0 flex flex-col items-start lg:items-end justify-center gap-2.5">
              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={handleStartSetup}
                  disabled={setupLoading}
                  className="group inline-flex items-center gap-2 px-4 h-10 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-750 transition-all shadow-subtle hover:shadow-subtle active:scale-[0.98] cursor-pointer"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 text-gray-500 dark:text-gray-400 group-hover:rotate-45 transition-transform ${setupLoading ? "animate-spin" : ""}`}
                  />
                  <span>{t("reconfigure")}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDisableError("");
                    setDisablePassword("");
                    setDisableCode("");
                    setShowDisableModal(true);
                  }}
                  className="inline-flex items-center gap-2 px-4 h-10 rounded-xl text-xs font-semibold text-red-600 dark:text-red-400 bg-red-50/60 dark:bg-red-950/20 border border-red-200/80 dark:border-red-900/40 hover:bg-red-100/70 dark:hover:bg-red-900/30 transition-all shadow-subtle active:scale-[0.98] cursor-pointer"
                >
                  <span>{t("disableButton")}</span>
                </button>
              </div>
              {/* 运行状态已由标题旁的徽章表达，不再重复占位 */}
            </div>
          </div>

          {/* Policy Management Grid */}
          <div className="p-6 sm:p-8 space-y-6">
            <div>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-gray-900 dark:text-white">
                    {t("currentPolicy")}
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {t("policyHint")}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                {/* Sudo Mode Option */}
                <div
                  onClick={() => handleSelectPolicy("sudo")}
                  className={`group relative rounded-2xl border p-5 cursor-pointer transition-all duration-150 ${
                    status.policy === "sudo"
                      ? "bg-accent-50/15 dark:bg-accent-950/20 border-accent-500 ring-2 ring-accent-500/20 shadow-subtle"
                      : "bg-white dark:bg-gray-900/70 border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors ${
                          status.policy === "sudo"
                            ? "border-accent-600 bg-accent-600 text-white"
                            : "border-gray-300 dark:border-gray-600 group-hover:border-gray-400"
                        }`}
                      >
                        {status.policy === "sudo" && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                      <div>
                        <span className="text-sm font-bold text-gray-900 dark:text-white block">
                          {t("sudoMode")}
                        </span>
                        <span className="text-[10px] font-semibold text-accent-600 dark:text-accent-400">
                          {t("sudoTag")}
                        </span>
                      </div>
                    </div>
                    {status.policy === "sudo" && (
                      <span className="text-xs font-bold text-accent-700 dark:text-accent-300 bg-accent-100/80 dark:bg-accent-950/70 px-2.5 py-0.5 rounded-full border border-accent-200 dark:border-accent-800">
                        {t("currentlyActive")}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-3 leading-relaxed pl-8">
                    {t("sudoModeDesc")}
                  </p>
                </div>

                {/* Login Protection Mode Option */}
                <div
                  onClick={() => handleSelectPolicy("login")}
                  className={`group relative rounded-2xl border p-5 cursor-pointer transition-all duration-150 ${
                    status.policy === "login"
                      ? "bg-accent-50/15 dark:bg-accent-950/20 border-accent-500 ring-2 ring-accent-500/20 shadow-subtle"
                      : "bg-white dark:bg-gray-900/70 border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors ${
                          status.policy === "login"
                            ? "border-accent-600 bg-accent-600 text-white"
                            : "border-gray-300 dark:border-gray-600 group-hover:border-gray-400"
                        }`}
                      >
                        {status.policy === "login" && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                      <div>
                        <span className="text-sm font-bold text-gray-900 dark:text-white block">
                          {t("loginMode")}
                        </span>
                        <span className="text-[10px] font-semibold text-indigo-600 dark:text-indigo-400">
                          {t("loginTag")}
                        </span>
                      </div>
                    </div>
                    {status.policy === "login" && (
                      <span className="text-xs font-bold text-accent-700 dark:text-accent-300 bg-accent-100/80 dark:bg-accent-950/70 px-2.5 py-0.5 rounded-full border border-accent-200 dark:border-accent-800">
                        {t("currentlyActive")}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-3 leading-relaxed pl-8">
                    {t("loginModeDesc")}
                  </p>
                </div>
              </div>
            </div>

            {/* Emergency Recovery Codes Box */}
            <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-900/40 p-4.5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400 border border-indigo-200/80 dark:border-indigo-900/50 flex items-center justify-center shrink-0">
                  <Lock className="w-4.5 h-4.5" />
                </div>
                <div>
                  <h5 className="text-xs font-bold text-gray-900 dark:text-white">
                    {t("recoveryCodesReadyTitle")}
                  </h5>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">
                    {t("recoveryCodesReadyDesc")}
                  </p>
                </div>
              </div>
              <div className="shrink-0 flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={downloadBackupCodes}
                  className="gap-1.5 text-xs text-accent-600 dark:text-accent-400 border-accent-200 dark:border-accent-900/40 hover:bg-accent-50 dark:hover:bg-accent-950/20"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>{t("downloadCodesFile")}</span>
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================== */}
      {/* 🚀 Modern Multi-Step 2FA Setup Wizard Dialog                */}
      {/* ========================================================== */}
      <Modal
        open={showSetupModal}
        onClose={() => setShowSetupModal(false)}
        title={
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-accent-600 to-indigo-600 text-white flex items-center justify-center shadow-subtle">
              <ShieldCheck className="w-4.5 h-4.5" />
            </div>
            <div>
              <div className="text-base font-bold text-gray-900 dark:text-white">
                {t("setupModalTitle")}
              </div>
              <div className="text-[11px] text-text-tertiary font-normal">
                {isZh ? "基于 RFC 6238 TOTP 工业级认证协议" : "Industry standard RFC 6238 TOTP"}
              </div>
            </div>
          </div>
        }
        size="lg"
      >
        {setupData && (
          <div className="space-y-6 pt-2 pb-1">
            {/* Top Stepper Indicator */}
            <div className="flex items-center justify-between px-2 sm:px-6">
              {/* Step 1 Indicator */}
              <div className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    setupStep > 1
                      ? "bg-emerald-500 text-white"
                      : setupStep === 1
                        ? "bg-accent-600 text-white ring-4 ring-accent-500/20 shadow-sm"
                        : "bg-gray-100 dark:bg-gray-800 text-text-tertiary"
                  }`}
                >
                  {setupStep > 1 ? <Check className="w-3.5 h-3.5" /> : "1"}
                </div>
                <span
                  className={`text-xs font-semibold ${
                    setupStep === 1
                      ? "text-gray-900 dark:text-white"
                      : "text-text-tertiary dark:text-gray-500"
                  }`}
                >
                  {isZh ? "扫码绑定" : "Scan QR"}
                </span>
              </div>

              <div
                className={`flex-1 h-0.5 mx-3 transition-colors ${
                  setupStep > 1 ? "bg-emerald-500" : "bg-gray-200 dark:bg-gray-700"
                }`}
              />

              {/* Step 2 Indicator */}
              <div className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    setupStep > 2
                      ? "bg-emerald-500 text-white"
                      : setupStep === 2
                        ? "bg-accent-600 text-white ring-4 ring-accent-500/20 shadow-sm"
                        : "bg-gray-100 dark:bg-gray-800 text-text-tertiary"
                  }`}
                >
                  {setupStep > 2 ? <Check className="w-3.5 h-3.5" /> : "2"}
                </div>
                <span
                  className={`text-xs font-semibold ${
                    setupStep === 2
                      ? "text-gray-900 dark:text-white"
                      : "text-text-tertiary dark:text-gray-500"
                  }`}
                >
                  {isZh ? "模式与备用码" : "Policy & Codes"}
                </span>
              </div>

              <div
                className={`flex-1 h-0.5 mx-3 transition-colors ${
                  setupStep > 2 ? "bg-emerald-500" : "bg-gray-200 dark:bg-gray-700"
                }`}
              />

              {/* Step 3 Indicator */}
              <div className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    setupStep === 3
                      ? "bg-accent-600 text-white ring-4 ring-accent-500/20 shadow-sm"
                      : "bg-gray-100 dark:bg-gray-800 text-text-tertiary"
                  }`}
                >
                  3
                </div>
                <span
                  className={`text-xs font-semibold ${
                    setupStep === 3
                      ? "text-gray-900 dark:text-white"
                      : "text-text-tertiary dark:text-gray-500"
                  }`}
                >
                  {isZh ? "验证激活" : "Verify"}
                </span>
              </div>
            </div>

            {/* Error Message Alert */}
            {setupError && (
              <div className="p-3.5 rounded-xl bg-danger-500/10 border border-danger-500/25 flex items-start gap-2.5 text-danger-700 dark:text-danger-400 text-xs animate-fade-in">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span className="leading-snug">{setupError}</span>
              </div>
            )}

            {/* ======================================================== */}
            {/* STEP 1: SCAN QR CODE                                      */}
            {/* ======================================================== */}
            {setupStep === 1 && (
              <div className="space-y-4 animate-fade-in">
                <div className="text-center max-w-md mx-auto">
                  <h4 className="text-sm font-bold text-gray-900 dark:text-white">
                    {isZh
                      ? "使用认证器应用扫描下方二维码"
                      : "Scan the QR code with your authenticator"}
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{t("step1Desc")}</p>
                </div>

                {/* Framed QR Container with Scan Corner Guides */}
                <div className="flex flex-col items-center justify-center p-6 bg-gradient-to-b from-gray-50/80 via-white to-gray-50/80 dark:from-gray-900/60 dark:via-gray-800 dark:to-gray-900/60 rounded-2xl border border-gray-200/80 dark:border-gray-800 shadow-inner">
                  <div className="relative p-3.5 bg-white rounded-2xl shadow-md border border-gray-200/90 ring-4 ring-black/[0.02]">
                    {/* Modern scanner corner brackets */}
                    <div className="absolute top-1.5 left-1.5 w-3.5 h-3.5 border-t-2 border-l-2 border-accent-500 rounded-tl-sm pointer-events-none" />
                    <div className="absolute top-1.5 right-1.5 w-3.5 h-3.5 border-t-2 border-r-2 border-accent-500 rounded-tr-sm pointer-events-none" />
                    <div className="absolute bottom-1.5 left-1.5 w-3.5 h-3.5 border-b-2 border-l-2 border-accent-500 rounded-bl-sm pointer-events-none" />
                    <div className="absolute bottom-1.5 right-1.5 w-3.5 h-3.5 border-b-2 border-r-2 border-accent-500 rounded-br-sm pointer-events-none" />

                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={setupData.qr_code}
                      alt="TOTP QR Code"
                      className="w-40 h-40 object-contain rounded-lg"
                    />
                  </div>

                  {/* Supported Apps Badges */}
                  <div className="flex flex-wrap items-center justify-center gap-1.5 mt-4 text-[10px] text-gray-500 dark:text-gray-400">
                    <span className="px-2 py-0.5 rounded-md bg-white dark:bg-gray-800 border border-gray-200/70 dark:border-gray-700 font-medium">
                      Google Authenticator
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-white dark:bg-gray-800 border border-gray-200/70 dark:border-gray-700 font-medium">
                      Microsoft Authenticator
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-white dark:bg-gray-800 border border-gray-200/70 dark:border-gray-700 font-medium">
                      1Password
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-white dark:bg-gray-800 border border-gray-200/70 dark:border-gray-700 font-medium">
                      Bitwarden
                    </span>
                  </div>
                </div>

                {/* Collapsible Manual Key Section */}
                <div className="rounded-xl border border-gray-200/80 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-900/30 p-3.5 transition-all">
                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      onClick={() => setShowManualKey(!showManualKey)}
                      className="text-xs font-semibold text-accent-600 dark:text-accent-400 hover:text-accent-700 flex items-center gap-1 transition-colors"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>
                        {showManualKey
                          ? isZh
                            ? "收起手动输入密钥"
                            : "Hide manual key"
                          : isZh
                            ? "无法扫码？点击查看密钥"
                            : "Can't scan? Enter key manually"}
                      </span>
                    </button>
                    {showManualKey && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(setupData.secret, true)}
                        className="text-xs h-7 gap-1"
                      >
                        {copiedSecret ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                            <span className="text-emerald-600 dark:text-emerald-400">
                              {t("copied")}
                            </span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5 text-gray-500" />
                            <span>{isZh ? "复制密钥" : "Copy Key"}</span>
                          </>
                        )}
                      </Button>
                    )}
                  </div>

                  {showManualKey && (
                    <div className="mt-2.5 pt-2.5 border-t border-gray-200/60 dark:border-gray-700/60 flex items-center gap-2">
                      <code className="flex-1 text-xs font-mono tracking-widest bg-white dark:bg-gray-800 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 select-all font-semibold break-all text-center">
                        {setupData.secret.match(/.{1,4}/g)?.join(" ") || setupData.secret}
                      </code>
                    </div>
                  )}
                </div>

                {/* Step 1 Actions */}
                <div className="pt-4 mt-2 flex items-center justify-end gap-3 border-t border-gray-100 dark:border-gray-800">
                  <button
                    type="button"
                    onClick={() => setShowSetupModal(false)}
                    className="h-10 px-4 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-100/90 hover:bg-gray-200/90 dark:bg-gray-800 dark:hover:bg-gray-750 border border-gray-200/80 dark:border-gray-700 transition-all active:scale-[0.98] cursor-pointer inline-flex items-center gap-1.5 whitespace-nowrap shadow-subtle"
                  >
                    <span>{t("cancel")}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSetupError("");
                      setSetupStep(2);
                    }}
                    className="group relative h-10 px-5 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-accent-600 via-indigo-600 to-accent-600 bg-[length:200%_auto] hover:bg-right transition-all duration-300 shadow-md shadow-accent-600/20 hover:shadow-lg hover:shadow-accent-600/30 active:scale-[0.98] cursor-pointer whitespace-nowrap inline-flex items-center gap-2 border border-white/10"
                  >
                    <span>{isZh ? "下一步：安全模式与备用码" : "Next: Policy & Backup"}</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform duration-200 group-hover:translate-x-0.5 opacity-80" />
                  </button>
                </div>
              </div>
            )}

            {/* ======================================================== */}
            {/* STEP 2: POLICY & BACKUP RECOVERY CODES                    */}
            {/* ======================================================== */}
            {setupStep === 2 && (
              <div className="space-y-5 animate-fade-in">
                {/* 1. Policy Selection */}
                <div>
                  <h5 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-2">
                    {isZh ? "1. 选择双因素认证策略" : "1. Choose Authentication Policy"}
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {/* Sudo Mode */}
                    <div
                      onClick={() => setSetupPolicy("sudo")}
                      className={`relative rounded-xl border p-3.5 cursor-pointer transition-all ${
                        setupPolicy === "sudo"
                          ? "bg-accent-50/20 dark:bg-accent-950/20 border-accent-500 ring-2 ring-accent-500/20 shadow-subtle"
                          : "bg-white dark:bg-gray-800/60 border-gray-200 dark:border-gray-700 hover:border-gray-300"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div
                            className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                              setupPolicy === "sudo"
                                ? "border-accent-600 bg-accent-600 text-white"
                                : "border-gray-300 dark:border-gray-600"
                            }`}
                          >
                            {setupPolicy === "sudo" && (
                              <div className="w-1.5 h-1.5 rounded-full bg-white" />
                            )}
                          </div>
                          <span className="text-xs font-bold text-gray-900 dark:text-white">
                            {t("sudoMode")}
                          </span>
                        </div>
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                          {isZh ? "推荐" : "Recommended"}
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-2 leading-relaxed pl-6">
                        {t("sudoModeDesc")}
                      </p>
                    </div>

                    {/* Login Mode */}
                    <div
                      onClick={() => setSetupPolicy("login")}
                      className={`relative rounded-xl border p-3.5 cursor-pointer transition-all ${
                        setupPolicy === "login"
                          ? "bg-accent-50/20 dark:bg-accent-950/20 border-accent-500 ring-2 ring-accent-500/20 shadow-subtle"
                          : "bg-white dark:bg-gray-800/60 border-gray-200 dark:border-gray-700 hover:border-gray-300"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div
                            className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                              setupPolicy === "login"
                                ? "border-accent-600 bg-accent-600 text-white"
                                : "border-gray-300 dark:border-gray-600"
                            }`}
                          >
                            {setupPolicy === "login" && (
                              <div className="w-1.5 h-1.5 rounded-full bg-white" />
                            )}
                          </div>
                          <span className="text-xs font-bold text-gray-900 dark:text-white">
                            {t("loginMode")}
                          </span>
                        </div>
                      </div>
                      <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-2 leading-relaxed pl-6">
                        {t("loginModeDesc")}
                      </p>
                    </div>
                  </div>
                </div>

                {/* 2. Emergency Backup Codes Card */}
                <div className="rounded-xl border border-gray-200 dark:border-gray-700/80 bg-gray-50/80 dark:bg-gray-900/40 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Lock className="w-4 h-4 text-accent-600 dark:text-accent-400" />
                      <h5 className="text-xs font-bold text-gray-900 dark:text-white">
                        {isZh
                          ? "2. 紧急恢复备用码 (一次性有效)"
                          : "2. Emergency Backup Codes (Single Use)"}
                      </h5>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(setupData.backup_codes.join("\n"))}
                        className="text-xs h-7 gap-1"
                      >
                        {copiedBackup ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                            <span className="text-emerald-600 dark:text-emerald-400">
                              {t("copied")}
                            </span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5 text-gray-500" />
                            <span>{isZh ? "复制全部" : "Copy All"}</span>
                          </>
                        )}
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={downloadBackupCodes}
                        className="text-xs h-7 gap-1 text-accent-600 dark:text-accent-400"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>{isZh ? "下载 .txt" : "Download .txt"}</span>
                      </Button>
                    </div>
                  </div>

                  <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed">
                    {t("step3Desc")}
                  </p>

                  {/* 8 Codes Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                    {setupData.backup_codes.map((code, idx) => (
                      <div
                        key={idx}
                        className="text-center font-mono text-xs font-bold tracking-wider text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-800 py-1.5 px-2.5 rounded-lg border border-gray-200/80 dark:border-gray-700 shadow-subtle select-all"
                      >
                        {code}
                      </div>
                    ))}
                  </div>

                  <div className="p-2.5 rounded-lg bg-amber-50/80 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 flex items-start gap-2 text-[11px] text-amber-800 dark:text-amber-300">
                    <ShieldAlert className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    <span>
                      {isZh
                        ? "请务必妥善保存上述恢复码。若您的认证器设备丢失或损坏，备用码是唯一能够恢复账户访问权限的凭证。"
                        : "Please save these codes safely. If you lose your device, these codes are the only way to recover access."}
                    </span>
                  </div>
                </div>

                {/* Step 2 Actions */}
                <div className="pt-4 mt-2 flex items-center justify-between gap-3 border-t border-gray-100 dark:border-gray-800">
                  <button
                    type="button"
                    onClick={() => setSetupStep(1)}
                    className="h-10 px-4 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-100/90 hover:bg-gray-200/90 dark:bg-gray-800 dark:hover:bg-gray-750 border border-gray-200/80 dark:border-gray-700 transition-all active:scale-[0.98] cursor-pointer inline-flex items-center gap-1.5 whitespace-nowrap shadow-subtle"
                  >
                    <ArrowLeft className="w-3.5 h-3.5 opacity-70" />
                    <span>{isZh ? "返回上一步" : "Back"}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSetupError("");
                      setSetupStep(3);
                    }}
                    className="group relative h-10 px-5 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-accent-600 via-indigo-600 to-accent-600 bg-[length:200%_auto] hover:bg-right transition-all duration-300 shadow-md shadow-accent-600/20 hover:shadow-lg hover:shadow-accent-600/30 active:scale-[0.98] cursor-pointer whitespace-nowrap inline-flex items-center gap-2 border border-white/10"
                  >
                    <span>{isZh ? "下一步：验证激活" : "Next: Verify & Activate"}</span>
                    <ArrowRight className="w-3.5 h-3.5 transition-transform duration-200 group-hover:translate-x-0.5 opacity-80" />
                  </button>
                </div>
              </div>
            )}

            {/* ======================================================== */}
            {/* STEP 3: VERIFY WITH 6-DIGIT OTP CELLS                     */}
            {/* ======================================================== */}
            {setupStep === 3 && (
              <div className="space-y-6 py-2 animate-fade-in text-center">
                <div className="space-y-2 max-w-md mx-auto">
                  <div className="w-12 h-12 mx-auto rounded-2xl bg-gradient-to-tr from-accent-600 to-indigo-600 text-white flex items-center justify-center shadow-md ring-4 ring-accent-500/10">
                    <KeyRound className="w-6 h-6" />
                  </div>
                  <h4 className="text-base font-bold text-gray-900 dark:text-white">
                    {isZh ? "输入 6 位动态验证码完成激活" : "Enter the 6-digit verification code"}
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                    {isZh
                      ? "打开您刚绑定的认证器 App，输入为当前 SOC Copilot 账号生成的 6 位实时数字口令："
                      : "Open your authenticator app and enter the 6-digit code for SOC Copilot:"}
                  </p>
                </div>

                {/* 6-Digit Segmented OtpInput */}
                <div className="py-2">
                  <OtpInput
                    value={setupCode}
                    onChange={setSetupCode}
                    onComplete={(code) => handleEnable2FA(code)}
                    disabled={setupLoading}
                    autoFocus
                    error={Boolean(setupError)}
                  />
                </div>

                <div className="text-[11px] text-text-tertiary dark:text-gray-500">
                  {isZh
                    ? "💡 动态验证码每 30 秒自动更新一次，支持直接复制粘贴"
                    : "💡 Codes refresh every 30 seconds. Paste is supported."}
                </div>

                {/* Step 3 Actions */}
                <div className="pt-4 mt-2 flex items-center justify-between gap-3 border-t border-gray-100 dark:border-gray-800">
                  <button
                    type="button"
                    onClick={() => setSetupStep(2)}
                    disabled={setupLoading}
                    className="h-10 px-4 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-100/90 hover:bg-gray-200/90 dark:bg-gray-800 dark:hover:bg-gray-750 border border-gray-200/80 dark:border-gray-700 transition-all active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none cursor-pointer inline-flex items-center gap-1.5 whitespace-nowrap shadow-subtle"
                  >
                    <ArrowLeft className="w-3.5 h-3.5 opacity-70" />
                    <span>{isZh ? "返回上一步" : "Back"}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleEnable2FA()}
                    disabled={setupLoading || setupCode.length !== 6}
                    className="group relative h-10 px-6 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-accent-600 via-indigo-600 to-accent-600 bg-[length:200%_auto] hover:bg-right transition-all duration-300 shadow-md shadow-accent-600/20 hover:shadow-lg hover:shadow-accent-600/30 active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none cursor-pointer whitespace-nowrap inline-flex items-center justify-center gap-2 border border-white/10 min-w-[140px]"
                  >
                    {setupLoading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>{t("activating")}</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="w-4 h-4 text-white" />
                        <span>{t("verifyAndActivate")}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* ========================================================== */}
      {/* 🔄 Switch Policy Modal with Modern OTP Input                */}
      {/* ========================================================== */}
      <Modal
        open={showPolicyModal}
        onClose={() => setShowPolicyModal(false)}
        title={
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent-600" />
            <span>{t("switchPolicyModalTitle")}</span>
          </div>
        }
        size="md"
      >
        <div className="space-y-4 py-2">
          {policyError && (
            <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/25 flex items-start gap-2.5 text-danger-700 dark:text-danger-400 text-xs">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{policyError}</span>
            </div>
          )}

          <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
            {t("switchPolicyModalDesc")}
          </p>

          <div className="p-3.5 rounded-xl bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 text-xs flex items-center justify-between">
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {t("targetPolicyLabel")}
            </span>
            <span className="font-bold text-accent-600 dark:text-accent-400 px-2 py-0.5 bg-accent-50 dark:bg-accent-950/40 rounded-full border border-accent-200 dark:border-accent-800">
              {targetPolicy === "sudo" ? t("sudoMode") : t("loginMode")}
            </span>
          </div>

          <div className="space-y-2 pt-1">
            <label className="block text-xs font-semibold text-center text-gray-700 dark:text-gray-300">
              {isZh ? "输入 6 位动态验证码确认切换" : "Enter 6-digit code to confirm"}
            </label>
            <OtpInput
              value={policyCode}
              onChange={setPolicyCode}
              onComplete={(code) => handleConfirmPolicySwitch(code)}
              disabled={policyLoading}
              autoFocus
              error={Boolean(policyError)}
            />
          </div>

          <div className="pt-4 mt-2 flex items-center justify-end gap-3 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={() => setShowPolicyModal(false)}
              disabled={policyLoading}
              className="h-10 px-4 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-100/90 hover:bg-gray-200/90 dark:bg-gray-800 dark:hover:bg-gray-750 border border-gray-200/80 dark:border-gray-700 transition-all active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none cursor-pointer inline-flex items-center gap-1.5 whitespace-nowrap shadow-subtle"
            >
              <span>{t("cancel")}</span>
            </button>
            <button
              type="button"
              onClick={() => handleConfirmPolicySwitch()}
              disabled={policyLoading || policyCode.length !== 6}
              className="group relative h-10 px-5 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-accent-600 via-indigo-600 to-accent-600 bg-[length:200%_auto] hover:bg-right transition-all duration-300 shadow-md shadow-accent-600/20 hover:shadow-lg hover:shadow-accent-600/30 active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none cursor-pointer whitespace-nowrap inline-flex items-center justify-center gap-2 border border-white/10"
            >
              {policyLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>{t("switching")}</span>
                </>
              ) : (
                <span>{t("confirmSwitch")}</span>
              )}
            </button>
          </div>
        </div>
      </Modal>

      {/* ========================================================== */}
      {/* ⚠️ Disable 2FA Modal with Modern Danger UX                  */}
      {/* ========================================================== */}
      <Modal
        open={showDisableModal}
        onClose={() => setShowDisableModal(false)}
        title={
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <ShieldAlert className="w-5 h-5" />
            <span>{t("disableModalTitle")}</span>
          </div>
        }
        size="md"
      >
        <form onSubmit={handleDisable2FA} className="space-y-4 py-2">
          {disableError && (
            <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/25 flex items-start gap-2.5 text-danger-700 dark:text-danger-400 text-xs">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{disableError}</span>
            </div>
          )}

          <div className="p-3 rounded-xl bg-red-50/80 dark:bg-red-950/20 border border-red-200/60 dark:border-red-900/40 text-xs text-red-700 dark:text-red-300 leading-relaxed">
            {t("disableModalDesc")}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              {t("passwordLabel")}
            </label>
            <Input
              id="disablePassword"
              name="disablePassword"
              type="password"
              required
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              placeholder={t("passwordPlaceholder")}
              leftIcon={<Lock className="w-4 h-4 text-text-muted" />}
              autoFocus
            />
          </div>

          <div className="space-y-2 pt-1">
            <label className="block text-xs font-semibold text-center text-gray-700 dark:text-gray-300">
              {isZh ? "输入 6 位动态验证码确认关闭" : "Enter 6-digit code to confirm"}
            </label>
            <OtpInput
              value={disableCode}
              onChange={setDisableCode}
              disabled={disableLoading}
              error={Boolean(disableError)}
            />
          </div>

          <div className="pt-4 mt-2 flex items-center justify-end gap-3 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={() => setShowDisableModal(false)}
              disabled={disableLoading}
              className="h-10 px-4 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-100/90 hover:bg-gray-200/90 dark:bg-gray-800 dark:hover:bg-gray-750 border border-gray-200/80 dark:border-gray-700 transition-all active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none cursor-pointer inline-flex items-center gap-1.5 whitespace-nowrap shadow-subtle"
            >
              <span>{t("cancel")}</span>
            </button>
            <button
              type="submit"
              disabled={disableLoading || !disablePassword || disableCode.length !== 6}
              className="group relative h-10 px-5 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-red-600 via-rose-600 to-red-600 bg-[length:200%_auto] hover:bg-right transition-all duration-300 shadow-md shadow-red-600/20 hover:shadow-lg hover:shadow-red-600/30 active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none cursor-pointer whitespace-nowrap inline-flex items-center justify-center gap-2 border border-white/10"
            >
              {disableLoading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>{t("disabling")}</span>
                </>
              ) : (
                <span>{t("confirmDisable")}</span>
              )}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
