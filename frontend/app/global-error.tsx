'use client';

/**
 * Global error boundary for Next.js App Router.
 * This catches errors in the root layout, including the html and body tags.
 * 
 * @see https://nextjs.org/docs/app/building-your-application/routing/error-handling#handling-errors-in-root-layouts
 */

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  return (
    <html lang="zh-CN">
      <body style={{
        margin: 0,
        padding: 0,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          padding: '20px',
          backgroundColor: '#fff',
        }}>
          <div style={{
            maxWidth: '500px',
            textAlign: 'center',
          }}>
            <h1 style={{
              fontSize: '48px',
              margin: '0 0 16px 0',
              color: '#1a1a1a',
            }}>
              ⚠️
            </h1>
            <h2 style={{
              fontSize: '24px',
              margin: '0 0 12px 0',
              color: '#1a1a1a',
            }}>
              发生严重错误
            </h2>
            <p style={{
              fontSize: '16px',
              color: '#666',
              margin: '0 0 24px 0',
            }}>
              应用遇到了一个严重错误，请刷新页面重试。
            </p>
            {process.env.NODE_ENV === 'development' && (
              <pre style={{
                textAlign: 'left',
                padding: '16px',
                backgroundColor: '#f5f5f5',
                borderRadius: '8px',
                overflow: 'auto',
                fontSize: '12px',
                color: '#d32f2f',
                marginBottom: '24px',
              }}>
                {error.message}
                {error.digest && `\n\nError ID: ${error.digest}`}
              </pre>
            )}
            <button
              onClick={reset}
              style={{
                padding: '12px 32px',
                fontSize: '16px',
                fontWeight: 500,
                color: '#fff',
                backgroundColor: '#1890ff',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              刷新页面
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
