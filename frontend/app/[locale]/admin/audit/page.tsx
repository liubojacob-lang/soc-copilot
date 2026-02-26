import { useTranslations } from 'next-intl';

export default function AdminAuditPage() {
  const t = useTranslations('admin');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h1 className="text-3xl font-bold text-gray-900">
            {t('auditLogs', { default: 'Audit Logs' })}
          </h1>
          <p className="mt-4 text-gray-600">
            View system audit logs and activities
          </p>

          <div className="mt-6 bg-white shadow rounded-lg p-6">
            <p className="text-center text-gray-500">
              Audit log list will be displayed here
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
