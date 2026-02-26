'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  MessageSquare,
  AlertTriangle,
  Check,
  ChevronRight,
  ChevronLeft,
  MoreHorizontal
} from 'lucide-react';
import type { ChatConversation } from '@/hooks/useChatHistory';

interface ChatHistorySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: ChatConversation[];
  currentId: string | null;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSelect: (conv: ChatConversation) => void;
  onDelete: (id: string) => void;
  onRename: (id: string, newTitle: string) => void;
  onNewChat: () => void;
  formatTimeAgo: (dateStr: string) => string;
}

export function ChatHistorySidebar({
  isOpen,
  onClose,
  conversations,
  currentId,
  searchQuery,
  onSearchChange,
  onSelect,
  onDelete,
  onRename,
  onNewChat,
  formatTimeAgo
}: ChatHistorySidebarProps) {
  const t = useTranslations('aiAssistant.history');
  
  const [isCollapsed, setIsCollapsed] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [hoveredConvId, setHoveredConvId] = useState<string | null>(null);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);

  // Focus input when editing starts
  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  // Close sidebar on mobile when not open
  if (!isOpen) return null;

  // Get first letter or emoji for icon
  const getInitial = (title: string) => {
    if (!title) return '💬';
    // Check for emoji at start
    const emojiMatch = title.match(/^[\u{1F300}-\u{1F9FF}]/u);
    if (emojiMatch) return emojiMatch[0];
    return title.charAt(0).toUpperCase();
  };

  // Get color based on title hash
  const getColor = (id: string) => {
    const colors = [
      'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
      'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
      'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
      'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
      'bg-rose-100 text-rose-600 dark:bg-rose-900/30 dark:text-rose-400',
      'bg-cyan-100 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-400',
      'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400',
    ];
    let hash = 0;
    for (let i = 0; i < id.length; i++) {
      hash = id.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };

  // Group conversations by date
  const groupedConversations = useMemo(() => {
    if (!mounted) return []; // Avoid hydration mismatch with Date
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const weekAgo = new Date(today.getTime() - 7 * 86400000);

    const groups: Record<string, ChatConversation[]> = {
      [t('today')]: [],
      [t('yesterday')]: [],
      [t('past7Days')]: [],
      [t('older')]: []
    };

    conversations.forEach(conv => {
      const date = new Date(conv.updatedAt);
      if (date >= today) {
        groups[t('today')].push(conv);
      } else if (date >= yesterday) {
        groups[t('yesterday')].push(conv);
      } else if (date >= weekAgo) {
        groups[t('past7Days')].push(conv);
      } else {
        groups[t('older')].push(conv);
      }
    });

    return Object.entries(groups)
      .filter(([, convs]) => convs.length > 0)
      .map(([label, conversations]) => ({ label, conversations }));
  }, [conversations, t, mounted]);

  // Start editing
  const startEditing = (conv: ChatConversation) => {
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  // Save rename
  const saveRename = () => {
    if (editingId && editTitle.trim()) {
      onRename(editingId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  // Cancel rename
  const cancelRename = () => {
    setEditingId(null);
    setEditTitle('');
  };

  // Handle key down in edit mode
  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveRename();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelRename();
    }
  };

  // Confirm delete
  const confirmDelete = () => {
    if (deleteConfirmId) {
      onDelete(deleteConfirmId);
      setDeleteConfirmId(null);
    }
  };

  // Handle conversation select
  const handleSelect = (conv: ChatConversation) => {
    onSelect(conv);
    setIsCollapsed(true);
  };

  // Collapsed sidebar - show only icons
  if (isCollapsed) {
    return (
      <>
        {/* Overlay */}
        <div 
          className="fixed inset-0 bg-black/20 z-40 lg:hidden"
          onClick={onClose}
        />
        
        <aside
          ref={sidebarRef}
          className="fixed left-0 top-0 h-screen w-[60px] bg-gray-50/95 dark:bg-gray-900/95 
                     border-r border-gray-200/60 dark:border-gray-700/60 z-50
                     flex flex-col backdrop-blur-sm transition-all duration-300"
        >
          {/* New Chat Button */}
          <div className="p-2 border-b border-gray-200/60 dark:border-gray-700/60">
            <button
              onClick={onNewChat}
              className="w-11 h-11 flex items-center justify-center rounded-xl
                         bg-gradient-to-br from-blue-500 to-indigo-600 text-white
                         hover:from-blue-600 hover:to-indigo-700 shadow-md hover:shadow-lg
                         transition-all duration-200 hover:scale-105"
              title={t('newChat')}
            >
              <Plus className="w-5 h-5" />
            </button>
          </div>

          {/* Recent Conversations Icons */}
          <div className="flex-1 overflow-y-auto py-2 space-y-1">
            {conversations.slice(0, 10).map((conv) => (
              <div
                key={conv.id}
                className="relative px-2"
                onMouseEnter={() => setHoveredConvId(conv.id)}
                onMouseLeave={() => setHoveredConvId(null)}
              >
                <button
                  onClick={() => handleSelect(conv)}
                  className={`
                    w-11 h-11 rounded-xl flex items-center justify-center text-sm font-medium
                    transition-all duration-200
                    ${conv.id === currentId 
                      ? 'bg-blue-100 dark:bg-blue-900/40 ring-2 ring-blue-400 dark:ring-blue-600 text-blue-700 dark:text-blue-300' 
                      : `bg-white dark:bg-gray-800 hover:scale-105 shadow-sm hover:shadow ${getColor(conv.id)}`
                    }
                  `}
                  title={conv.title}
                >
                  {getInitial(conv.title)}
                </button>
                
                {/* Active indicator */}
                {conv.id === currentId && (
                  <div className="absolute -right-0.5 top-1/2 -translate-y-1/2 w-1.5 h-6 
                                  bg-blue-500 dark:bg-blue-400 rounded-l-full" />
                )}
                
                {/* Hover tooltip */}
                {hoveredConvId === conv.id && (
                  <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50">
                    <div className="bg-gray-900 dark:bg-gray-800 text-white text-xs px-3 py-1.5 
                                    rounded-lg whitespace-nowrap shadow-lg">
                      <div className="font-medium max-w-[200px] truncate">{conv.title}</div>
                      <div className="text-gray-400 text-[10px] mt-0.5">
                        {formatTimeAgo(conv.updatedAt)} · {conv.messages.length}条
                      </div>
                    </div>
                    <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 
                                    w-2 h-2 bg-gray-900 dark:bg-gray-800 rotate-45" />
                  </div>
                )}
              </div>
            ))}
            
            {/* Show more indicator */}
            {conversations.length > 10 && (
              <div className="px-2 pt-1">
                <button
                  onClick={() => setIsCollapsed(false)}
                  className="w-11 h-11 rounded-xl flex items-center justify-center
                             bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400
                             hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                  title={t('showMore')}
                >
                  <MoreHorizontal className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>

          {/* Expand Button */}
          <div className="p-2 border-t border-gray-200/60 dark:border-gray-700/60">
            <button
              onClick={() => setIsCollapsed(false)}
              className="w-11 h-11 flex items-center justify-center rounded-xl
                         text-gray-500 dark:text-gray-400
                         hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200
                         transition-all duration-200"
              title={t('expandHistory')}
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </aside>
      </>
    );
  }

  // Expanded sidebar - full view
  return (
    <>
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
        onClick={() => setIsCollapsed(true)}
      />

      {/* Sidebar */}
      <aside
        ref={sidebarRef}
        className="fixed left-0 top-0 h-screen w-[300px] bg-white dark:bg-gray-900 
                   border-r border-gray-200 dark:border-gray-700 z-50
                   flex flex-col shadow-2xl animate-in slide-in-from-left-2 duration-300"
      >
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 
                           border-b border-gray-200 dark:border-gray-700 
                           bg-gradient-to-r from-gray-50 to-white dark:from-gray-800 dark:to-gray-900">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <MessageSquare className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <h2 className="font-semibold text-gray-900 dark:text-white">
              {t('title')}
            </h2>
            <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full">
              {conversations.length}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsCollapsed(true)}
              className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 
                         hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title={t('collapse')}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 
                         hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <span className="sr-only">Close</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </header>

        {/* New Chat Button */}
        <div className="p-3 border-b border-gray-100 dark:border-gray-800">
          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 
                       text-sm font-medium text-white 
                       bg-gradient-to-r from-blue-600 to-indigo-600 
                       hover:from-blue-700 hover:to-indigo-700 
                       rounded-xl transition-all shadow-md hover:shadow-lg"
          >
            <Plus className="w-4 h-4" />
            {t('newChat')}
          </button>
        </div>

        {/* Search */}
        <div className="p-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={t('search')}
              className="w-full pl-10 pr-3 py-2.5 text-sm 
                         border border-gray-200 dark:border-gray-700 
                         rounded-xl bg-gray-50 dark:bg-gray-800 
                         text-gray-900 dark:text-white 
                         placeholder-gray-500 dark:placeholder-gray-400 
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent 
                         transition-all"
            />
          </div>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            /* Empty State */
            <div className="flex flex-col items-center justify-center py-12 px-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-gray-100 to-gray-200 
                              dark:from-gray-800 dark:to-gray-700 
                              flex items-center justify-center mb-4">
                <MessageSquare className="w-8 h-8 text-gray-400 dark:text-gray-500" />
              </div>
              <p className="text-gray-700 dark:text-gray-300 font-medium text-center mb-1">
                {t('emptyTitle')}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center mb-5">
                {t('emptyHint')}
              </p>
              <button
                onClick={onNewChat}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium 
                           text-blue-600 dark:text-blue-400 
                           bg-blue-50 dark:bg-blue-900/30 
                           hover:bg-blue-100 dark:hover:bg-blue-900/50 
                           rounded-xl transition-colors"
              >
                <Plus className="w-4 h-4" />
                {t('newChat')}
              </button>
            </div>
          ) : (
            /* Grouped Conversations */
            <div className="py-2">
              {groupedConversations.map(({ label, conversations: groupConvs }) => (
                <div key={label} className="mb-2">
                  <div className="px-4 py-1.5 text-[11px] font-semibold text-gray-400 dark:text-gray-500 
                                  uppercase tracking-wider flex items-center gap-2">
                    {label}
                    <span className="text-gray-300 dark:text-gray-600 font-normal">
                      ({groupConvs.length})
                    </span>
                  </div>
                  {groupConvs.map(conv => (
                    <ConversationItem
                      key={conv.id}
                      conv={conv}
                      isActive={conv.id === currentId}
                      isEditing={conv.id === editingId}
                      editTitle={editTitle}
                      inputRef={inputRef}
                      onSelect={handleSelect}
                      onStartEdit={() => startEditing(conv)}
                      onEditTitleChange={setEditTitle}
                      onEditKeyDown={handleEditKeyDown}
                      onSaveEdit={saveRename}
                      onCancelEdit={cancelRename}
                      onDelete={() => setDeleteConfirmId(conv.id)}
                      formatTimeAgo={formatTimeAgo}
                      getInitial={getInitial}
                      getColor={getColor}
                      t={t}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 
                        bg-gray-50/80 dark:bg-gray-800/50">
          <div className="flex items-center justify-between text-[11px] text-gray-400 dark:text-gray-500">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-[10px] font-mono">
                ⌘N
              </kbd>
              <span>{t('shortcuts.new')}</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-[10px] font-mono">
                ESC
              </kbd>
              <span>{t('shortcuts.close')}</span>
            </span>
          </div>
        </div>
      </aside>

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setDeleteConfirmId(null)}
          />
          <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm 
                          overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 
                                flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
                    {t('deleteConfirm')}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t('deleteWarning')}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="flex-1 px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 
                           hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                {t('cancelRename')}
              </button>
              <button
                onClick={confirmDelete}
                className="flex-1 px-4 py-3 text-sm font-medium text-white bg-red-600 
                           hover:bg-red-700 transition-colors"
              >
                {t('delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// Individual conversation item
interface ConversationItemProps {
  conv: ChatConversation;
  isActive: boolean;
  isEditing: boolean;
  editTitle: string;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onSelect: (conv: ChatConversation) => void;
  onStartEdit: () => void;
  onEditTitleChange: (title: string) => void;
  onEditKeyDown: (e: React.KeyboardEvent) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onDelete: () => void;
  formatTimeAgo: (dateStr: string) => string;
  getInitial: (title: string) => string;
  getColor: (id: string) => string;
  t: (key: string) => string;
}

function ConversationItem({
  conv,
  isActive,
  isEditing,
  editTitle,
  inputRef,
  onSelect,
  onStartEdit,
  onEditTitleChange,
  onEditKeyDown,
  onSaveEdit,
  onCancelEdit,
  onDelete,
  formatTimeAgo,
  getInitial,
  getColor,
  t
}: ConversationItemProps) {
  return (
    <div className="px-2">
      {isEditing ? (
        /* Edit Mode */
        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-xl 
                        border border-blue-200 dark:border-blue-800">
          <input
            ref={inputRef}
            type="text"
            value={editTitle}
            onChange={(e) => onEditTitleChange(e.target.value)}
            onKeyDown={onEditKeyDown}
            placeholder={t('renamePlaceholder')}
            className="w-full px-3 py-2 text-sm 
                       border border-gray-300 dark:border-gray-600 
                       rounded-lg bg-white dark:bg-gray-800 
                       text-gray-900 dark:text-white 
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={onSaveEdit}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 
                         text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 
                         rounded-lg transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              {t('saveRename')}
            </button>
            <button
              onClick={onCancelEdit}
              className="flex-1 px-3 py-1.5 text-xs font-medium 
                         text-gray-600 dark:text-gray-400 
                         bg-gray-100 dark:bg-gray-700 
                         hover:bg-gray-200 dark:hover:bg-gray-600 
                         rounded-lg transition-colors"
            >
              {t('cancelRename')}
            </button>
          </div>
        </div>
      ) : (
        /* View Mode */
        <div
          className={`
            group relative flex items-start gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all
            ${isActive 
              ? 'bg-blue-100 dark:bg-blue-900/40 ring-1 ring-blue-200 dark:ring-blue-800' 
              : 'hover:bg-gray-100 dark:hover:bg-gray-800/70'
            }
          `}
          onClick={() => onSelect(conv)}
          onDoubleClick={(e) => {
            e.stopPropagation();
            onStartEdit();
          }}
        >
          {/* Active indicator */}
          {isActive && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 
                            bg-blue-600 dark:bg-blue-400 rounded-r-full" />
          )}
          
          {/* Icon with color */}
          <div className={`
            flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center text-sm font-medium
            ${isActive 
              ? 'bg-blue-200 dark:bg-blue-800 text-blue-700 dark:text-blue-300' 
              : getColor(conv.id)
            }
          `}>
            {getInitial(conv.title)}
          </div>
          
          {/* Content */}
          <div className="flex-1 min-w-0 py-0.5">
            <p className={`text-sm font-medium truncate 
                           ${isActive ? 'text-blue-900 dark:text-blue-100' : 'text-gray-800 dark:text-gray-200'}`}>
              {conv.title}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 flex items-center gap-1.5">
              <span>{formatTimeAgo(conv.updatedAt)}</span>
              <span className="w-1 h-1 rounded-full bg-gray-300 dark:bg-gray-600" />
              <span>{conv.messages.length}{t('messages')}</span>
            </p>
          </div>
          
          {/* Actions */}
          <div className={`
            flex items-center gap-0.5 flex-shrink-0
            opacity-0 group-hover:opacity-100 transition-opacity
            ${isActive ? 'opacity-100' : ''}
          `}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStartEdit();
              }}
              className="p-1.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 
                         hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
              title={t('rename')}
            >
              <Edit2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 
                         hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
              title={t('delete')}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
