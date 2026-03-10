import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // 타임아웃 설정: 180초 (Gemini API는 복잡한 질문에 대해 응답 생성에 더 오래 걸릴 수 있음)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000);

    const res = await fetch(`${API_BASE_URL}/api/v1/chat`, {
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

      console.error(`Chat request failed: ${res.status}`, errorData);

      return NextResponse.json(
        {
          error: "Chat request failed",
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

    console.error("Chat proxy error:", {
      message: errorMessage,
      isTimeout,
      apiUrl: API_BASE_URL,
      errorType: error instanceof Error ? error.constructor.name : typeof error,
    });

    return NextResponse.json(
      {
        error: "Backend chat API unreachable",
        detail: isTimeout
          ? "Connection timeout (180s)"
          : errorMessage,
        apiUrl: API_BASE_URL,
      },
      { status: 502 },
    );
  }
}
