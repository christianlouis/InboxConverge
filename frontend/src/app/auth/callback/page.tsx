'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { authApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setUser } = useAuthStore();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Processing authentication...');

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const error = searchParams.get('error');

      if (error) {
        setStatus('error');
        setMessage(`Authentication failed: ${error}`);
        setTimeout(() => router.push('/login'), 3000);
        return;
      }

      if (!code) {
        setStatus('error');
        setMessage('No authorization code received');
        setTimeout(() => router.push('/login'), 3000);
        return;
      }

      try {
        const redirectUri = `${window.location.origin}/auth/callback`;
        const response = await authApi.googleAuth(code, redirectUri);
        
        localStorage.setItem('access_token', response.access_token);
        localStorage.setItem('user', JSON.stringify(response.user));
        setUser(response.user);
        
        setStatus('success');
        setMessage('Authentication successful! Redirecting...');
        setTimeout(() => router.push('/dashboard'), 1000);
      } catch (error) {
        console.error('Auth callback error:', error);
        setStatus('error');
        const errorMessage = error instanceof Error && 'response' in error 
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail 
          : null;
        setMessage(errorMessage || 'Authentication failed');
        setTimeout(() => router.push('/login'), 3000);
      }
    };

    handleCallback();
  }, [searchParams, router, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div className="flex flex-col items-center">
          {status === 'loading' && (
            <>
              <Loader2 className="h-12 w-12 text-blue-600 animate-spin mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Authenticating...
              </h2>
            </>
          )}
          
          {status === 'success' && (
            <>
              <CheckCircle className="h-12 w-12 text-green-600 mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Success!
              </h2>
            </>
          )}
          
          {status === 'error' && (
            <>
              <XCircle className="h-12 w-12 text-red-600 mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Authentication Failed
              </h2>
            </>
          )}
          
          <p className="text-gray-600 text-center">{message}</p>
        </div>
      </div>
    </div>
  );
}
