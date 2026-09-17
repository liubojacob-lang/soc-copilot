"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import {
  X,
  Download,
  Star,
  CheckCircle,
  Tag,
  Cpu,
  Layers,
  BookOpen,
  FileText,
  User,
  GitBranch,
  ShieldCheck,
  Check,
} from "lucide-react";
import { apiClient as api } from "@/lib/api";
import { useFocusTrap } from "@/hooks/useFocusTrap";

export interface MarketplacePlaybookSummary {
  id: string;
  name: string;
  description: string | null;
  category: string;
  difficulty: "beginner" | "intermediate" | "advanced" | string;
  rating_average: number;
  rating_count: number;
  download_count: number;
  verified: boolean;
  author?: string;
  author_name?: string;
  version?: string;
  tags?: string[];
}

export interface MarketplacePlaybookDetailFull extends MarketplacePlaybookSummary {
  dag_json?: {
    nodes?: Array<{ id: string; type: string; name?: string; label?: string }>;
    edges?: Array<{ id?: string; source: string; target: string }>;
  };
  documentation?: string | null;
  required_plugins?: string[];
  compatible_versions?: string[];
  review_count?: number;
}

interface PlaybookDetailsDrawerProps {
  playbookId?: string | null;
  playbook?: MarketplacePlaybookSummary | null;
  isOpen: boolean;
  onClose: () => void;
  onDownload: (id: string) => Promise<void>;
  isDownloading: boolean;
}

export function PlaybookDetailsDrawer({
  playbookId,
  playbook,
  isOpen,
  onClose,
  onDownload,
  isDownloading,
}: PlaybookDetailsDrawerProps) {
  const t = useTranslations("marketplace");
  const tCommon = useTranslations("common");

  const [detail, setDetail] = useState<MarketplacePlaybookDetailFull | null>(null);
  const [loading, setLoading] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  const targetId = playbookId || playbook?.id || null;

  useFocusTrap(isOpen && !!targetId, onClose, drawerRef);

  // Lock background scroll when drawer is open
  useEffect(() => {
    if (!isOpen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [isOpen]);

  // Fetch full details whenever the drawer opens or targetId changes
  useEffect(() => {
    if (!isOpen || !targetId) {
      setDetail(null);
      return;
    }

    if (playbook) {
      setDetail(playbook as MarketplacePlaybookDetailFull);
    }

    if (targetId.startsWith("adapted-")) {
      return;
    }

    let active = true;
    const fetchDetail = async () => {
      setLoading(true);
      try {
        const res = await api.get<MarketplacePlaybookDetailFull>(
          `/api/marketplace/playbooks/${targetId}`
        );
        if (active && res) {
          setDetail(res);
        }
      } catch {
        // Keep initial playbook data if error
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    fetchDetail();
    return () => {
      active = false;
    };
  }, [isOpen, targetId, playbook]);

  if (!isOpen || !targetId) return null;

  const currentData: MarketplacePlaybookDetailFull = detail || (playbook as MarketplacePlaybookDetailFull) || {
    id: targetId,
    name: "Playbook",
    description: "",
    category: "",
    difficulty: "intermediate",
    rating_average: 5.0,
    rating_count: 1,
    download_count: 0,
    verified: false,
  };
  const nodes = currentData.dag_json?.nodes || [];
  const requiredPlugins = currentData.required_plugins || [];
  const tags = currentData.tags || [];

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm animate-in fade-in duration-200"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={drawerRef}
        className="w-full max-w-2xl bg-surface-card border-l border-border-subtle shadow-2xl h-full flex flex-col overflow-hidden animate-in slide-in-from-right duration-250 text-content-primary"
        role="dialog"
        aria-modal="true"
        aria-labelledby="marketplace-drawer-title"
        tabIndex={-1}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-border-subtle flex items-start justify-between gap-4 bg-surface-ground/50 shrink-0">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/40">
                {currentData.category}
              </span>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                  currentData.difficulty === "beginner"
                    ? "bg-green-50 text-green-700 border-green-200/60 dark:bg-green-950/40 dark:text-green-300 dark:border-green-800/40"
                    : currentData.difficulty === "intermediate"
                      ? "bg-yellow-50 text-yellow-700 border-yellow-200/60 dark:bg-yellow-950/40 dark:text-yellow-300 dark:border-yellow-800/40"
                      : "bg-red-50 text-red-700 border-red-200/60 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800/40"
                }`}
              >
                {currentData.difficulty === "beginner"
                  ? t("difficulty.beginner")
                  : currentData.difficulty === "intermediate"
                    ? t("difficulty.intermediate")
                    : t("difficulty.advanced")}
              </span>
              {currentData.verified && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/40">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                  {t("verifiedOnly")}
                </span>
              )}
            </div>

            <h2 id="marketplace-drawer-title" className="text-xl font-bold text-content-primary leading-snug">
              {currentData.name}
            </h2>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-content-muted hover:text-content-primary rounded-lg hover:bg-surface-ground transition-colors shrink-0"
            aria-label={tCommon("close")}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body (Scrollable) */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 bg-surface-ground rounded-xl border border-border-subtle text-xs">
            <div>
              <div className="text-content-muted flex items-center gap-1 mb-1">
                <User className="w-3.5 h-3.5" />
                <span>{t("author")}</span>
              </div>
              <div className="font-semibold text-content-primary truncate">
                {currentData.author_name || currentData.author || "Community"}
              </div>
            </div>

            <div>
              <div className="text-content-muted flex items-center gap-1 mb-1">
                <GitBranch className="w-3.5 h-3.5" />
                <span>{t("version")}</span>
              </div>
              <div className="font-semibold text-content-primary">
                v{currentData.version || "1.0.0"}
              </div>
            </div>

            <div>
              <div className="text-content-muted flex items-center gap-1 mb-1">
                <Download className="w-3.5 h-3.5" />
                <span>{tCommon("download")}</span>
              </div>
              <div className="font-semibold text-content-primary">
                {currentData.download_count || 0} 次
              </div>
            </div>

            <div>
              <div className="text-content-muted flex items-center gap-1 mb-1">
                <Star className="w-3.5 h-3.5 text-yellow-500 fill-current" />
                <span>{t("rating")}</span>
              </div>
              <div className="font-semibold text-content-primary flex items-center gap-1">
                <span>{currentData.rating_average || "5.0"}</span>
                <span className="text-content-muted text-[11px]">({currentData.rating_count || 1})</span>
              </div>
            </div>
          </div>

          {/* Description */}
          <div>
            <h3 className="text-sm font-semibold text-content-primary flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-amber-500" />
              {t("overview")}
            </h3>
            <p className="text-sm text-content-secondary leading-relaxed bg-surface-ground/30 p-3 rounded-lg border border-border-subtle">
              {currentData.description || "暂无剧本描述"}
            </p>
          </div>

          {/* Workflow Execution Steps */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-content-primary flex items-center gap-2">
                <Layers className="w-4 h-4 text-amber-500" />
                {t("executionSteps")}
              </h3>
              {nodes.length > 0 && (
                <span className="text-xs text-content-muted font-mono">
                  {t("nodesCount", { count: nodes.length })}
                </span>
              )}
            </div>

            {loading ? (
              <div className="p-4 flex items-center justify-center text-xs text-content-muted gap-2 bg-surface-ground/40 rounded-lg">
                <span className="w-4 h-4 border-2 border-amber-600/30 border-t-amber-600 rounded-full animate-spin" />
                <span>{t("loading")}</span>
              </div>
            ) : nodes.length === 0 ? (
              <p className="text-xs text-content-muted italic bg-surface-ground/30 p-3 rounded-lg border border-border-subtle">
                包含标准安全编排节点，导入后可在剧本编辑器中查看与编辑。
              </p>
            ) : (
              <div className="space-y-2 border border-border-subtle rounded-xl p-3.5 bg-surface-ground/30">
                {nodes.map((node, index) => (
                  <div key={node.id || index} className="flex items-center gap-3 text-xs">
                    <div className="w-6 h-6 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 flex items-center justify-center font-bold text-[11px] shrink-0">
                      {index + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-content-primary truncate">
                        {node.name || node.label || node.id}
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-surface-card border border-border-subtle text-content-muted font-mono text-[10px]">
                      {node.type}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Required Plugins */}
          {requiredPlugins.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-content-primary flex items-center gap-2 mb-2">
                <Cpu className="w-4 h-4 text-amber-500" />
                {t("requiredPlugins")}
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {requiredPlugins.map((plugin) => (
                  <span
                    key={plugin}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-mono bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-200/60 dark:border-blue-800/40"
                  >
                    <Check className="w-3 h-3 text-blue-500" />
                    {plugin}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Tags & Security Standards */}
          {tags.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-content-primary flex items-center gap-2 mb-2">
                <Tag className="w-4 h-4 text-amber-500" />
                {t("tags")}
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${
                      tag.startsWith("att&ck")
                        ? "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300 border border-red-200/60 dark:border-red-800/40 font-mono"
                        : tag.startsWith("standard")
                          ? "bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border border-purple-200/60 dark:border-purple-800/40 font-mono"
                          : "bg-surface-ground text-content-secondary border border-border-subtle"
                    }`}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* SOP Documentation */}
          {currentData.documentation && (
            <div>
              <h3 className="text-sm font-semibold text-content-primary flex items-center gap-2 mb-2">
                <BookOpen className="w-4 h-4 text-amber-500" />
                {t("documentation")}
              </h3>
              <div className="p-4 bg-surface-ground/50 rounded-xl border border-border-subtle text-xs text-content-secondary whitespace-pre-wrap font-sans leading-relaxed max-h-60 overflow-y-auto">
                {currentData.documentation}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-border-subtle bg-surface-ground/50 flex items-center justify-between gap-3 shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-content-secondary hover:text-content-primary hover:bg-surface-card rounded-lg border border-border-subtle transition-colors"
          >
            {tCommon("close")}
          </button>

          <button
            onClick={() => onDownload(currentData.id)}
            disabled={isDownloading}
            className="px-5 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-medium disabled:opacity-50 flex items-center gap-2 transition-colors shadow-sm"
          >
            {isDownloading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>{t("downloading")}</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>{t("downloadToLocal")}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
