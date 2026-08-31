"use client";

/**
 * React Query hooks for Security Cases.
 *
 * Features:
 * - useCases: paginated list with filters
 * - useCaseDetail: single case by ID
 * - useCreateCase: mutation for creating a case
 * - useUpdateCase: mutation for updating a case
 * - useDeleteCase: mutation for deletion
 * - useTransitionCase: mutation for status transitions
 * - useCaseAlerts: linked alerts for a case
 * - useLinkAlert / useUnlinkAlert: manage alert links
 * - useCaseComments: comments for a case
 * - useAddCaseComment: mutation for adding a comment
 * - useCaseTimeline: timeline/audit log for a case
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryClient";
import {
  listCases,
  getCase,
  createCase,
  updateCase,
  deleteCase,
  transitionCaseStatus,
  getCaseAlerts,
  linkAlertToCase,
  unlinkAlertFromCase,
  getCaseComments,
  addCaseComment,
  getCaseTimeline,
  type CaseFilters,
  type CaseCreatePayload,
  type CaseUpdatePayload,
  type CaseStatusTransition,
  type CaseCommentCreate,
} from "@/lib/api/cases";

// ── useCases ──────────────────────────────────────────

export function useCases(filters: CaseFilters = {}) {
  return useQuery({
    queryKey: [...queryKeys.cases.all, "list", filters],
    queryFn: () => listCases(filters),
    staleTime: 30 * 1000,
  });
}

// ── useCaseDetail ─────────────────────────────────────

export function useCaseDetail(id: string | null | undefined) {
  const enabled = id !== null && id !== undefined && id !== "";
  return useQuery({
    queryKey: [...queryKeys.cases.all, "detail", id],
    queryFn: () => getCase(id!),
    enabled,
    staleTime: 15 * 1000,
  });
}

// ── useCaseAlerts ─────────────────────────────────────

export function useCaseAlerts(id: string | null | undefined) {
  const enabled = id !== null && id !== undefined && id !== "";
  return useQuery({
    queryKey: [...queryKeys.cases.all, "detail", id, "alerts"],
    queryFn: () => getCaseAlerts(id!),
    enabled,
    staleTime: 15 * 1000,
  });
}

// ── useCaseComments ───────────────────────────────────

export function useCaseComments(id: string | null | undefined) {
  const enabled = id !== null && id !== undefined && id !== "";
  return useQuery({
    queryKey: [...queryKeys.cases.all, "detail", id, "comments"],
    queryFn: () => getCaseComments(id!),
    enabled,
    staleTime: 15 * 1000,
  });
}

// ── useCaseTimeline ───────────────────────────────────

export function useCaseTimeline(id: string | null | undefined) {
  const enabled = id !== null && id !== undefined && id !== "";
  return useQuery({
    queryKey: [...queryKeys.cases.all, "detail", id, "timeline"],
    queryFn: () => getCaseTimeline(id!),
    enabled,
    staleTime: 15 * 1000,
  });
}

// ── useCreateCase ─────────────────────────────────────

export function useCreateCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CaseCreatePayload) => createCase(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...queryKeys.cases.all] });
    },
  });
}

// ── useUpdateCase ─────────────────────────────────────

export function useUpdateCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CaseUpdatePayload }) =>
      updateCase(id, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.cases.all, "detail", variables.id],
      });
      queryClient.invalidateQueries({ queryKey: [...queryKeys.cases.all] });
    },
  });
}

// ── useDeleteCase ─────────────────────────────────────

export function useDeleteCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteCase(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...queryKeys.cases.all] });
    },
  });
}

// ── useTransitionCase ─────────────────────────────────

export function useTransitionCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CaseStatusTransition }) =>
      transitionCaseStatus(id, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.cases.all, "detail", variables.id],
      });
      queryClient.invalidateQueries({ queryKey: [...queryKeys.cases.all] });
    },
  });
}

// ── useLinkAlert ──────────────────────────────────────

export function useLinkAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, alertId }: { caseId: string; alertId: number }) =>
      linkAlertToCase(caseId, alertId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.cases.all, "detail", variables.caseId, "alerts"],
      });
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.cases.all, "detail", variables.caseId, "timeline"],
      });
    },
  });
}

// ── useUnlinkAlert ────────────────────────────────────

export function useUnlinkAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, alertId }: { caseId: string; alertId: number }) =>
      unlinkAlertFromCase(caseId, alertId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.cases.all, "detail", variables.caseId, "alerts"],
      });
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.cases.all, "detail", variables.caseId, "timeline"],
      });
    },
  });
}

// ── useAddCaseComment ─────────────────────────────────

export function useAddCaseComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, payload }: { caseId: string; payload: CaseCommentCreate }) =>
      addCaseComment(caseId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.cases.all, "detail", variables.caseId, "comments"],
      });
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.cases.all, "detail", variables.caseId, "timeline"],
      });
    },
  });
}
