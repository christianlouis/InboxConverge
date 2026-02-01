'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery } from '@tanstack/react-query';
import { mailAccountsApi, processingRunsApi } from '@/lib/api';
import { 
  Mail, 
  Send, 
  CheckCircle, 
  AlertCircle,
  TrendingUp,
  Clock
} from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
  trend?: string;
}

function StatCard({ title, value, icon: Icon, iconColor, trend }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-gray-900">{value}</p>
          {trend && (
            <div className="mt-2 flex items-center text-sm">
              <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
              <span className="text-green-600">{trend}</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-full ${iconColor}`}>
          <Icon className="h-8 w-8 text-white" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: accounts } = useQuery({
    queryKey: ['mail-accounts'],
    queryFn: mailAccountsApi.list,
  });

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ['processing-runs'],
    queryFn: () => processingRunsApi.list(),
  });

  const stats = {
    totalAccounts: accounts?.length || 0,
    activeAccounts: accounts?.filter((a) => a.is_enabled).length || 0,
    emailsToday: runs
      ?.filter((r) => {
        const today = new Date().toDateString();
        return new Date(r.started_at).toDateString() === today;
      })
      .reduce((sum, r) => sum + r.emails_forwarded, 0) || 0,
    errors: runs?.filter((r) => r.errors_count > 0).length || 0,
  };

  return (
    <AuthGuard>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Total Accounts"
              value={stats.totalAccounts}
              icon={Mail}
              iconColor="bg-blue-500"
            />
            <StatCard
              title="Emails Forwarded Today"
              value={stats.emailsToday}
              icon={Send}
              iconColor="bg-green-500"
            />
            <StatCard
              title="Active Accounts"
              value={stats.activeAccounts}
              icon={CheckCircle}
              iconColor="bg-purple-500"
            />
            <StatCard
              title="Errors"
              value={stats.errors}
              icon={AlertCircle}
              iconColor="bg-red-500"
            />
          </div>

          {/* Recent Processing Runs */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Recent Processing Runs</h3>
            </div>
            <div className="overflow-x-auto">
              {runsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : runs && runs.length > 0 ? (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Account
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Started At
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Fetched
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Forwarded
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Errors
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {runs.slice(0, 10).map((run) => {
                      const account = accounts?.find((a) => a.id === run.mail_account_id);
                      return (
                        <tr key={run.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {account?.name || `Account ${run.mail_account_id}`}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <div className="flex items-center">
                              <Clock className="h-4 w-4 mr-1 text-gray-400" />
                              {new Date(run.started_at).toLocaleString()}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span
                              className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                run.status === 'completed'
                                  ? 'bg-green-100 text-green-800'
                                  : run.status === 'failed'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}
                            >
                              {run.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {run.emails_fetched}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {run.emails_forwarded}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {run.errors_count > 0 ? (
                              <span className="text-red-600 font-medium">{run.errors_count}</span>
                            ) : (
                              <span className="text-gray-400">0</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div className="text-center py-12">
                  <p className="text-gray-500">No processing runs yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </DashboardLayout>
    </AuthGuard>
  );
}
