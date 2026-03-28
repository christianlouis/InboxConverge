'use client';

import { useState } from 'react';
import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery } from '@tanstack/react-query';
import { processingRunsApi, mailAccountsApi, MailAccount, ProcessingRun, ProcessingLog } from '@/lib/api';
import { parseUTC } from '@/lib/date-utils';
import {
  Inbox,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from 'lucide-react';

function formatRelative(iso?: string | null): string {
  if (!iso) return 'Never';
  const diff = Date.now() - parseUTC(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatDate(iso: string): string {
  return parseUTC(iso).toLocaleString(undefined, {
    dateStyle: 'short',
    timeStyle: 'medium',
  });
}

function formatDuration(seconds?: number | null): string {
  if (seconds == null) return '—';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const totalSecs = Math.floor(seconds);
  return `${Math.floor(totalSecs / 60)}m ${totalSecs % 60}s`;
}

function RunDetailRow({ run }: { run: ProcessingRun }) {
  const [expanded, setExpanded] = useState(false);
  const [logsPage, setLogsPage] = useState(1);

  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ['run-logs', run.id, logsPage],
    queryFn: () => processingRunsApi.getLogs(run.id, { page: logsPage, page_size: 20 }),
    enabled: expanded,
  });

  return (
    <>
      <tr
        className="hover:bg-gray-50 cursor-pointer text-sm"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-2 text-gray-700 whitespace-nowrap">{formatDate(run.started_at)}</td>
        <td className="px-4 py-2 text-right text-gray-900 font-medium">{run.emails_fetched}</td>
        <td className="px-4 py-2 text-right text-gray-700">{run.emails_forwarded}</td>
        <td className="px-4 py-2 text-right">
          {run.emails_failed > 0 ? (
            <span className="text-red-600 font-medium">{run.emails_failed}</span>
          ) : (
            <span className="text-gray-400">0</span>
          )}
        </td>
        <td className="px-4 py-2 text-right text-gray-500">{formatDuration(run.duration_seconds)}</td>
        <td className="px-4 py-2 text-right">
          {expanded ? (
            <ChevronUp className="h-3.5 w-3.5 text-gray-400 inline" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5 text-gray-400 inline" />
          )}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={6} className="bg-gray-50 px-6 py-3 border-b border-gray-100">
            {run.error_message && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                {run.error_message}
              </div>
            )}
            {logsLoading ? (
              <div className="flex items-center gap-2 text-sm text-gray-500 py-1">
                <RefreshCw className="h-4 w-4 animate-spin" /> Loading…
              </div>
            ) : logsData && logsData.items.length > 0 ? (
              <>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-400 uppercase tracking-wide">
                      <th className="text-left pb-1 pr-4">Time</th>
                      <th className="text-left pb-1 pr-4">Subject</th>
                      <th className="text-left pb-1 pr-4">From</th>
                      <th className="text-left pb-1">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logsData.items.map((log: ProcessingLog) => (
                      <tr key={log.id} className="border-t border-gray-100">
                        <td className="py-1 pr-4 text-gray-500 whitespace-nowrap">
                          {formatDate(log.timestamp)}
                        </td>
                        <td className="py-1 pr-4 text-gray-700 max-w-xs truncate">
                          {log.email_subject ?? '—'}
                        </td>
                        <td className="py-1 pr-4 text-gray-500 max-w-xs truncate">
                          {log.email_from ?? '—'}
                        </td>
                        <td className="py-1">
                          {log.success ? (
                            <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                          ) : (
                            <XCircle className="h-3.5 w-3.5 text-red-500" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {logsData.pages > 1 && (
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setLogsPage((p) => Math.max(1, p - 1));
                      }}
                      disabled={logsPage === 1}
                      className="p-1 rounded hover:bg-gray-200 disabled:opacity-40"
                    >
                      <ChevronLeft className="h-3.5 w-3.5" />
                    </button>
                    <span>Page {logsPage} of {logsData.pages}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setLogsPage((p) => Math.min(logsData.pages, p + 1));
                      }}
                      disabled={logsPage === logsData.pages}
                      className="p-1 rounded hover:bg-gray-200 disabled:opacity-40"
                    >
                      <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </>
            ) : (
              <p className="text-xs text-gray-400 py-1">No per-email logs for this run.</p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function MailboxCard({
  account,
  runs,
}: {
  account: MailAccount;
  runs: ProcessingRun[];
}) {
  const [showHistory, setShowHistory] = useState(false);
  const hasError = !!account.last_error_message;
  const lastChecked = account.last_check_at;

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      {/* Mailbox header */}
      <div className="px-5 py-4 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <Inbox className="h-5 w-5 text-blue-500 shrink-0" />
          <div className="min-w-0">
            <p className="font-semibold text-gray-900 truncate">{account.name}</p>
            <p className="text-xs text-gray-500 truncate">{account.email_address}</p>
          </div>
        </div>
        {/* Last attempt status */}
        <div className="text-right shrink-0">
          {hasError ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600">
              <XCircle className="h-4 w-4" />
              Error
            </span>
          ) : lastChecked ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-green-600">
              <CheckCircle className="h-4 w-4" />
              OK
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-400">
              <Clock className="h-4 w-4" />
              Pending
            </span>
          )}
          <p className="text-xs text-gray-400 mt-0.5">
            Last check: {formatRelative(lastChecked)}
          </p>
        </div>
      </div>

      {/* Error message */}
      {hasError && (
        <div className="mx-5 mb-3 p-2 bg-red-50 border border-red-200 rounded flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
          <p className="text-xs text-red-700">{account.last_error_message}</p>
        </div>
      )}

      {/* Successful pulls summary */}
      <div className="border-t border-gray-100 px-5 py-3">
        {runs.length === 0 ? (
          <p className="text-xs text-gray-400">No emails fetched yet.</p>
        ) : (
          <>
            <button
              onClick={() => setShowHistory((v) => !v)}
              className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              {showHistory ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              {runs.length} successful pull{runs.length !== 1 ? 's' : ''}
              {runs[0] && (
                <span className="text-gray-400 font-normal text-xs ml-1">
                  — last {formatRelative(runs[0].started_at)}
                </span>
              )}
            </button>

            {showHistory && (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                      <th className="px-4 pb-2">Date</th>
                      <th className="px-4 pb-2 text-right">Fetched</th>
                      <th className="px-4 pb-2 text-right">Forwarded</th>
                      <th className="px-4 pb-2 text-right">Failed</th>
                      <th className="px-4 pb-2 text-right">Duration</th>
                      <th className="px-4 pb-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {runs.map((run) => (
                      <RunDetailRow key={run.id} run={run} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function LogsPage() {
  const [runsPage, setRunsPage] = useState(1);

  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ['mail-accounts'],
    queryFn: mailAccountsApi.list,
  });

  // Fetch recent successful runs (emails_fetched > 0) across all accounts
  const { data: runsData, isLoading: runsLoading, isError, refetch } = useQuery({
    queryKey: ['processing-runs-meaningful', runsPage],
    queryFn: () =>
      processingRunsApi.list({ page: runsPage, page_size: 100, has_emails: true }),
  });

  const isLoading = accountsLoading || runsLoading;

  // Group runs by account id
  const runsByAccount = (runsData?.items ?? []).reduce<Record<number, ProcessingRun[]>>(
    (acc, run) => {
      if (!acc[run.mail_account_id]) acc[run.mail_account_id] = [];
      acc[run.mail_account_id].push(run);
      return acc;
    },
    {}
  );

  return (
    <AuthGuard>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <Inbox className="h-6 w-6 text-blue-600" />
                Mailbox Activity
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                Last check status and successful email pulls for each mailbox.
              </p>
            </div>
            <button
              onClick={() => refetch()}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : isError ? (
            <div className="text-center py-16 text-red-500">
              Failed to load mailbox activity. Please try again.
            </div>
          ) : accounts && accounts.length > 0 ? (
            <>
              <div className="space-y-4">
                {accounts.map((account) => (
                  <MailboxCard
                    key={account.id}
                    account={account}
                    runs={runsByAccount[account.id] ?? []}
                  />
                ))}
              </div>

              {/* Pagination for runs (only shown when there are multiple pages) */}
              {runsData && runsData.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 bg-white border border-gray-200 rounded-lg">
                  <span className="text-sm text-gray-500">
                    Showing page {runsData.page} of {runsData.pages} ({runsData.total} successful pulls)
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setRunsPage((p) => Math.max(1, p - 1))}
                      disabled={runsPage === 1}
                      className="flex items-center px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-40 transition-colors"
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </button>
                    <button
                      onClick={() => setRunsPage((p) => Math.min(runsData.pages, p + 1))}
                      disabled={runsPage === runsData.pages}
                      className="flex items-center px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-40 transition-colors"
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-16 bg-white rounded-lg shadow border border-dashed border-gray-300">
              <Clock className="mx-auto h-12 w-12 text-gray-300 mb-3" />
              <h3 className="text-base font-semibold text-gray-700 mb-1">No mail accounts yet</h3>
              <p className="text-sm text-gray-500 max-w-xs mx-auto">
                Add a mail account to start seeing activity here.
              </p>
            </div>
          )}
        </div>
      </DashboardLayout>
    </AuthGuard>
  );
}

