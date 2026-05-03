'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { mailAccountsApi, MailAccount, MailAccountCreate, MailAccountUpdate } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { X, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { ProviderWizard } from './ProviderWizard';

interface AddMailAccountModalProps {
  account?: MailAccount | null;
  onClose: () => void;
}

type WizardStep = 'provider' | 'form';

export function AddMailAccountModal({ account, onClose }: AddMailAccountModalProps) {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isEditMode = !!account;
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [testMessage, setTestMessage] = useState('');
  const [autoDetecting, setAutoDetecting] = useState(false);
  const [wizardStep, setWizardStep] = useState<WizardStep>(isEditMode ? 'form' : 'provider');

  const [formData, setFormData] = useState<MailAccountCreate>({
    name: account?.name || '',
    email_address: account?.email_address || '',
    protocol: account?.protocol || 'pop3_ssl',
    host: account?.host || '',
    port: account?.port || 995,
    username: account?.username || '',
    password: '',
    use_ssl: account?.use_ssl ?? true,
    use_tls: account?.use_tls ?? false,
    forward_to: account?.forward_to || user?.email || '',
    delivery_method: account?.delivery_method || 'gmail_api',
    is_enabled: account?.is_enabled ?? true,
    check_interval_minutes: account?.check_interval_minutes || 5,
    max_emails_per_check: account?.max_emails_per_check || 50,
    delete_after_forward: account?.delete_after_forward ?? true,
    debug_logging: account?.debug_logging ?? false,
    provider_name: account?.provider_name ?? null,
  });

  const onMutationSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['mail-accounts'] });
    onClose();
  };

  const createMutation = useMutation({
    mutationFn: (data: MailAccountCreate) => mailAccountsApi.create(data),
    onSuccess: onMutationSuccess,
  });

  const updateMutation = useMutation({
    mutationFn: (data: MailAccountUpdate) => mailAccountsApi.update(account!.id, data),
    onSuccess: onMutationSuccess,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const newValue =
      type === 'checkbox'
        ? (e.target as HTMLInputElement).checked
        : type === 'number'
        ? Number(value)
        : value;

    setFormData((prev) => {
      const updated = { ...prev, [name]: newValue };
      // Keep email_address in sync with username unless explicitly changed
      if (name === 'username') {
        updated.email_address = value;
      }
      return updated;
    });
  };

  const handleProviderSelect = (config: { name: string; provider_name: string; protocol: string; host: string; port: number; use_ssl: boolean }) => {
    setFormData((prev) => ({
      ...prev,
      name: config.name,
      protocol: config.protocol,
      host: config.host,
      port: config.port,
      use_ssl: config.use_ssl,
      provider_name: config.provider_name,
    }));
    setWizardStep('form');
  };

  const handleAutoDetect = async () => {
    if (!formData.username) {
      alert('Please enter an email address first');
      return;
    }

    setAutoDetecting(true);
    try {
      const result = await mailAccountsApi.autoDetect(formData.username);
      const suggestion = result.success && result.suggestions.length > 0 ? result.suggestions[0] : null;
      if (suggestion) {
        setFormData((prev) => ({
          ...prev,
          protocol: suggestion.protocol || prev.protocol,
          host: suggestion.host || prev.host,
          port: suggestion.port || prev.port,
          use_ssl: suggestion.use_ssl ?? prev.use_ssl,
        }));
      }
      alert('Settings auto-detected successfully!');
    } catch {
      alert('Failed to auto-detect settings. Please enter manually.');
    } finally {
      setAutoDetecting(false);
    }
  };

  const extractErrorMessage = (error: unknown, fallback: string): string => {
    interface FastAPIValidationError { msg: string; loc?: unknown[]; type?: string }
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const msgs = (detail as FastAPIValidationError[]).map((d) => d?.msg ?? JSON.stringify(d));
      return msgs.join('; ');
    }
    if (error instanceof Error && error.message) return error.message;
    return fallback;
  };

  const handleTestConnection = async () => {
    setTestStatus('testing');
    setTestMessage('');
    try {
      let result: { success: boolean; message: string };

      if (isEditMode && !formData.password && account?.id) {
        // Edit mode with no new password entered — test using stored credentials
        result = await mailAccountsApi.testExisting(account.id);
      } else {
        if (!formData.username || !formData.password || !formData.host) {
          setTestStatus('error');
          setTestMessage('Please fill in username, password, and host');
          return;
        }
        result = await mailAccountsApi.test({
          protocol: formData.protocol,
          host: formData.host,
          port: formData.port,
          username: formData.username,
          password: formData.password,
          use_ssl: formData.use_ssl,
        });
      }

      if (result.success) {
        setTestStatus('success');
        setTestMessage(result.message);
      } else {
        setTestStatus('error');
        setTestMessage(result.message || 'Connection failed');
      }
    } catch (error) {
      setTestStatus('error');
      setTestMessage(extractErrorMessage(error, 'Connection failed'));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEditMode) {
        // Send all fields so the user can change any aspect of the account.
        // Password is the only exception: omit it when blank so the stored
        // credential is preserved.
        const updateData: MailAccountUpdate = {
          name: formData.name,
          email_address: formData.email_address,
          protocol: formData.protocol,
          host: formData.host,
          port: formData.port,
          use_ssl: formData.use_ssl,
          use_tls: formData.use_tls,
          username: formData.username,
          forward_to: formData.forward_to,
          delivery_method: formData.delivery_method,
          is_enabled: formData.is_enabled,
          check_interval_minutes: formData.check_interval_minutes,
          max_emails_per_check: formData.max_emails_per_check,
          delete_after_forward: formData.delete_after_forward,
          debug_logging: formData.debug_logging,
        };
        if (formData.password) {
          updateData.password = formData.password;
        }
        await updateMutation.mutateAsync(updateData);
      } else {
        await createMutation.mutateAsync(formData);
      }
    } catch (error) {
      alert(extractErrorMessage(error, 'Failed to save account'));
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div className="fixed inset-0 bg-gray-500/75 transition-opacity" onClick={onClose} />

        <div className="relative z-10 bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all w-full sm:my-8 sm:max-w-2xl">
          <form onSubmit={handleSubmit}>
            <div className="bg-white px-6 pt-6 pb-4">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">
                  {isEditMode ? 'Edit Mail Account' : 'Add Mail Account'}
                </h3>
                <button
                  type="button"
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-500"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>

              {wizardStep === 'provider' && !isEditMode ? (
                <ProviderWizard
                  onSelect={handleProviderSelect}
                  onManual={() => setWizardStep('form')}
                />
              ) : (
                <div className="space-y-4">
                  {!isEditMode && (
                    <button
                      type="button"
                      onClick={() => setWizardStep('provider')}
                      className="text-sm text-blue-600 hover:text-blue-800 mb-2"
                    >
                      ← Back to provider selection
                    </button>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Account Name
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="My Email Account"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email Address / Username
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        name="username"
                        value={formData.username}
                        onChange={handleChange}
                        required={!isEditMode}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="user@example.com"
                      />
                      <button
                        type="button"
                        onClick={handleAutoDetect}
                        disabled={autoDetecting}
                        className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
                      >
                        {autoDetecting ? 'Detecting...' : 'Auto-Detect'}
                      </button>
                    </div>

                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      required={!isEditMode}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder={isEditMode ? 'Leave blank to keep current password' : 'Password'}
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Protocol
                      </label>
                      <select
                        name="protocol"
                        value={formData.protocol}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="pop3">POP3</option>
                        <option value="pop3_ssl">POP3 (SSL)</option>
                        <option value="imap">IMAP</option>
                        <option value="imap_ssl">IMAP (SSL)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Host
                      </label>
                      <input
                        type="text"
                        name="host"
                        value={formData.host}
                        onChange={handleChange}
                        required={!isEditMode}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="pop.gmail.com"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Port
                      </label>
                      <input
                        type="number"
                        name="port"
                        value={formData.port}
                        onChange={handleChange}
                        required={!isEditMode}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        name="use_ssl"
                        id="use_ssl"
                        checked={formData.use_ssl}
                        onChange={handleChange}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <label htmlFor="use_ssl" className="ml-2 block text-sm text-gray-700">
                        Use SSL/TLS
                      </label>
                    </div>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        name="delete_after_forward"
                        id="delete_after_forward"
                        checked={formData.delete_after_forward}
                        onChange={handleChange}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <label htmlFor="delete_after_forward" className="ml-2 block text-sm text-gray-700">
                        Delete after forwarding
                      </label>
                    </div>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        name="is_enabled"
                        id="is_enabled"
                        checked={formData.is_enabled ?? true}
                        onChange={handleChange}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <label htmlFor="is_enabled" className="ml-2 block text-sm text-gray-700">
                        Enabled
                      </label>
                    </div>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        name="debug_logging"
                        id="debug_logging"
                        checked={formData.debug_logging ?? false}
                        onChange={handleChange}
                        className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                      />
                      <label htmlFor="debug_logging" className="ml-2 block text-sm text-gray-700">
                        Debug logging
                        <span className="ml-1 text-xs text-gray-400">(auto-disables after 5 runs)</span>
                      </label>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Forward To (destination email)
                    </label>
                    <input
                      type="email"
                      name="forward_to"
                      value={formData.forward_to}
                      onChange={handleChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="you@gmail.com"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Fetched emails will be delivered to this address.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Delivery Method
                      </label>
                      <select
                        name="delivery_method"
                        value={formData.delivery_method}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="gmail_api">Gmail API (recommended)</option>
                        <option value="smtp">SMTP</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Check Interval (minutes)
                      </label>
                      <input
                        type="number"
                        name="check_interval_minutes"
                        value={formData.check_interval_minutes}
                        onChange={handleChange}
                        required
                        min="1"
                        max="1440"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Max Emails Per Check
                    </label>
                    <input
                      type="number"
                      name="max_emails_per_check"
                      value={formData.max_emails_per_check}
                      onChange={handleChange}
                      min="1"
                      max="1000"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  {testStatus !== 'idle' && (
                    <div
                      className={`p-3 rounded-md flex items-start ${
                        testStatus === 'success'
                          ? 'bg-green-50 border border-green-200'
                          : testStatus === 'error'
                          ? 'bg-red-50 border border-red-200'
                          : 'bg-blue-50 border border-blue-200'
                      }`}
                    >
                      {testStatus === 'testing' && <Loader2 className="h-5 w-5 text-blue-500 animate-spin mr-2" />}
                      {testStatus === 'success' && <CheckCircle className="h-5 w-5 text-green-500 mr-2" />}
                      {testStatus === 'error' && <XCircle className="h-5 w-5 text-red-500 mr-2" />}
                      <span
                        className={`text-sm ${
                          testStatus === 'success'
                            ? 'text-green-700'
                            : testStatus === 'error'
                            ? 'text-red-700'
                            : 'text-blue-700'
                        }`}
                      >
                        {testStatus === 'testing' ? 'Testing connection...' : testMessage}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {wizardStep === 'form' && (
              <div className="bg-gray-50 px-6 py-4 flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testStatus === 'testing'}
                  className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50"
                >
                  Test Connection
                </button>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createMutation.isPending || updateMutation.isPending}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {(createMutation.isPending || updateMutation.isPending) ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
