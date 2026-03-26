'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  adminApi,
  adminNotificationsApi,
  AdminNotificationConfig,
  AdminNotificationConfigCreate,
  AdminNotificationConfigUpdate,
} from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  Users,
  Mail,
  Activity,
  Shield,
  Bell,
  Plus,
  Edit2,
  Trash2,
  Send,
  CheckCircle,
  XCircle,
  Loader2,
  X,
} from 'lucide-react';
import Link from 'next/link';

// ── Admin Notification Modal ─────────────────────────────────────────────

interface AdminNotificationModalProps {
  config?: AdminNotificationConfig | null;
  onClose: () => void;
}

function AdminNotificationModal({ config, onClose }: AdminNotificationModalProps) {
  const queryClient = useQueryClient();
  const isEdit = !!config;

  const [formData, setFormData] = useState<AdminNotificationConfigCreate>({
    name: config?.name ?? '',
    apprise_url: config?.apprise_url ?? '',
    is_enabled: config?.is_enabled ?? true,
    notify_on_errors: config?.notify_on_errors ?? true,
    notify_on_system_events: config?.notify_on_system_events ?? true,
    description: config?.description ?? '',
  });
  const [error, setError] = useState('');

  const onSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['admin-notifications'] });
    onClose();
  };

  const createMutation = useMutation({
    mutationFn: (data: AdminNotificationConfigCreate) => adminNotificationsApi.create(data),
    onSuccess,
    onError: () => setError('Failed to save. Please check the Apprise URL and try again.'),
  });

  const updateMutation = useMutation({
    mutationFn: (data: AdminNotificationConfigUpdate) =>
      adminNotificationsApi.update(config!.id, data),
    onSuccess,
    onError: () => setError('Failed to save. Please check the Apprise URL and try again.'),
  });

  const isPending = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!formData.name.trim() || !formData.apprise_url.trim()) {
      setError('Name and Apprise URL are required.');
      return;
    }
    if (isEdit) {
      updateMutation.mutate(formData);
    } else {
      createMutation.mutate(formData);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-5 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEdit ? 'Edit System Alert Channel' : 'Add System Alert Channel'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData((p) => ({ ...p, name: e.target.value }))}
              placeholder="e.g. Admin Telegram Alert"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Apprise URL</label>
            <input
              type="text"
              value={formData.apprise_url}
              onChange={(e) => setFormData((p) => ({ ...p, apprise_url: e.target.value }))}
              placeholder="tgram://bot_token/chat_id/"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Any valid{' '}
              <a
                href="https://apprise.readthedocs.io"
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                Apprise
              </a>{' '}
              notification URL.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description{' '}
              <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              value={formData.description ?? ''}
              onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value || null }))}
              placeholder="What is this channel used for?"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700">Triggers</p>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_enabled}
                onChange={(e) => setFormData((p) => ({ ...p, is_enabled: e.target.checked }))}
                className="h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
              />
              <span className="text-sm text-gray-800">Enabled</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.notify_on_errors}
                onChange={(e) => setFormData((p) => ({ ...p, notify_on_errors: e.target.checked }))}
                className="h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
              />
              <span className="text-sm text-gray-800">Notify on errors</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.notify_on_system_events}
                onChange={(e) =>
                  setFormData((p) => ({ ...p, notify_on_system_events: e.target.checked }))
                }
                className="h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
              />
              <span className="text-sm text-gray-800">Notify on system events</span>
            </label>
          </div>

          {error && <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex-1 py-2 bg-purple-600 text-white rounded-md text-sm hover:bg-purple-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {isEdit ? 'Save Changes' : 'Add Channel'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Admin Page ───────────────────────────────────────────────────────────

export default function AdminPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showNotifModal, setShowNotifModal] = useState(false);
  const [editingNotif, setEditingNotif] = useState<AdminNotificationConfig | null>(null);
  const [testingNotifId, setTestingNotifId] = useState<number | null>(null);
  const [notifTestResults, setNotifTestResults] = useState<
    Record<number, { success: boolean; message: string }>
  >({});

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

  const { data: adminNotifications, isLoading: notifLoading } = useQuery({
    queryKey: ['admin-notifications'],
    queryFn: adminNotificationsApi.list,
    enabled: !!user?.is_superuser,
  });

  const deleteNotifMutation = useMutation({
    mutationFn: adminNotificationsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-notifications'] });
    },
  });

  const handleEditNotif = (config: AdminNotificationConfig) => {
    setEditingNotif(config);
    setShowNotifModal(true);
  };

  const handleDeleteNotif = async (id: number) => {
    if (!confirm('Delete this system alert channel?')) return;
    try {
      await deleteNotifMutation.mutateAsync(id);
    } catch {
      alert('Failed to delete channel');
    }
  };

  const handleTestNotif = async (config: AdminNotificationConfig) => {
    setTestingNotifId(config.id);
    try {
      const result = await adminNotificationsApi.test(config.apprise_url);
      setNotifTestResults((prev) => ({ ...prev, [config.id]: result }));
    } catch {
      setNotifTestResults((prev) => ({
        ...prev,
        [config.id]: { success: false, message: 'Test request failed' },
      }));
    } finally {
      setTestingNotifId(null);
      setTimeout(() => {
        setNotifTestResults((prev) => {
          const next = { ...prev };
          delete next[config.id];
          return next;
        });
      }, 5000);
    }
  };

  const handleCloseNotifModal = () => {
    setShowNotifModal(false);
    setEditingNotif(null);
  };

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

            {/* System Alert Channels */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <Bell className="h-5 w-5 text-purple-600" />
                    System Alert Channels
                  </h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Admin-level channels that receive system-wide error and event notifications.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setEditingNotif(null);
                    setShowNotifModal(true);
                  }}
                  className="flex items-center px-3 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors text-sm font-medium"
                >
                  <Plus className="h-4 w-4 mr-1.5" />
                  Add Channel
                </button>
              </div>

              {notifLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-600" />
                </div>
              ) : adminNotifications && adminNotifications.length > 0 ? (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {adminNotifications.map((config) => {
                    const testResult = notifTestResults[config.id];
                    const isTesting = testingNotifId === config.id;
                    return (
                      <div
                        key={config.id}
                        className={`bg-white rounded-lg shadow border transition-opacity ${
                          config.is_enabled ? 'border-gray-200' : 'border-gray-200 opacity-60'
                        }`}
                      >
                        <div className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold text-gray-900 truncate">
                                {config.name}
                              </p>
                              {config.description && (
                                <p className="text-xs text-gray-500 mt-0.5 truncate">
                                  {config.description}
                                </p>
                              )}
                            </div>
                            <span
                              className={`ml-2 flex-shrink-0 flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                                config.is_enabled
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-gray-100 text-gray-500'
                              }`}
                            >
                              {config.is_enabled ? (
                                <CheckCircle className="h-3 w-3" />
                              ) : (
                                <XCircle className="h-3 w-3" />
                              )}
                              {config.is_enabled ? 'On' : 'Off'}
                            </span>
                          </div>

                          <div className="flex flex-wrap gap-1.5 mb-3">
                            {config.notify_on_errors && (
                              <span className="px-1.5 py-0.5 rounded text-xs bg-red-50 text-red-700 border border-red-200">
                                On Errors
                              </span>
                            )}
                            {config.notify_on_system_events && (
                              <span className="px-1.5 py-0.5 rounded text-xs bg-purple-50 text-purple-700 border border-purple-200">
                                System Events
                              </span>
                            )}
                          </div>

                          {testResult && (
                            <div
                              className={`mb-3 p-2 rounded text-xs flex items-center gap-1.5 ${
                                testResult.success
                                  ? 'bg-green-50 text-green-700 border border-green-200'
                                  : 'bg-red-50 text-red-700 border border-red-200'
                              }`}
                            >
                              {testResult.success ? (
                                <CheckCircle className="h-3.5 w-3.5 flex-shrink-0" />
                              ) : (
                                <XCircle className="h-3.5 w-3.5 flex-shrink-0" />
                              )}
                              {testResult.message}
                            </div>
                          )}

                          <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                            <button
                              onClick={() => handleTestNotif(config)}
                              disabled={isTesting}
                              title="Send test notification"
                              className="flex items-center justify-center px-2.5 py-1.5 text-xs font-medium text-purple-600 bg-purple-50 rounded-md hover:bg-purple-100 disabled:opacity-50 transition-colors"
                            >
                              {isTesting ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Send className="h-3.5 w-3.5 mr-1" />
                              )}
                              {isTesting ? '…' : 'Test'}
                            </button>
                            <button
                              onClick={() => handleEditNotif(config)}
                              className="flex-1 flex items-center justify-center px-2.5 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors"
                            >
                              <Edit2 className="h-3.5 w-3.5 mr-1" />
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteNotif(config.id)}
                              disabled={deleteNotifMutation.isPending}
                              className="flex-1 flex items-center justify-center px-2.5 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100 disabled:opacity-50 transition-colors"
                            >
                              <Trash2 className="h-3.5 w-3.5 mr-1" />
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-10 bg-white rounded-lg shadow border border-dashed border-gray-300">
                  <Bell className="mx-auto h-8 w-8 text-gray-300 mb-2" />
                  <p className="text-sm text-gray-500">No system alert channels configured yet.</p>
                  <button
                    onClick={() => {
                      setEditingNotif(null);
                      setShowNotifModal(true);
                    }}
                    className="mt-3 inline-flex items-center px-3 py-1.5 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors text-sm font-medium"
                  >
                    <Plus className="h-4 w-4 mr-1.5" />
                    Add First Channel
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {showNotifModal && (
          <AdminNotificationModal config={editingNotif} onClose={handleCloseNotifModal} />
        )}
      </DashboardLayout>
    </AuthGuard>
  );
}

