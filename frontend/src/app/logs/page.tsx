'use client';

import { useState } from 'react';
import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery } from '@tanstack/react-query';
import { processingRunsApi, ProcessingRun, ProcessingLog } from '@/lib/api';
import {
  FileText,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronUp,
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
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'short',
    timeStyle: 'medium',
  });
}

function RunRow({ run }: { run: ProcessingRun }) {
  const [expanded, setExpanded] = useState(false);
  const [logsPage, setLogsPage] = useState(1);

  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ['run-logs', run.id, logsPage],
    queryFn: () => processingRunsApi.getLogs(run.id, { page: logsPage, page_size: 20 }),
    enabled: expanded,
  });

  const statusClass = STATUS_STYLES[run.status] ?? 'bg-gray-100 text-gray-800';

  return (
    <>
      <tr
        className="hover:bg-gray-50 cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
          {formatDate(run.started_at)}
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
          <div className="font-medium">{run.account_name ?? '—'}</div>
          <div className="text-xs text-gray-400">{run.account_email ?? ''}</div>
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${statusClass}`}>
            {run.status}
          </span>
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 text-right whitespace-nowrap">
          {run.emails_fetched}
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 text-right whitespace-nowrap">
          {run.emails_forwarded}
        </td>
        <td className="px-4 py-3 text-sm text-red-600 text-right whitespace-nowrap">
          {run.emails_failed > 0 ? run.emails_failed : <span className="text-gray-400">0</span>}
        </td>
        <td className="px-4 py-3 text-sm text-gray-500 text-right whitespace-nowrap">
          {formatDuration(run.duration_seconds)}
        </td>
        <td className="px-4 py-3 text-right">
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400 inline" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400 inline" />
          )}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={8} className="bg-gray-50 px-6 py-4 border-b border-gray-100">
            {run.error_message && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                {run.error_message}
              </div>
            )}
            {logsLoading ? (
              <div className="flex items-center gap-2 text-sm text-gray-500 py-2">
                <RefreshCw className="h-4 w-4 animate-spin" /> Loading logs…
              </div>
            ) : logsData && logsData.items.length > 0 ? (
              <>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-400 uppercase tracking-wide">
                      <th className="text-left pb-1 pr-4">Time</th>
                      <th className="text-left pb-1 pr-4">Level</th>
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
                        <td className="py-1 pr-4">
                          <span
                            className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                              log.level === 'ERROR'
                                ? 'bg-red-100 text-red-700'
                                : log.level === 'WARNING'
                                ? 'bg-yellow-100 text-yellow-700'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {log.level}
                          </span>
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
                  <div className="flex items-center gap-2 mt-3 text-xs text-gray-500">
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
                    <span>
                      Page {logsPage} of {logsData.pages}
                    </span>
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
              <p className="text-sm text-gray-400 py-2">No per-email logs recorded for this run.</p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export default function LogsPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['processing-runs', page],
    queryFn: () => processingRunsApi.list({ page, page_size: 20 }),
  });

  return (
    <AuthGuard>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <FileText className="h-6 w-6 text-blue-600" />
                Processing Logs
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                History of email processing runs for all your mail accounts.
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

          {/* Table */}
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : isError ? (
            <div className="text-center py-16 text-red-500">
              Failed to load processing logs. Please try again.
            </div>
          ) : data && data.items.length > 0 ? (
            <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <th className="px-4 py-3">Started</th>
                      <th className="px-4 py-3">Account</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Fetched</th>
                      <th className="px-4 py-3 text-right">Forwarded</th>
                      <th className="px-4 py-3 text-right">Failed</th>
                      <th className="px-4 py-3 text-right">Duration</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.items.map((run) => (
                      <RunRow key={run.id} run={run} />
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {data.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                  <span className="text-sm text-gray-500">
                    Page {data.page} of {data.pages} ({data.total} runs)
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
              <Clock className="mx-auto h-12 w-12 text-gray-300 mb-3" />
              <h3 className="text-base font-semibold text-gray-700 mb-1">No processing runs yet</h3>
              <p className="text-sm text-gray-500 max-w-xs mx-auto">
                Logs will appear here once your mail accounts start processing emails.
              </p>
            </div>
          )}
        </div>
      </DashboardLayout>
    </AuthGuard>
  );
}
