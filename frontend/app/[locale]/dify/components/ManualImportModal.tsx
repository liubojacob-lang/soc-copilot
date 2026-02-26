/** Manual import modal for Dify workflows */

import { useState } from 'react';
import { Link, Download, Clock, X } from 'lucide-react';

interface ManualImportModalProps {
  show: boolean;
  importing: boolean;
  onImport: (appId: string) => Promise<void>;
  onClose: () => void;
  t: any;
}

export function ManualImportModal({
  show,
  importing,
  onImport,
  onClose,
  t
}: ManualImportModalProps) {
  const [appId, setAppId] = useState("");

  const handleImport = async () => {
    await onImport(appId);
    setAppId("");
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-lg w-full">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Link className="w-5 h-5" />
            {t('manualImport.title')}
          </h3>
        </div>
        <div className="p-6">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {t('manualImport.description')}
          </p>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('manualImport.appId')}
            </label>
            <input
              type="text"
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
              placeholder={t('manualImport.placeholder')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
            />
          </div>
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 mb-4">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              <strong>{t('manualImport.howToFind.title')}</strong><br />
              {t('manualImport.howToFind.step1')}<br />
              {t('manualImport.howToFind.step2')}<br />
              {t('manualImport.howToFind.step3')}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => {
                onClose();
                setAppId("");
              }}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              disabled={importing}
            >
              {t('cancel')}
            </button>
            <button
              onClick={handleImport}
              disabled={importing || !appId.trim()}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {importing ? (
                <>
                  <Clock className="w-4 h-4 animate-spin" />
                  {t('importing')}
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  {t('import')}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
