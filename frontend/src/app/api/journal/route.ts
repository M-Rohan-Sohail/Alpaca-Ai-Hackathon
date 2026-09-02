import { NextResponse } from "next/server";
import { journal } from "@/lib/mock/store";

export async function GET() {
  return NextResponse.json(journal);
}
