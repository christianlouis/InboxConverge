'use client';

import { useState } from 'react';
import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationsApi, NotificationConfig, NotificationConfigCreate, NotificationConfigUpdate } from '@/lib/api';
import { NotificationWizard } from '@/components/NotificationWizard';
import { Plus, Edit2, Trash2, Bell, Send, CheckCircle, XCircle, Loader2 } from 'lucide-react';

const CHANNEL_DISPLAY: Record<string, { icon: string; label: string; color: string }> = {
  telegram: { icon: '🤖', label: 'Telegram', color: 'bg-blue-100 text-blue-800' },
  discord: { icon: '💬', label: 'Discord', color: 'bg-indigo-100 text-indigo-800' },
  slack: { icon: '💼', label: 'Slack', color: 'bg-yellow-100 text-yellow-800' },
  email: { icon: '📧', label: 'Email', color: 'bg-green-100 text-green-800' },
  webhook: { icon: '🔗', label: 'Webhook', color: 'bg-purple-100 text-purple-800' },
  custom: { icon: '⚙️', label: 'Custom', color: 'bg-gray-100 text-gray-800' },
};

export default function NotificationsPage() {
  const [showWizard, setShowWizard] = useState(false);
  const [editingConfig, setEditingConfig] = useState<NotificationConfig | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResults, setTestResults] = useState<Record<number, { success: boolean; message: string }>>({});
  const queryClient = useQueryClient();

  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: notificationsApi.list,
  });

  const createMutation = useMutation({
    mutationFn: (data: NotificationConfigCreate) => notificationsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      setShowWizard(false);
      setEditingConfig(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: NotificationConfigUpdate }) =>
      notificationsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      setShowWizard(false);
      setEditingConfig(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: notificationsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_enabled }: { id: number; is_enabled: boolean }) =>
      notificationsApi.update(id, { is_enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const handleWizardComplete = (config: {
    name: string;
    channel: string;
    apprise_url: string;
    notify_on_errors: boolean;
    notify_on_success: boolean;
  }) => {
    if (editingConfig) {
      updateMutation.mutate({ id: editingConfig.id, data: config });
    } else {
      createMutation.mutate(config);
    }
  };

  const handleEdit = (config: NotificationConfig) => {
    setEditingConfig(config);
    setShowWizard(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this notification channel?')) return;
    try {
      await deleteMutation.mutateAsync(id);
    } catch {
      alert('Failed to delete notification channel');
    }
  };

  const handleTest = async (config: NotificationConfig) => {
    if (!config.apprise_url) return;
    setTestingId(config.id);
    try {
      const result = await notificationsApi.test(config.apprise_url);
      setTestResults((prev) => ({ ...prev, [config.id]: result }));
    } catch {
      setTestResults((prev) => ({
        ...prev,
        [config.id]: { success: false, message: 'Test request failed' },
      }));
    } finally {
      setTestingId(null);
      setTimeout(() => {
        setTestResults((prev) => {
          const next = { ...prev };
          delete next[config.id];
          return next;
        });
      }, 5000);
    }
  };

  const handleOpenWizard = () => {
    setEditingConfig(null);
    setShowWizard(true);
  };

  const handleCancelWizard = () => {
    setShowWizard(false);
    setEditingConfig(null);
  };

  if (showWizard) {
    return (
      <AuthGuard>
        <DashboardLayout>
          <div className="max-w-xl mx-auto">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <NotificationWizard
                onComplete={handleWizardComplete}
                onCancel={handleCancelWizard}
                initialData={
                  editingConfig
                    ? {
                        name: editingConfig.name,
                        channel: editingConfig.channel,
                        apprise_url: editingConfig.apprise_url,
                        notify_on_errors: editingConfig.notify_on_errors,
                        notify_on_success: editingConfig.notify_on_success,
                      }
                    : null
                }
              />
            </div>
          </div>
        </DashboardLayout>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <Bell className="h-6 w-6 text-blue-600" />
                Notification Channels
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                Get alerts when emails are processed or errors occur.
              </p>
            </div>
            <button
              onClick={handleOpenWizard}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Channel
            </button>
          </div>

          {/* Content */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : notifications && notifications.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {notifications.map((config) => {
                const channel = CHANNEL_DISPLAY[config.channel] ?? CHANNEL_DISPLAY.custom;
                const testResult = testResults[config.id];
                const isTesting = testingId === config.id;

                return (
                  <div
                    key={config.id}
                    className={`bg-white rounded-lg shadow border overflow-hidden transition-opacity ${
                      config.is_enabled ? 'border-gray-200' : 'border-gray-200 opacity-60'
                    }`}
                  >
                    <div className="p-5">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <span className="text-2xl flex-shrink-0">{channel.icon}</span>
                          <div className="min-w-0">
                            <h3 className="text-sm font-semibold text-gray-900 truncate">
                              {config.name}
                            </h3>
                            <span
                              className={`inline-block mt-0.5 px-2 py-0.5 rounded-full text-xs font-medium ${channel.color}`}
                            >
                              {channel.label}
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={() =>
                            toggleMutation.mutate({
                              id: config.id,
                              is_enabled: !config.is_enabled,
                            })
                          }
                          disabled={toggleMutation.isPending}
                          title={config.is_enabled ? 'Disable' : 'Enable'}
                          className={`ml-2 flex-shrink-0 flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                            config.is_enabled
                              ? 'bg-green-100 text-green-700 hover:bg-green-200'
                              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                          }`}
                        >
                          {config.is_enabled ? (
                            <CheckCircle className="h-3 w-3" />
                          ) : (
                            <XCircle className="h-3 w-3" />
                          )}
                          {config.is_enabled ? 'On' : 'Off'}
                        </button>
                      </div>

                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {config.notify_on_errors && (
                          <span className="px-2 py-0.5 rounded text-xs bg-red-50 text-red-700 border border-red-200">
                            On Errors
                          </span>
                        )}
                        {config.notify_on_success && (
                          <span className="px-2 py-0.5 rounded text-xs bg-green-50 text-green-700 border border-green-200">
                            On Success
                          </span>
                        )}
                        {!config.notify_on_errors && !config.notify_on_success && (
                          <span className="px-2 py-0.5 rounded text-xs bg-gray-50 text-gray-500 border border-gray-200">
                            No triggers set
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
                          onClick={() => handleTest(config)}
                          disabled={isTesting || !config.apprise_url}
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
                          onClick={() => handleEdit(config)}
                          className="flex-1 flex items-center justify-center px-2.5 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors"
                        >
                          <Edit2 className="h-3.5 w-3.5 mr-1" />
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(config.id)}
                          disabled={deleteMutation.isPending}
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
            <div className="text-center py-16 bg-white rounded-lg shadow border border-dashed border-gray-300">
              <Bell className="mx-auto h-12 w-12 text-gray-300 mb-3" />
              <h3 className="text-base font-semibold text-gray-700 mb-1">
                No notification channels yet
              </h3>
              <p className="text-sm text-gray-500 mb-4 max-w-xs mx-auto">
                Add a channel to receive alerts when emails are processed or errors occur.
              </p>
              <button
                onClick={handleOpenWizard}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Channel
              </button>
            </div>
          )}

          {/* Info box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-blue-900 mb-1">About Notifications</h4>
            <p className="text-xs text-blue-700 leading-relaxed">
              Notifications are powered by{' '}
              <a
                href="https://github.com/caronc/apprise"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-blue-900"
              >
                Apprise
              </a>
              , which supports 80+ notification services including Telegram, Discord, Slack, email,
              and many more. Each channel can be configured independently with different triggers.
            </p>
          </div>
        </div>
      </DashboardLayout>
    </AuthGuard>
  );
}
