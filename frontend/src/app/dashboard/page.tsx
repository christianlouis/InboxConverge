'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery } from '@tanstack/react-query';
import { mailAccountsApi, MailAccount } from '@/lib/api';
import { formatRelative } from '@/lib/date-utils';
import Link from 'next/link';
import {
  Mail,
  Send,
  CheckCircle,
  AlertCircle,
  Clock,
  XCircle,
  AlertTriangle,
  Inbox,
} from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
}

function StatCard({ title, value, icon: Icon, iconColor }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="mt-2 text-3xl font-semibold text-gray-900">{value}</p>
        </div>
        <div className={`p-3 rounded-full ${iconColor}`}>
          <Icon className="h-8 w-8 text-white" />
        </div>
      </div>
    </div>
  );
}

function AccountStatusRow({ account }: { account: MailAccount }) {
  const hasError = !!account.last_error_message;
  const lastChecked = account.last_check_at;

  return (
    <div className="px-5 py-4 border-b border-gray-100 last:border-b-0">
      <div className="flex items-start justify-between gap-4">
        {/* Left: name + email */}
        <div className="flex items-center gap-3 min-w-0">
          <Inbox className="h-4 w-4 text-blue-400 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate">{account.name}</p>
            <p className="text-xs text-gray-400 truncate">{account.email_address}</p>
          </div>
        </div>

        {/* Right: status badge + last check */}
        <div className="text-right shrink-0">
          {hasError ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600">
              <XCircle className="h-3.5 w-3.5" />
              Error
            </span>
          ) : lastChecked ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-green-600">
              <CheckCircle className="h-3.5 w-3.5" />
              OK
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-400">
              <Clock className="h-3.5 w-3.5" />
              Pending
            </span>
          )}
          <p className="text-xs text-gray-400 mt-0.5">
            {formatRelative(lastChecked)}
          </p>
        </div>
      </div>

      {/* Error message */}
      {hasError && (
        <div className="mt-2 flex items-start gap-1.5 p-2 bg-red-50 border border-red-200 rounded">
          <AlertTriangle className="h-3.5 w-3.5 text-red-500 shrink-0 mt-0.5" />
          <p className="text-xs text-red-700 line-clamp-2">{account.last_error_message}</p>
        </div>
      )}

      {/* Lifetime counters (only when there's activity) */}
      {(account.total_emails_processed > 0 || account.total_emails_failed > 0) && (
        <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
          <span>{account.total_emails_processed.toLocaleString()} processed</span>
          {account.total_emails_failed > 0 && (
            <span className="text-red-500">{account.total_emails_failed.toLocaleString()} failed</span>
          )}
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ['mail-accounts'],
    queryFn: mailAccountsApi.list,
  });

  const stats = {
    totalAccounts: accounts?.length || 0,
    activeAccounts: accounts?.filter((a) => a.is_enabled).length || 0,
    totalProcessed: accounts?.reduce((sum, a) => sum + a.total_emails_processed, 0) || 0,
    accountsWithErrors: accounts?.filter((a) => !!a.last_error_message).length || 0,
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
              title="Emails Processed"
              value={stats.totalProcessed.toLocaleString()}
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
              title="Accounts with Errors"
              value={stats.accountsWithErrors}
              icon={AlertCircle}
              iconColor={stats.accountsWithErrors > 0 ? 'bg-red-500' : 'bg-gray-400'}
            />
          </div>

          {/* Mailbox Status Overview */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Mailbox Status</h3>
              <Link href="/logs" className="text-sm text-blue-600 hover:text-blue-800 font-medium">
                View activity & history →
              </Link>
            </div>

            {accountsLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              </div>
            ) : accounts && accounts.length > 0 ? (
              <div>
                {accounts.map((account) => (
                  <AccountStatusRow key={account.id} account={account} />
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <Clock className="mx-auto h-10 w-10 text-gray-300 mb-3" />
                <p className="text-sm text-gray-500">No mail accounts configured yet.</p>
                <Link
                  href="/accounts"
                  className="mt-3 inline-block text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  Add your first account →
                </Link>
              </div>
            )}
          </div>
        </div>
      </DashboardLayout>
    </AuthGuard>
  );
}
