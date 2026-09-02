import { NextResponse } from "next/server";
import { candidates } from "@/lib/mock/store";

export async function GET() {
  return NextResponse.json(candidates);
}
