import { NextRequest } from "next/server";

// SSE streaming proxy - Next.js rewrites don't properly support SSE
export async function GET(request: NextRequest) {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${backendUrl}/api/monitor/stream`;

  try {
    const authHeader = request.headers.get("authorization");
    const headers: Record<string, string> = {
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    };
    if (authHeader) {
      headers["Authorization"] = authHeader;
    }

    const response = await fetch(url, {
      method: "GET",
      headers,
      signal: request.signal,
    });

    if (!response.ok) {
      return new Response(JSON.stringify({ error: `Backend returned ${response.status}` }), {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    const reader = response.body?.getReader();
    if (!reader) {
      return new Response(JSON.stringify({ error: "No response body" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }

    let isClosed = false;
    const cleanup = () => {
      if (isClosed) return;
      isClosed = true;
      try {
        reader.cancel();
      } catch {
        // ignore
      }
    };

    request.signal.addEventListener("abort", cleanup);

    const stream = new ReadableStream({
      async start(controller) {
        try {
          while (!isClosed && !request.signal.aborted) {
            const { done, value } = await reader.read();
            if (done || isClosed || request.signal.aborted) {
              break;
            }
            controller.enqueue(value);
          }
        } catch (error) {
          if (!request.signal.aborted) {
            console.error("[SSE Proxy] Stream error:", error);
          }
        } finally {
          cleanup();
          try {
            controller.close();
          } catch {
            // ignore
          }
        }
      },
      cancel() {
        cleanup();
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    if ((error as any)?.name === "AbortError" || request.signal.aborted) {
      return new Response(null, { status: 499 });
    }
    console.error("[SSE Proxy] Error:", error);
    return new Response(JSON.stringify({ error: "Failed to connect to backend" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
