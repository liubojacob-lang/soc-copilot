'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Global error boundary for Next.js App Router.
 * This file catches runtime errors in the root layout and renders a fallback UI.
 * 
 * @see https://nextjs.org/docs/app/building-your-application/routing/error-handling
 */

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: ErrorProps) {
  const router = useRouter();

  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Global error caught:', error);
    
    // You could send this to a monitoring service like Sentry
    // captureException(error);
  }, [error]);

  const handleGoHome = () => {
    router.push('/');
  };

  const handleGoBack = () => {
    router.back();
  };

  return (
    <div style={styles.container}>
      <div style={styles.content}>
        <div style={styles.icon}>⚠️</div>
        <h1 style={styles.title}>出现了一些问题</h1>
        <p style={styles.message}>
          页面遇到了一个意外错误，请尝试刷新页面或返回首页。
        </p>
        
        {process.env.NODE_ENV === 'development' && (
          <details style={styles.details}>
            <summary style={styles.summary}>错误详情 (仅开发环境可见)</summary>
            <div style={styles.errorBox}>
              <p style={styles.errorName}>{error.name}: {error.message}</p>
              {error.digest && (
                <p style={styles.digest}>Error ID: {error.digest}</p>
              )}
              {error.stack && (
                <pre style={styles.stack}>{error.stack}</pre>
              )}
            </div>
          </details>
        )}
        
        <div style={styles.actions}>
          <button onClick={reset} style={styles.primaryButton}>
            重试
          </button>
          <button onClick={handleGoBack} style={styles.secondaryButton}>
            返回上一页
          </button>
          <button onClick={handleGoHome} style={styles.secondaryButton}>
            返回首页
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    padding: '20px',
    backgroundColor: '#f5f5f5',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  content: {
    maxWidth: '600px',
    width: '100%',
    padding: '40px',
    backgroundColor: '#fff',
    borderRadius: '12px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
    textAlign: 'center',
  },
  icon: {
    fontSize: '56px',
    marginBottom: '20px',
  },
  title: {
    margin: '0 0 12px 0',
    fontSize: '28px',
    fontWeight: 600,
    color: '#1a1a1a',
  },
  message: {
    margin: '0 0 28px 0',
    fontSize: '16px',
    color: '#666',
    lineHeight: 1.6,
  },
  details: {
    marginBottom: '28px',
    textAlign: 'left',
    backgroundColor: '#fafafa',
    padding: '16px',
    borderRadius: '8px',
    border: '1px solid #e8e8e8',
  },
  summary: {
    cursor: 'pointer',
    fontWeight: 500,
    color: '#333',
    fontSize: '14px',
  },
  errorBox: {
    marginTop: '16px',
  },
  errorName: {
    margin: '0 0 8px 0',
    fontSize: '14px',
    color: '#d32f2f',
    fontWeight: 500,
  },
  digest: {
    margin: '0 0 8px 0',
    fontSize: '12px',
    color: '#888',
    fontFamily: 'monospace',
  },
  stack: {
    margin: '0',
    padding: '12px',
    backgroundColor: '#fff',
    borderRadius: '4px',
    overflow: 'auto',
    fontSize: '12px',
    color: '#d32f2f',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    maxHeight: '200px',
    border: '1px solid #ffcdd2',
  },
  actions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
  primaryButton: {
    padding: '12px 28px',
    fontSize: '15px',
    fontWeight: 500,
    color: '#fff',
    backgroundColor: '#1890ff',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  secondaryButton: {
    padding: '12px 28px',
    fontSize: '15px',
    fontWeight: 500,
    color: '#1890ff',
    backgroundColor: '#fff',
    border: '1px solid #1890ff',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
};
