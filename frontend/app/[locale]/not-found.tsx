import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

export default function NotFoundPage() {
  const t = useTranslations("errors.notFound");

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-6xl font-bold text-gray-300 dark:text-gray-600" aria-hidden="true">
        404
      </p>
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">{t("title")}</h1>
      <p className="max-w-md text-sm text-gray-500 dark:text-gray-400">{t("description")}</p>
      <Link
        href="/"
        className="mt-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
      >
        {t("backHome")}
      </Link>
    </div>
  );
}
