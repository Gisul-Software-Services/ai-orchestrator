import { NextResponse } from "next/server";

const RAG_URL = process.env.RAG_SERVICE_URL ?? "http://127.0.0.1:7003";
const ADMIN_KEY = process.env.RAG_ADMIN_KEY ?? "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg";

export async function POST() {
  try {
    // Trigger the regenerate_sample_data.py script via a shell command
    // This endpoint signals that regeneration should happen
    return NextResponse.json({ 
      message: "To regenerate sample data, run: python3 regenerate_sample_data.py --rows 100",
      command: "python3 /root/gisul_model/regenerate_sample_data.py --rows 100",
      rag_url: RAG_URL
    });
  } catch {
    return NextResponse.json({ error: "Failed" }, { status: 503 });
  }
}
