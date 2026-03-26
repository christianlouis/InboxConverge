'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Users, Mail, Activity, Shield } from 'lucide-react';
import Link from 'next/link';

export default function AdminPage() {
  const { user } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (user && !user.is_superuser) {
      router.replace('/dashboard');
    }
  }, [user, router]);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminApi.getStats,
    enabled: !!user?.is_superuser,
  });

  // AuthGuard must always render so it can fetch the current user and handle
  // unauthenticated redirects.  The early-return that was here prevented
  // AuthGuard from ever mounting on a direct navigation to /admin, leaving a
  // permanent blank page.  The superuser guard is now applied inside the
  // layout so that the auth check always runs first.
  return (
    <AuthGuard>
      <DashboardLayout>
        {!user?.is_superuser ? (
          // Shown briefly while AuthGuard resolves the current user, or while
          // the non-superuser redirect in the useEffect at the top of this
          // component fires (router.replace('/dashboard')).
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <Shield className="h-6 w-6 text-purple-600" />
                Admin Overview
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                System-wide statistics and management tools.
              </p>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
                <div className="bg-white rounded-lg shadow p-6 flex items-center gap-4">
                  <div className="p-3 rounded-full bg-purple-100">
                    <Users className="h-6 w-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Total Users</p>
                    <p className="text-3xl font-semibold text-gray-900">{stats?.total_users ?? '—'}</p>
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow p-6 flex items-center gap-4">
                  <div className="p-3 rounded-full bg-blue-100">
                    <Mail className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Mail Accounts</p>
                    <p className="text-3xl font-semibold text-gray-900">{stats?.total_mail_accounts ?? '—'}</p>
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow p-6 flex items-center gap-4">
                  <div className="p-3 rounded-full bg-green-100">
                    <Activity className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Processing Runs</p>
                    <p className="text-3xl font-semibold text-gray-900">{stats?.total_processing_runs ?? '—'}</p>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              <Link
                href="/admin/users"
                className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow flex items-center gap-4 group"
              >
                <div className="p-3 rounded-full bg-purple-100 group-hover:bg-purple-200 transition-colors">
                  <Users className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-900">Manage Users</p>
                  <p className="text-sm text-gray-500">View, edit, assign plans, promote to admin</p>
                </div>
              </Link>
              <Link
                href="/admin/plans"
                className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow flex items-center gap-4 group"
              >
                <div className="p-3 rounded-full bg-blue-100 group-hover:bg-blue-200 transition-colors">
                  <Mail className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-900">Manage Plans</p>
                  <p className="text-sm text-gray-500">Create and configure subscription plans</p>
                </div>
              </Link>
              <Link
                href="/admin/logs"
                className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow flex items-center gap-4 group"
              >
                <div className="p-3 rounded-full bg-green-100 group-hover:bg-green-200 transition-colors">
                  <Activity className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-900">Activity Logs</p>
                  <p className="text-sm text-gray-500">Processing runs and per-email logs across all users</p>
                </div>
              </Link>
            </div>
          </div>
        )}
      </DashboardLayout>
    </AuthGuard>
  );
}
