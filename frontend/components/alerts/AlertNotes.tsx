"use client";

/**
 * AlertNotes Component
 * 告警备注输入和显示
 */

import React, { useState, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import { MessageSquare, Send, Trash2, Edit, User } from "lucide-react";

interface AlertNote {
  id: string;
  user_id: string;
  username: string;
  content: string;
  created_at: string;
  updated_at?: string;
}

interface AlertNotesProps {
  notes: AlertNote[];
  onAdd: (content: string) => Promise<void>;
  onDelete?: (noteId: string) => Promise<void>;
  onEdit?: (noteId: string, content: string) => Promise<void>;
  currentUserId?: string;
  canAdd?: boolean;
  canDelete?: boolean;
  canEdit?: boolean;
}

export function AlertNotes({
  notes,
  onAdd,
  onDelete,
  onEdit,
  currentUserId,
  canAdd = true,
  canDelete = true,
  canEdit = true,
}: AlertNotesProps) {
  const t = useTranslations("notes");
  const tTime = useTranslations("time");
  const [newNote, setNewNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 按时间排序（最新的在上面）
  const sortedNotes = [...notes].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const handleSubmit = async () => {
    if (!newNote.trim() || submitting) return;

    setSubmitting(true);
    try {
      await onAdd(newNote.trim());
      setNewNote("");
    } catch (error) {
      console.error("Failed to add note:", error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (noteId: string) => {
    if (!onDelete) return;
    if (!confirm(t("deleteConfirm"))) return;

    try {
      await onDelete(noteId);
    } catch (error) {
      console.error("Failed to delete note:", error);
    }
  };

  const handleEditStart = (note: AlertNote) => {
    if (!onEdit) return;
    setEditingId(note.id);
    setEditContent(note.content);
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditContent("");
  };

  const handleEditSave = async (noteId: string) => {
    if (!onEdit || !editContent.trim()) return;

    try {
      await onEdit(noteId, editContent.trim());
      setEditingId(null);
      setEditContent("");
    } catch (error) {
      console.error("Failed to edit note:", error);
    }
  };

  // 自动调整文本框高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [newNote, editContent]);

  const formatRelativeTime = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return tTime("justNow");
    if (diffMins < 60) return tTime("minutesAgo", { count: diffMins });
    if (diffHours < 24) return tTime("hoursAgo", { count: diffHours });
    if (diffDays < 7) return tTime("daysAgo", { count: diffDays });
    return then.toLocaleDateString();
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{t("title")}</h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">({notes.length})</span>
        </div>
      </div>

      {/* Add Note */}
      {canAdd && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <textarea
            ref={textareaRef}
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            placeholder={t("placeholder")}
            rows={2}
            disabled={submitting}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white resize-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-gray-500 dark:text-gray-400">{t("submitHint")}</span>
            <button
              onClick={handleSubmit}
              disabled={!newNote.trim() || submitting}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-4 h-4" />
              {submitting ? t("adding") : t("addNote")}
            </button>
          </div>
        </div>
      )}

      {/* Notes List */}
      <div className="space-y-3">
        {sortedNotes.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
            <MessageSquare className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">{t("empty")}</p>
          </div>
        ) : (
          sortedNotes.map((note) => (
            <div
              key={note.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
            >
              <div className="p-4">
                {/* Note Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {note.username}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {formatRelativeTime(note.created_at)}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1">
                    {canEdit &&
                      note.user_id === currentUserId &&
                      onEdit &&
                      editingId !== note.id && (
                        <button
                          onClick={() => handleEditStart(note)}
                          className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                          title={t("editNote")}
                        >
                          <Edit className="w-4 h-4 text-gray-500" />
                        </button>
                      )}
                    {canDelete && note.user_id === currentUserId && onDelete && (
                      <button
                        onClick={() => handleDelete(note.id)}
                        className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                        title={t("deleteNote")}
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Note Content */}
                {editingId === note.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      rows={4}
                      className="w-full px-3 py-2 border border-blue-300 dark:border-blue-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white resize-none"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditSave(note.id)}
                        disabled={!editContent.trim()}
                        className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >
                        {t("save")}
                      </button>
                      <button
                        onClick={handleEditCancel}
                        className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                      >
                        {t("cancel")}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {note.content}
                  </div>
                )}

                {/* Updated At */}
                {note.updated_at && note.updated_at !== note.created_at && (
                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    {t("edited")} {formatRelativeTime(note.updated_at)}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// 简化版：仅用于侧边栏显示
export function CompactNotes({ notes, limit = 3 }: { notes: AlertNote[]; limit?: number }) {
  const t = useTranslations("notes");
  const tTime = useTranslations("time");

  if (!notes || notes.length === 0) {
    return null;
  }

  const recentNotes = [...notes]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, limit);

  const formatRelativeTime = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return tTime("justNow");
    if (diffMins < 60) return tTime("minutesAgo", { count: diffMins });
    if (diffHours < 24) return tTime("hoursAgo", { count: diffHours });
    if (diffDays < 7) return tTime("daysAgo", { count: diffDays });
    return then.toLocaleDateString();
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{t("recentNotes")}</h4>
        <MessageSquare className="w-4 h-4 text-gray-400" />
      </div>

      <div className="space-y-2">
        {recentNotes.map((note) => (
          <div
            key={note.id}
            className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3 border border-gray-200 dark:border-gray-700"
          >
            <div className="flex items-center gap-2 mb-1">
              <User className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-xs font-medium text-gray-900 dark:text-white">
                {note.username}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {formatRelativeTime(note.created_at)}
              </span>
            </div>
            <p className="text-xs text-gray-700 dark:text-gray-300 line-clamp-2">{note.content}</p>
          </div>
        ))}

        {notes.length > limit && (
          <div className="text-center">
            <button className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
              {t("viewAll", { count: notes.length })}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
