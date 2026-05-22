'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  RotateCcw,
} from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
}

function StatCard({ title, value, icon: Icon, iconColor }: StatCardProps) {
  return (
    <div className="ic-card p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
        </div>
        <div className={`rounded-lg p-3 ${iconColor}`}>
          <Icon className="h-8 w-8 text-white" />
        </div>
      </div>
    </div>
  );
}

function AccountStatusRow({ account }: { account: MailAccount }) {
  const hasError = !!account.last_error_message;
  const lastChecked = account.last_check_at;
  const queryClient = useQueryClient();

  const clearErrorMutation = useMutation({
    mutationFn: () => mailAccountsApi.clearError(account.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mail-accounts'] });
    },
  });

  return (
    <div className="px-5 py-4 border-b border-[#edf2f8] last:border-b-0">
      <div className="flex items-start justify-between gap-4">
        {/* Left: name + email */}
        <div className="flex items-center gap-3 min-w-0">
          <Inbox className="h-4 w-4 text-blue-500 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-950 truncate">{account.name}</p>
            <p className="text-xs text-slate-400 truncate">{account.email_address}</p>
          </div>
        </div>

        {/* Right: status badge + last check */}
        <div className="text-right shrink-0">
          {hasError ? (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-red-600">
              <XCircle className="h-3.5 w-3.5" />
              Error
            </span>
          ) : lastChecked ? (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-[#11834d]">
              <CheckCircle className="h-3.5 w-3.5" />
              OK
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-slate-400">
              <Clock className="h-3.5 w-3.5" />
              Pending
            </span>
          )}
          <p className="text-xs text-slate-400 mt-0.5">
            {formatRelative(lastChecked)}
          </p>
        </div>
      </div>

      {/* Error message */}
      {hasError && (
        <div className="mt-2 flex items-start gap-1.5 rounded-md border border-red-200 bg-red-50 p-2">
          <AlertTriangle className="h-3.5 w-3.5 text-red-500 shrink-0 mt-0.5" />
          <p className="text-xs text-red-700 line-clamp-2 flex-1">{account.last_error_message}</p>
          <button
            onClick={() => clearErrorMutation.mutate()}
            disabled={clearErrorMutation.isPending}
            title="Clear error status"
            className="flex-shrink-0 flex items-center gap-0.5 px-1.5 py-0.5 text-xs text-red-600 bg-red-100 hover:bg-red-200 rounded transition-colors disabled:opacity-50"
          >
            <RotateCcw className="h-3 w-3" />
            Clear
          </button>
        </div>
      )}

      {/* Lifetime counters (only when there's activity) */}
      {(account.total_emails_processed > 0 || account.total_emails_failed > 0) && (
        <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
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
              iconColor="bg-[#0b63f6]"
            />
            <StatCard
              title="Emails Processed"
              value={stats.totalProcessed.toLocaleString()}
              icon={Send}
              iconColor="bg-[#11834d]"
            />
            <StatCard
              title="Active Accounts"
              value={stats.activeAccounts}
              icon={CheckCircle}
              iconColor="bg-[#10213f]"
            />
            <StatCard
              title="Accounts with Errors"
              value={stats.accountsWithErrors}
              icon={AlertCircle}
              iconColor={stats.accountsWithErrors > 0 ? 'bg-red-500' : 'bg-slate-400'}
            />
          </div>

          {/* Mailbox Status Overview */}
          <div className="ic-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-[#d9e3f2] bg-[#fbfdff] px-6 py-4">
              <h3 className="text-lg font-bold text-slate-950">Mailbox Status</h3>
              <Link href="/logs" className="text-sm font-bold text-[#0b63f6] hover:text-[#0649bf]">
                View activity & history →
              </Link>
            </div>

            {accountsLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-[#0b63f6]" />
              </div>
            ) : accounts && accounts.length > 0 ? (
              <div>
                {accounts.map((account) => (
                  <AccountStatusRow key={account.id} account={account} />
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <Clock className="mx-auto h-10 w-10 text-slate-300 mb-3" />
                <p className="text-sm text-slate-500">No mail accounts configured yet.</p>
                <Link
                  href="/accounts"
                  className="mt-3 inline-block text-sm font-bold text-[#0b63f6] hover:text-[#0649bf]"
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
