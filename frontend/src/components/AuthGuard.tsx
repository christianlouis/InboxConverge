'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { userApi } from '@/lib/api';

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, setUser, setLoading, isLoading } = useAuthStore();

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        setLoading(false);
        router.push('/login');
        return;
      }

      try {
        const userData = await userApi.getCurrentUser();
        setUser(userData);
      } catch (error) {
        console.error('Auth check failed:', error);
        setUser(null);
        router.push('/login');
      }
    };

    checkAuth();
  }, [router, setUser, setLoading]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}
