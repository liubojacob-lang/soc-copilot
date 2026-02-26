/** Constants and filter options for audit logs */

import type { QuickFilter, FilterOption } from './types';

/** Quick filter presets */
export const quickFilters: QuickFilter[] = [
  {
    name: "Errors",
    icon: "🔴",
    filter: { filterAction: "", filterStatusCode: "error", filterPath: "" },
    description: "Show only error responses"
  },
  {
    name: "Success",
    icon: "✅",
    filter: { filterAction: "", filterStatusCode: "success", filterPath: "" },
    description: "Only successful requests"
  },
  {
    name: "Login",
    icon: "🔐",
    filter: { filterAction: "login:*", filterStatusCode: "", filterPath: "" },
    description: "Login activity"
  },
  {
    name: "Users",
    icon: "👥",
    filter: { filterAction: "users:*", filterStatusCode: "", filterPath: "" },
    description: "User management"
  },
];

/** Common action filters */
export const getCommonActions = (t: any): FilterOption[] => [
  { value: "", label: t('allActions') },
  { value: "login:*", label: t('authentication') },
  { value: "users:*", label: t('userManagement') },
  { value: "playbook:*", label: t('playbooks') },
  { value: "assets:*", label: t('assets') },
  { value: "api_keys:*", label: t('apiKeys') },
];

/** Extended action filters */
export const getExtendedActions = (t: any): FilterOption[] => [
  { value: "playbook_definitions:*", label: t('playbookDefinitions') },
  { value: "ti:*", label: t('threatIntel') },
  { value: "ioc_hits:*", label: t('iocHits') },
  { value: "alert:*", label: t('alertAnalysis') },
  { value: "report:*", label: t('reports') },
  { value: "timeline:*", label: t('timelines') },
  { value: "audit_logs:*", label: t('auditLogs') },
  { value: "webhooks:*", label: t('webhooks') },
  { value: "history:*", label: t('history') },
];

/** Common path filters */
export const getCommonPaths = (t: any): FilterOption[] => [
  { value: "", label: t('allPaths') },
  { value: "/api/playbook*", label: t('playbooks') },
  { value: "/api/auth*", label: t('authentication') },
  { value: "/api/users*", label: t('userManagement') },
  { value: "/api/assets*", label: t('assets') },
];

/** Extended path filters */
export const getExtendedPaths = (t: any): FilterOption[] => [
  { value: "/api/api-keys*", label: t('apiKeys') },
  { value: "/api/ti*", label: t('threatIntel') },
  { value: "/api/audit-logs*", label: t('auditLogs') },
  { value: "/api/webhooks*", label: t('webhooks') },
  { value: "/api/history*", label: t('history') },
  { value: "/api/alert", label: t('alertAnalysis') },
  { value: "/api/report", label: t('reports') },
  { value: "/api/timeline", label: t('timelines') },
];

/** Status code filters */
export const getStatusCodes = (t: any): FilterOption[] => [
  { value: "", label: t('allStatus') },
  { value: "success", label: t('success') },
  { value: "error", label: t('allErrors') },
  { value: "4xx", label: t('clientErrors') },
  { value: "5xx", label: t('serverErrors') },
];

/** Extended status code filters */
export const getExtendedStatusCodes = (t: any): FilterOption[] => [
  { value: "200", label: t('ok') },
  { value: "201", label: t('created') },
  { value: "204", label: t('noContent') },
  { value: "400", label: t('badRequest') },
  { value: "401", label: t('unauthorized') },
  { value: "403", label: t('forbidden') },
  { value: "404", label: t('notFound') },
  { value: "422", label: t('unprocessable') },
  { value: "500", label: t('serverError') },
];
