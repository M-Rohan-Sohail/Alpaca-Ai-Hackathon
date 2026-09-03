"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type {
  DashboardResponse,
  JournalEntry,
  PipelineCandidate,
  Position,
  PipelineStatusResponse,
} from "@/lib/api/types";

// Refresh intervals per Section F of the spec.
const DASHBOARD_REFRESH_MS = 8_000;
const PIPELINE_REFRESH_MS = 8_000;
const POSITIONS_REFRESH_MS = 4_000;

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiClient.get<DashboardResponse>("/api/dashboard"),
    refetchInterval: DASHBOARD_REFRESH_MS,
  });
}

export function usePipelineLatest() {
  return useQuery({
    queryKey: ["pipeline", "latest"],
    queryFn: () => apiClient.get<PipelineCandidate[]>("/api/pipeline/latest"),
    refetchInterval: PIPELINE_REFRESH_MS,
  });
}

export function usePositions() {
  return useQuery({
    queryKey: ["positions"],
    queryFn: () => apiClient.get<Position[]>("/api/positions"),
    refetchInterval: POSITIONS_REFRESH_MS,
  });
}

export function useJournal() {
  return useQuery({
    queryKey: ["journal"],
    queryFn: () => apiClient.get<JournalEntry[]>("/api/journal"),
  });
}

export function usePipelineStatus() {
  return useQuery({
    queryKey: ["pipeline", "status"],
    queryFn: () => apiClient.get<PipelineStatusResponse>("/api/pipeline/status"),
    refetchInterval: 3000,
  });
}

export function useStartPipeline() {
  return useMutation({
    mutationFn: () => apiClient.post<{ status: string }>("/api/execute/pipeline"),
  });
}
