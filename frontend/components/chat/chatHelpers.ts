import { useMemo } from "react";
import type { ChatConversation } from "@/hooks/useChatHistory";

/** Get first letter or leading emoji for a conversation icon. */
export function getInitial(title: string): string {
  if (!title) return "💬";
  const emojiMatch = title.match(/^[\u{1F300}-\u{1F9FF}]/u);
  if (emojiMatch) return emojiMatch[0];
  return title.charAt(0).toUpperCase();
}

const AVATAR_COLORS = [
  "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
  "bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400",
  "bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400",
  "bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400",
  "bg-rose-100 text-rose-600 dark:bg-rose-900/30 dark:text-rose-400",
  "bg-cyan-100 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-400",
  "bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400",
];

/** Deterministic avatar color class based on id hash. */
export function getColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export interface ConversationGroup {
  label: string;
  conversations: ChatConversation[];
}

/** Group conversations into today / yesterday / past 7 days / older buckets.
 * i18n-namespace: aiAssistant.history
 */
export function useGroupedConversations(
  conversations: ChatConversation[],
  t: (key: "today" | "yesterday" | "past7Days" | "older") => string,
  mounted: boolean
): ConversationGroup[] {
  return useMemo(() => {
    if (!mounted) return [];

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const weekAgo = new Date(today.getTime() - 7 * 86400000);

    const groups: Record<string, ChatConversation[]> = {
      [t("today")]: [],
      [t("yesterday")]: [],
      [t("past7Days")]: [],
      [t("older")]: [],
    };

    conversations.forEach((conv) => {
      const date = new Date(conv.updatedAt);
      if (date >= today) {
        groups[t("today")].push(conv);
      } else if (date >= yesterday) {
        groups[t("yesterday")].push(conv);
      } else if (date >= weekAgo) {
        groups[t("past7Days")].push(conv);
      } else {
        groups[t("older")].push(conv);
      }
    });

    return Object.entries(groups)
      .filter(([, convs]) => convs.length > 0)
      .map(([label, conversations]) => ({ label, conversations }));
  }, [conversations, t, mounted]);
}
