'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { mailAccountsApi, MailAccount } from '@/lib/api';
import { Plus, Edit2, Trash2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { useState } from 'react';
import { AddMailAccountModal } from '@/components/AddMailAccountModal';

export default function AccountsPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<MailAccount | null>(null);
  const queryClient = useQueryClient();

  const { data: accounts, isLoading } = useQuery({
    queryKey: ['mail-accounts'],
    queryFn: mailAccountsApi.list,
  });

  const deleteMutation = useMutation({
    mutationFn: mailAccountsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mail-accounts'] });
    },
  });

  const handleEdit = (account: MailAccount) => {
    setEditingAccount(account);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this mail account?')) {
      try {
        await deleteMutation.mutateAsync(id);
      } catch {
        alert('Failed to delete account');
      }
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingAccount(null);
  };

  return (
    <AuthGuard>
      <DashboardLayout>
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">Mail Accounts</h1>
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <Plus className="h-5 w-5 mr-2" />
              Add Account
            </button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : accounts && accounts.length > 0 ? (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {accounts.map((account) => (
                <div
                  key={account.id}
                  className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden"
                >
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-900 mb-1">
                          {account.name}
                        </h3>
                        <p className="text-sm text-gray-500">{account.username}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {account.is_enabled ? (
                          <CheckCircle className="h-5 w-5 text-green-500" aria-label="Enabled" />
                        ) : (
                          <XCircle className="h-5 w-5 text-gray-400" aria-label="Disabled" />
                        )}
                      </div>
                    </div>

                    <div className="space-y-2 mb-4">
                      <div className="flex items-center text-sm">
                        <span className="text-gray-500 w-20">Protocol:</span>
                        <span className="text-gray-900 font-medium">
                          {account.protocol.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex items-center text-sm">
                        <span className="text-gray-500 w-20">Host:</span>
                        <span className="text-gray-900">{account.host}:{account.port}</span>
                      </div>
                      <div className="flex items-center text-sm">
                        <span className="text-gray-500 w-20">SSL:</span>
                        <span className="text-gray-900">
                          {account.use_ssl ? 'Yes' : 'No'}
                        </span>
                      </div>
                      <div className="flex items-center text-sm">
                        <span className="text-gray-500 w-20">Interval:</span>
                        <span className="text-gray-900">
                          Every {account.check_interval_minutes} min
                        </span>
                      </div>
                    </div>

                    {account.last_checked_at && (
                      <div className="mb-4 text-xs text-gray-500">
                        Last checked: {new Date(account.last_checked_at).toLocaleString()}
                      </div>
                    )}

                    {account.last_error && (
                      <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                        <div className="flex items-start">
                          <AlertTriangle className="h-4 w-4 text-red-500 mr-2 mt-0.5 flex-shrink-0" />
                          <p className="text-xs text-red-700">{account.last_error}</p>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-2 pt-4 border-t border-gray-200">
                      <button
                        onClick={() => handleEdit(account)}
                        className="flex-1 flex items-center justify-center px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors"
                      >
                        <Edit2 className="h-4 w-4 mr-1" />
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(account.id)}
                        disabled={deleteMutation.isPending}
                        className="flex-1 flex items-center justify-center px-3 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100 transition-colors disabled:opacity-50"
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <p className="text-gray-500 mb-4">No mail accounts configured yet</p>
              <button
                onClick={() => setIsModalOpen(true)}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                <Plus className="h-5 w-5 mr-2" />
                Add Your First Account
              </button>
            </div>
          )}
        </div>

        {isModalOpen && (
          <AddMailAccountModal
            account={editingAccount}
            onClose={handleCloseModal}
          />
        )}
      </DashboardLayout>
    </AuthGuard>
  );
}
