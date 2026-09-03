import { NextResponse } from "next/server";
import { getAdminFirestore } from "@/lib/firebase-admin";
import { candidates } from "@/lib/mock/store";
import type { PipelineCandidate } from "@/lib/api/types";

interface SubmitCandidateRequest {
  symbol: string;
}

export interface SubmitCandidateResponse {
  symbol: string;
  status: "PROCESSED" | "QUEUED";
  candidate: PipelineCandidate | null;
  message: string;
}

// Saves the submitted ticker to Firestore (collection "pipeline_submissions")
// so it exists durably while processing runs, then deletes that document once
// processing completes -- Firestore is used here as a transient inbox, not a
// permanent store of trading data.
export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as SubmitCandidateRequest | null;
  const symbol = body?.symbol?.trim().toUpperCase();

  if (!symbol) {
    return NextResponse.json({ message: "symbol is required" }, { status: 400 });
  }

  const db = getAdminFirestore();
  const docRef = db.collection("pipeline_submissions").doc();

  await docRef.set({
    symbol,
    status: "processing",
    submittedAt: new Date().toISOString(),
  });

  let response: SubmitCandidateResponse;
  try {
    // Placeholder "processing": the real pipeline (Section M backend, not yet
    // built) would pick this up and run its own analysis. Until then, this
    // just checks whether the symbol already has a result from today's mock
    // pipeline run.
    const match = candidates.find((c) => c.symbol === symbol) ?? null;
    response = match
      ? {
          symbol,
          status: "PROCESSED",
          candidate: match,
          message: `${symbol} has already been processed by the pipeline today.`,
        }
      : {
          symbol,
          status: "QUEUED",
          candidate: null,
          message: `${symbol} was submitted. It will be picked up by the next pipeline scan.`,
        };
  } finally {
    // Processing is complete (or has handed off to the real pipeline) --
    // the submission no longer needs to live in Firestore.
    await docRef.delete();
  }

  return NextResponse.json(response);
}
