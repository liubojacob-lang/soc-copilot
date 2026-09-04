import { useTranslations } from "next-intl";
import { PageHeader } from "@/components/common/PageHeader";

export default function AdminSettingsPage() {
  const t = useTranslations("adminSettings");
  const tCommon = useTranslations("common");

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <p className="text-center text-gray-500 dark:text-gray-400">{t("settingsForm")}</p>
        </div>
      </main>
    </div>
  );
}
