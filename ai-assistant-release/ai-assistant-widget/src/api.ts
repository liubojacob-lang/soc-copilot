export interface ChatRequest { message: string; model_id?: string; }
export interface ChatResponse { content?: string; }
export async function postChat(baseUrl: string, data: ChatRequest): Promise<ChatResponse> {
  const resp = await fetch(`${baseUrl}/api/ai/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
  if (!resp.ok) throw new Error(`Chat API error: ${resp.status} ${resp.statusText}`);
  return resp.json();
}
