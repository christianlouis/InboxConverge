'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { mailAccountsApi, MailAccount, MailAccountCreate } from '@/lib/api';
import { X, Loader2, CheckCircle, XCircle } from 'lucide-react';

interface AddMailAccountModalProps {
  account?: MailAccount | null;
  onClose: () => void;
}

export function AddMailAccountModal({ account, onClose }: AddMailAccountModalProps) {
  const queryClient = useQueryClient();
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [testMessage, setTestMessage] = useState('');
  const [autoDetecting, setAutoDetecting] = useState(false);

  const [formData, setFormData] = useState<MailAccountCreate>({
    name: account?.name || '',
    protocol: account?.protocol || 'pop3',
    host: account?.host || '',
    port: account?.port || 995,
    username: account?.username || '',
    password: '',
    use_ssl: account?.use_ssl ?? true,
    check_interval_minutes: account?.check_interval_minutes || 5,
    max_emails_per_check: account?.max_emails_per_check || 100,
  });

  const createMutation = useMutation({
    mutationFn: (data: MailAccountCreate) =>
      account ? mailAccountsApi.update(account.id, data) : mailAccountsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mail-accounts'] });
      onClose();
    },
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : 
              type === 'number' ? Number(value) : value,
    }));
  };

  const handleAutoDetect = async () => {
    if (!formData.username) {
      alert('Please enter an email address first');
      return;
    }

    setAutoDetecting(true);
    try {
      const settings = await mailAccountsApi.autoDetect(formData.username);
      setFormData((prev) => ({
        ...prev,
        protocol: settings.protocol || prev.protocol,
        host: settings.host || prev.host,
        port: settings.port || prev.port,
        use_ssl: settings.use_ssl ?? prev.use_ssl,
      }));
      alert('Settings auto-detected successfully!');
    } catch {
      alert('Failed to auto-detect settings. Please enter manually.');
    } finally {
      setAutoDetecting(false);
    }
  };

  const handleTestConnection = async () => {
    if (!formData.username || !formData.password || !formData.host) {
      alert('Please fill in username, password, and host');
      return;
    }

    setTestStatus('testing');
    setTestMessage('');
    try {
      await mailAccountsApi.test({
        protocol: formData.protocol,
        host: formData.host,
        port: formData.port,
        username: formData.username,
        password: formData.password,
        use_ssl: formData.use_ssl,
      });
      setTestStatus('success');
      setTestMessage('Connection successful!');
    } catch (error) {
      setTestStatus('error');
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail 
        : null;
      setTestMessage(errorMessage || 'Connection failed');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createMutation.mutateAsync(formData);
    } catch (error) {
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail 
        : null;
      alert(errorMessage || 'Failed to save account');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose} />

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
          <form onSubmit={handleSubmit}>
            <div className="bg-white px-6 pt-6 pb-4">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">
                  {account ? 'Edit Mail Account' : 'Add Mail Account'}
                </h3>
                <button
                  type="button"
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-500"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>

              <div className="space-y-4">
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
                      required
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
                    required={!account}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder={account ? 'Leave blank to keep current password' : 'Password'}
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
                      <option value="imap">IMAP</option>
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
                      required
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
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

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

                <div className="grid grid-cols-2 gap-4">
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
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
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
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
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
            </div>

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
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
