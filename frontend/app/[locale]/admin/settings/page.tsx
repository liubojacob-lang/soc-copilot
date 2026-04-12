import { useTranslations } from "next-intl";

export default function AdminSettingsPage() {
  const t = useTranslations("adminSettings");
  const tCommon = useTranslations("common");

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h1 className="text-3xl font-bold text-gray-900">{t("title")}</h1>
          <p className="mt-4 text-gray-600">{t("subtitle")}</p>

          <div className="mt-6 bg-white shadow rounded-lg p-6">
            <p className="text-center text-gray-500">{t("settingsForm")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
