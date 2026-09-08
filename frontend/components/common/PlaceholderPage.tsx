import { useTranslations } from "next-intl";

interface PlaceholderPageProps {
  title: string;
  description?: string;
  feature?: string;
}

export function PlaceholderPage({ title, description, feature }: PlaceholderPageProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">SOC Copilot</h1>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-[1600px] mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">{title}</h2>
            {description && <p className="text-gray-600 mb-4">{description}</p>}
            {feature && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                <p className="text-sm text-blue-800">
                  <strong>Feature:</strong> {feature}
                </p>
                <p className="text-sm text-blue-600 mt-2">
                  This feature is under development. Check back soon!
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
