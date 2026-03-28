'use client';

import { useState } from 'react';
import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { adminApi, AdminProcessingRun } from '@/lib/api';
import { parseUTC } from '@/lib/date-utils';
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
  RefreshCw,
} from 'lucide-react';

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  partial_failure: 'bg-yellow-100 text-yellow-800',
  running: 'bg-blue-100 text-blue-800',
};

function formatDuration(seconds?: number | null): string {
  if (seconds == null) return '—';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

function formatDate(iso: string): string {
  return parseUTC(iso).toLocaleString(undefined, {
    dateStyle: 'short',
    timeStyle: 'medium',
  });
}

export default function AdminLogsPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    if (user && !user.is_superuser) {
      router.replace('/dashboard');
    }
  }, [user, router]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-processing-runs', page, statusFilter],
    queryFn: () =>
      adminApi.listProcessingRuns({
        page,
        page_size: 25,
        ...(statusFilter ? { status: statusFilter } : {}),
      }),
    enabled: !!user?.is_superuser,
  });

  return (
    <AuthGuard>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <Activity className="h-6 w-6 text-purple-600" />
                Activity Logs
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                All email processing runs across every user account.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="text-sm border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All statuses</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="partial_failure">Partial failure</option>
                <option value="running">Running</option>
              </select>
              <button
                onClick={() => refetch()}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
            </div>
          </div>

          {/* Table */}
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
            </div>
          ) : isError ? (
            <div className="text-center py-16 text-red-500">
              Failed to load activity logs. Please try again.
            </div>
          ) : data && data.items.length > 0 ? (
            <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <th className="px-4 py-3">Started</th>
                      <th className="px-4 py-3">User</th>
                      <th className="px-4 py-3">Account</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Fetched</th>
                      <th className="px-4 py-3 text-right">Forwarded</th>
                      <th className="px-4 py-3 text-right">Failed</th>
                      <th className="px-4 py-3 text-right">Duration</th>
                      <th className="px-4 py-3">OK</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.items.map((run: AdminProcessingRun) => {
                      const statusClass =
                        STATUS_STYLES[run.status] ?? 'bg-gray-100 text-gray-800';
                      const ok = run.emails_failed === 0 && run.status !== 'failed';
                      return (
                        <tr key={run.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
                            {formatDate(run.started_at)}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                            {run.user_email ?? `#${run.user_id}`}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                            <div className="font-medium">{run.account_name ?? '—'}</div>
                            <div className="text-xs text-gray-400">{run.account_email ?? ''}</div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span
                              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${statusClass}`}
                            >
                              {run.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600 text-right whitespace-nowrap">
                            {run.emails_fetched}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600 text-right whitespace-nowrap">
                            {run.emails_forwarded}
                          </td>
                          <td className="px-4 py-3 text-sm text-right whitespace-nowrap">
                            {run.emails_failed > 0 ? (
                              <span className="text-red-600">{run.emails_failed}</span>
                            ) : (
                              <span className="text-gray-400">0</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500 text-right whitespace-nowrap">
                            {formatDuration(run.duration_seconds)}
                          </td>
                          <td className="px-4 py-3">
                            {ok ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-500" />
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {data.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                  <span className="text-sm text-gray-500">
                    Page {data.page} of {data.pages} ({data.total} total runs)
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="flex items-center px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-40 transition-colors"
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </button>
                    <button
                      onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                      disabled={page === data.pages}
                      className="flex items-center px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-40 transition-colors"
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-16 bg-white rounded-lg shadow border border-dashed border-gray-300">
              <Activity className="mx-auto h-12 w-12 text-gray-300 mb-3" />
              <h3 className="text-base font-semibold text-gray-700 mb-1">No activity yet</h3>
              <p className="text-sm text-gray-500 max-w-xs mx-auto">
                Processing run logs will appear here once mail accounts are active.
              </p>
            </div>
          )}
        </div>
      </DashboardLayout>
    </AuthGuard>
  );
}
