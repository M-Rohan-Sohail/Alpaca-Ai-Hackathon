"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type {
  CloseTradeRequest,
  CloseTradeResponse,
  DashboardResponse,
  JournalEntry,
  PipelineCandidate,
  Position,
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

export function useCloseTrade() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CloseTradeRequest) =>
      apiClient.post<CloseTradeResponse>("/api/execute/close", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["journal"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
