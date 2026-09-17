"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import {
  X,
  Globe,
  Search,
  Sparkles,
  Link as LinkIcon,
  FileCode,
  Shield,
  Star,
  ExternalLink,
  CheckCircle,
  Loader2,
  GitFork,
  ArrowRight,
} from "lucide-react";
import { apiClient as api } from "@/lib/api";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import { useToast } from "@/components/Toast";

export interface ExternalSearchItem {
  id: string;
  title: string;
  repository: string;
  source_platform: string;
  description: string;
  stars: number;
  url: string;
  raw_url?: string;
  category: string;
  difficulty: string;
  tags: string[];
  standard?: string;
}

interface ExternalPlaybookModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdaptSuccess: (adaptedPlaybook: any) => void;
}

const PRESET_TOPICS = [
  "Cobalt Strike",
  "Phishing",
  "Ransomware",
  "Log4j",
  "AWS Root",
  "Cryptomining",
];

export function ExternalPlaybookModal({
  isOpen,
  onClose,
  onAdaptSuccess,
}: ExternalPlaybookModalProps) {
  const t = useTranslations("marketplace");
  const tCommon = useTranslations("common");
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<"search" | "direct">("search");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ExternalSearchItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Direct tab inputs
  const [directUrl, setDirectUrl] = useState("");
  const [directContent, setDirectContent] = useState("");
  const [directTitle, setDirectTitle] = useState("");
  const [sourcePlatform, setSourcePlatform] = useState("Cortex XSOAR");

  // Adapting progress
  const [isAdapting, setIsAdapting] = useState(false);
  const [adaptingTarget, setAdaptingTarget] = useState<string | null>(null);

  const modalRef = useRef<HTMLDivElement>(null);
  useFocusTrap(isOpen, onClose, modalRef);

  // Lock background scroll
  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isOpen]);

  // Initial search load
  useEffect(() => {
    if (isOpen && searchResults.length === 0) {
      handleSearch("");
    }
  }, [isOpen]);

  const handleSearch = async (queryToUse?: string) => {
    const q = queryToUse !== undefined ? queryToUse : searchQuery;
    setIsSearching(true);
    try {
      const res = await api.get<ExternalSearchItem[]>(
        `/api/marketplace/external/search?query=${encodeURIComponent(q)}`
      );
      setSearchResults(Array.isArray(res) ? res : []);
    } catch (e: any) {
      showToast(e.message || "Search failed", "error");
    } finally {
      setIsSearching(false);
    }
  };

  const handleAdapt = async (item?: ExternalSearchItem) => {
    setIsAdapting(true);
    setAdaptingTarget(item ? item.title : directTitle || "外部剧本");
    try {
      const payload = item
        ? {
            url: item.raw_url || item.url,
            title_hint: item.title,
            source_platform: item.source_platform,
          }
        : {
            url: directUrl.trim() || undefined,
            content: directContent.trim() || undefined,
            title_hint: directTitle.trim() || undefined,
            source_platform: sourcePlatform,
          };

      const res = await api.post<any>("/api/marketplace/external/adapt", payload, 90000);
      if (res && res.name) {
        showToast(t("adaptSuccess"), "success");
        onAdaptSuccess(res);
        onClose();
      } else {
        throw new Error("Invalid adapted response");
      }
    } catch (e: any) {
      showToast(e.message || t("adaptFailed"), "error");
    } finally {
      setIsAdapting(false);
      setAdaptingTarget(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !isAdapting) onClose();
      }}
    >
      <div
        ref={modalRef}
        className="w-full max-w-3xl bg-surface-card border border-border-subtle rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[88vh] animate-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
        aria-labelledby="external-modal-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-border-subtle bg-surface-ground/50 flex items-start justify-between gap-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center border border-amber-200/60 dark:border-amber-800/40">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <h2
                id="external-modal-title"
                className="text-lg font-bold text-content-primary flex items-center gap-2"
              >
                <span>{t("externalModalTitle")}</span>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-200/60 dark:border-blue-800/40">
                  AI Powered
                </span>
              </h2>
              <p className="text-xs text-content-muted mt-0.5">{t("externalModalSubtitle")}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isAdapting}
            className="p-1.5 text-content-muted hover:text-content-primary rounded-lg hover:bg-surface-ground transition-colors disabled:opacity-50"
            aria-label={tCommon("close")}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 border-b border-border-subtle flex gap-6 bg-surface-card shrink-0">
          <button
            type="button"
            onClick={() => setActiveTab("search")}
            className={`py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "search"
                ? "border-amber-500 text-amber-600 dark:text-amber-400"
                : "border-transparent text-content-muted hover:text-content-primary"
            }`}
          >
            <Globe className="w-4 h-4" />
            <span>{t("tabSearchOnline")}</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("direct")}
            className={`py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "direct"
                ? "border-amber-500 text-amber-600 dark:text-amber-400"
                : "border-transparent text-content-muted hover:text-content-primary"
            }`}
          >
            <FileCode className="w-4 h-4" />
            <span>{t("tabDirectImport")}</span>
          </button>
        </div>

        {/* Tab Content (Scrollable) */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === "search" ? (
            <div className="space-y-4">
              {/* Search Bar & Quick Tags */}
              <div className="space-y-2.5">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSearch();
                  }}
                  className="flex gap-2"
                >
                  <div className="flex-1 relative">
                    <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder={t("searchExternalPlaceholder")}
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-amber-500 dark:bg-gray-700 dark:text-white text-xs sm:text-sm"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isSearching}
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 transition-colors shrink-0 shadow-sm"
                  >
                    {isSearching ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Search className="w-3.5 h-3.5" />
                    )}
                    <span>{t("searchExternalButton")}</span>
                  </button>
                </form>

                {/* Popular Query Chips */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[11px] text-content-muted">热门场景:</span>
                  {PRESET_TOPICS.map((topic) => (
                    <button
                      key={topic}
                      type="button"
                      onClick={() => {
                        setSearchQuery(topic);
                        handleSearch(topic);
                      }}
                      className="px-2 py-0.5 rounded-full bg-surface-ground text-content-secondary hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/40 border border-border-subtle text-[11px] transition-colors"
                    >
                      {topic}
                    </button>
                  ))}
                </div>
              </div>

              {/* Results List */}
              {isSearching ? (
                <div className="py-12 flex flex-col items-center justify-center text-content-muted text-xs gap-2">
                  <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
                  <span>正在全网检索开源安全剧本库...</span>
                </div>
              ) : searchResults.length === 0 ? (
                <div className="py-12 text-center text-content-muted text-xs bg-surface-ground/40 rounded-xl border border-border-subtle p-6">
                  {t("noExternalResults")}
                </div>
              ) : (
                <div className="space-y-3">
                  {searchResults.map((item) => (
                    <div
                      key={item.id}
                      className="p-4 bg-surface-ground/60 hover:bg-surface-ground rounded-xl border border-border-subtle transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border border-purple-200/60 dark:border-purple-800/40">
                            {item.source_platform}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono text-content-muted bg-surface-card border border-border-subtle">
                            {item.repository}
                          </span>
                          {item.standard && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-200/60 dark:border-blue-800/40">
                              {item.standard}
                            </span>
                          )}
                          <div className="flex items-center gap-0.5 text-xs text-amber-500 ml-auto sm:ml-0">
                            <Star className="w-3 h-3 fill-current" />
                            <span className="text-[11px] font-semibold">{item.stars}</span>
                          </div>
                        </div>

                        <h3 className="font-semibold text-sm text-content-primary mb-1 group-hover:text-amber-600 transition-colors">
                          {item.title}
                        </h3>
                        <p className="text-xs text-content-secondary line-clamp-2 leading-relaxed mb-2">
                          {item.description}
                        </p>

                        <div className="flex items-center gap-1.5 flex-wrap">
                          {item.tags.slice(0, 3).map((tag) => (
                            <span
                              key={tag}
                              className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface-card border border-border-subtle text-content-muted"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-border-subtle">
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                          className="p-2 text-content-muted hover:text-content-primary rounded-lg hover:bg-surface-card transition-colors"
                          title="查看开源仓库源文件"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>

                        <button
                          type="button"
                          onClick={() => handleAdapt(item)}
                          disabled={isAdapting}
                          className="px-3.5 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 transition-colors shadow-sm"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>{t("adaptAndPreview")}</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Direct Tab */
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-content-primary mb-1">
                  {t("sourcePlatform")}
                </label>
                <select
                  value={sourcePlatform}
                  onChange={(e) => setSourcePlatform(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-xs dark:bg-gray-700 dark:text-white"
                >
                  <option value="Cortex XSOAR">Cortex XSOAR (YAML)</option>
                  <option value="Splunk SOAR">Splunk SOAR / Phantom (Python/JSON)</option>
                  <option value="Shuffle SOAR">Shuffle SOAR (JSON Workflow)</option>
                  <option value="Microsoft Sentinel">Microsoft Sentinel (Logic Apps ARM)</option>
                  <option value="NIST / CISA">NIST / CISA 标准应急 SOP (Markdown/Text)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-content-primary mb-1">
                  {t("inputUrlLabel")}
                </label>
                <div className="relative">
                  <LinkIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                  <input
                    type="url"
                    value={directUrl}
                    onChange={(e) => setDirectUrl(e.target.value)}
                    placeholder="https://raw.githubusercontent.com/demisto/content/.../playbook.yml"
                    className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-xs dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-content-primary mb-1">
                  {t("inputContentLabel")}
                </label>
                <textarea
                  rows={8}
                  value={directContent}
                  onChange={(e) => setDirectContent(e.target.value)}
                  placeholder={`# 示例：粘贴外部剧本定义或事故处理规范...
name: Log4Shell Incident Response
tasks:
  - id: extract
    type: extract_iocs
  - id: query_ti
    type: virustotal
  - id: block_ip
    type: firewall_acl`}
                  className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg font-mono text-xs leading-relaxed dark:bg-gray-700 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-content-primary mb-1">
                  {t("titleHintLabel")}
                </label>
                <input
                  type="text"
                  value={directTitle}
                  onChange={(e) => setDirectTitle(e.target.value)}
                  placeholder="例如：Log4Shell 应急处置自动化响应"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-xs dark:bg-gray-700 dark:text-white"
                />
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => handleAdapt()}
                  disabled={isAdapting || (!directUrl.trim() && !directContent.trim())}
                  className="w-full py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold disabled:opacity-50 flex items-center justify-center gap-2 transition-colors shadow-sm"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{t("startAdapt")}</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Adapting Overlay */}
        {isAdapting && (
          <div className="absolute inset-0 bg-surface-card/90 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center z-10 animate-in fade-in duration-150">
            <div className="w-12 h-12 rounded-2xl bg-amber-100 dark:bg-amber-950/60 text-amber-600 flex items-center justify-center mb-3">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
            <h4 className="font-bold text-sm text-content-primary mb-1">
              AI 正在智能适配工作流拓扑...
            </h4>
            <p className="text-xs text-content-muted max-w-sm">
              正在将「{adaptingTarget}」解析为标准有向无环图 (DAG)，映射节点动作与依赖插件。
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
