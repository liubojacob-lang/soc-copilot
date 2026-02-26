/**
 * Sentry server configuration for server-side rendering.
 * 
 * This file configures Sentry for server-side error tracking and performance monitoring.
 * Environment variables required:
 * - SENTRY_DSN: Sentry DSN for your project
 * - SENTRY_ENVIRONMENT: Environment name (development, staging, production)
 */

import * as Sentry from '@sentry/nextjs';

const SENTRY_DSN = process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN;
const SENTRY_ENVIRONMENT = process.env.SENTRY_ENVIRONMENT || process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || 'development';
const SENTRY_RELEASE = process.env.SENTRY_RELEASE || process.env.NEXT_PUBLIC_SENTRY_RELEASE || '0.8.0';

// Only initialize Sentry if DSN is configured
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: SENTRY_ENVIRONMENT,
    release: SENTRY_RELEASE,
    
    // Performance monitoring
    tracesSampleRate: SENTRY_ENVIRONMENT === 'production' ? 0.1 : 1.0,
    
    // Ignore common server errors that are not actionable
    ignoreErrors: [
      // Network errors
      'ECONNREFUSED',
      'ECONNRESET',
      'ETIMEDOUT',
      // Auth related (handled by app)
      'Unauthorized',
      'Invalid token',
      // Cancelled requests
      'cancelled',
      'canceled',
    ],
    
    // Filter out sensitive data
    beforeSend(event, hint) {
      // Don't send events with sensitive data
      const request = event.request;
      if (request) {
        // Remove sensitive headers
        if (request.headers) {
          delete request.headers['authorization'];
          delete request.headers['cookie'];
          delete request.headers['x-api-key'];
        }
        // Remove sensitive URL params
        if (request.url) {
          try {
            const url = new URL(request.url);
            url.searchParams.delete('token');
            url.searchParams.delete('api_key');
            request.url = url.toString();
          } catch {
            // Invalid URL, keep as is
          }
        }
      }
      return event;
    },
  });
  
  console.log(`[Sentry] Server initialized: environment=${SENTRY_ENVIRONMENT}, release=${SENTRY_RELEASE}`);
} else {
  console.log('[Sentry] Server not initialized: SENTRY_DSN not set');
}

// Export for use in other files
export { Sentry };
