import { NextRequest } from "next/server";

// SSE streaming proxy - Next.js rewrites don't properly support SSE
export async function GET(request: NextRequest) {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${backendUrl}/api/monitor/stream`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });

    if (!response.ok) {
      return new Response(JSON.stringify({ error: `Backend returned ${response.status}` }), {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    // For SSE, we need to return a streaming response
    const reader = response.body?.getReader();

    if (!reader) {
      return new Response(JSON.stringify({ error: "No response body" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }

    const stream = new ReadableStream({
      async start(controller) {
        const decoder = new TextDecoder();

        try {
          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              try {
                controller.close();
              } catch {
                // Controller might already be closed, ignore
              }
              break;
            }

            controller.enqueue(value);
          }
        } catch (error) {
          console.error("[SSE Proxy] Stream error:", error);
          try {
            controller.error(error);
          } catch {
            // Controller might already be closed, ignore
          }
        }
      },
      cancel() {
        reader.cancel();
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
    console.error("[SSE Proxy] Error:", error);
    return new Response(JSON.stringify({ error: "Failed to connect to backend" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
