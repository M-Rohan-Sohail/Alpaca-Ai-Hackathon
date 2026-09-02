import { NextResponse } from "next/server";
import { dashboardState, seedActivity } from "@/lib/mock/store";
import type { DashboardResponse } from "@/lib/api/types";

export async function GET() {
  const body: DashboardResponse = {
    ...dashboardState,
    recent_activity: seedActivity.slice(0, 10),
  };
  return NextResponse.json(body);
}
