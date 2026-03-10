import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // 타임아웃 설정: 30초
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const res = await fetch(`${API_BASE_URL}/api/terms/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const errorData = await res
        .json()
        .catch(() => ({ detail: res.statusText }));

      console.error(`Term search request failed: ${res.status}`, errorData);

      return NextResponse.json(
        {
          error: "Term search request failed",
          status: res.status,
          detail: errorData.detail ?? errorData.message ?? null,
        },
        { status: res.status },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : String(error);
    const isTimeout = errorMessage.includes("aborted") || errorMessage.includes("timeout");

    console.error("Term search proxy error:", {
      message: errorMessage,
      isTimeout,
      apiUrl: API_BASE_URL,
      errorType: error instanceof Error ? error.constructor.name : typeof error,
    });

    return NextResponse.json(
      {
        error: "Backend term search API unreachable",
        detail: isTimeout
          ? "Connection timeout (30s)"
          : errorMessage,
        apiUrl: API_BASE_URL,
      },
      { status: 502 },
    );
  }
}
