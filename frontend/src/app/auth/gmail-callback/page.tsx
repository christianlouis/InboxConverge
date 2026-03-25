'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { gmailApi } from '@/lib/api';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

function GmailCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Connecting your Gmail account…');

  useEffect(() => {
    async function handleCallback() {
      const code = searchParams.get('code');
      const error = searchParams.get('error');

      if (error) {
        setStatus('error');
        setMessage(
          error === 'access_denied'
            ? 'You declined the Gmail permission request. No changes were made.'
            : `Google returned an error: ${error}`
        );
        return;
      }

      if (!code) {
        setStatus('error');
        setMessage('No authorization code received from Google.');
        return;
      }

      const redirectUri = `${window.location.origin}/auth/gmail-callback`;

      try {
        await gmailApi.saveCallback(code, redirectUri);
        setStatus('success');
        setMessage('Gmail connected successfully! Redirecting to settings…');
        setTimeout(() => router.push('/settings'), 2000);
      } catch (err: unknown) {
        const detail =
          err instanceof Error && 'response' in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data
                ?.detail
            : null;
        setStatus('error');
        setMessage(detail || 'Failed to connect Gmail. Please try again.');
      }
    }

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-lg shadow-md p-8 max-w-md w-full text-center">
        {status === 'loading' && (
          <>
            <Loader2 className="h-12 w-12 text-blue-500 animate-spin mx-auto mb-4" />
            <p className="text-gray-700">{message}</p>
          </>
        )}
        {status === 'success' && (
          <>
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Connected!</h2>
            <p className="text-gray-600">{message}</p>
          </>
        )}
        {status === 'error' && (
          <>
            <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Connection failed</h2>
            <p className="text-gray-600 mb-6">{message}</p>
            <button
              onClick={() => router.push('/settings')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Back to Settings
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function GmailCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      }
    >
      <GmailCallbackContent />
    </Suspense>
  );
}
