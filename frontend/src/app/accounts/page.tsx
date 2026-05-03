'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { mailAccountsApi, MailAccount } from '@/lib/api';
import { Plus, Edit2, Trash2, CheckCircle, XCircle, AlertTriangle, Power, RefreshCw, RotateCcw } from 'lucide-react';
import { useState } from 'react';
import Image from 'next/image';
import { AddMailAccountModal } from '@/components/AddMailAccountModal';

// Map provider_name (from backend) to the SVG icon filename in /public/providers/
const PROVIDER_ICON_MAP: Record<string, string> = {
  'Gmail': 'gmail',
  'GMX': 'gmx',
  'WEB.DE': 'webde',
  'Outlook / Hotmail': 'outlook',
  'Yahoo Mail': 'yahoo',
  'AOL Mail': 'aol',
  'T-Online': 'tonline',
  '1&1 / IONOS': 'ionos',
  'Freenet': 'freenet',
  'Posteo': 'posteo',
  'mail.de': 'mailde',
  'iCloud Mail': 'icloud',
  'Proton Mail': 'protonmail',
};

// Fallback: map email domains to SVG icon filenames for accounts without a provider_name
const DOMAIN_ICON_MAP: Record<string, string> = {
  // Gmail
  'gmail.com': 'gmail', 'googlemail.com': 'gmail',
  // GMX
  'gmx.de': 'gmx', 'gmx.net': 'gmx', 'gmx.at': 'gmx', 'gmx.ch': 'gmx', 'gmx.com': 'gmx',
  // WEB.DE
  'web.de': 'webde',
  // Outlook / Hotmail
  'outlook.com': 'outlook', 'hotmail.com': 'outlook', 'live.com': 'outlook',
  'msn.com': 'outlook', 'outlook.de': 'outlook',
  // Yahoo Mail
  'yahoo.com': 'yahoo', 'yahoo.de': 'yahoo', 'yahoo.co.uk': 'yahoo', 'ymail.com': 'yahoo',
  // AOL Mail
  'aol.com': 'aol', 'aim.com': 'aol',
  // T-Online
  't-online.de': 'tonline',
  // 1&1 / IONOS
  'online.de': 'ionos', 'onlinehome.de': 'ionos', '1und1.de': 'ionos',
  // Freenet
  'freenet.de': 'freenet',
  // iCloud Mail
  'icloud.com': 'icloud', 'me.com': 'icloud', 'mac.com': 'icloud',
  // Posteo
  'posteo.de': 'posteo', 'posteo.net': 'posteo',
  // Proton Mail
  'proton.me': 'protonmail', 'protonmail.com': 'protonmail',
  'protonmail.ch': 'protonmail', 'pm.me': 'protonmail',
};

/**
 * Full-width logo banner rendered at the top of a card.
 * Uses next/image fill + object-contain so every logo – regardless of its
 * native aspect ratio (1:1 square up to ~6:1 wordmark) – fits correctly
 * inside the fixed-height strip without distortion.
 *
 * Resolves the icon by first checking provider_name, then falling back to
 * the email domain so that accounts created without a provider_name still
 * show the correct logo.
 */
function ProviderLogoBanner({ providerName, email }: { providerName?: string | null; email?: string | null }) {
  let icon = providerName ? PROVIDER_ICON_MAP[providerName] : undefined;
  if (!icon && email) {
    const atIndex = email.lastIndexOf('@');
    const domain = atIndex !== -1 ? email.slice(atIndex + 1).toLowerCase() : undefined;
    if (domain) icon = DOMAIN_ICON_MAP[domain];
  }
  if (!icon) return null;
  const label = providerName ?? email?.split('@')[1] ?? 'provider';
  return (
    <div className="relative h-16 w-full bg-gray-50 border-b border-gray-100 overflow-hidden">
      <Image
        src={`/providers/${icon}.svg`}
        alt={`${label} logo`}
        fill
        unoptimized
        sizes="(max-width: 768px) 100vw, 33vw"
        style={{ objectFit: 'contain', padding: '12px' }}
      />
    </div>
  );
}

export default function AccountsPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<MailAccount | null>(null);
  const [pullingIds, setPullingIds] = useState<Set<number>>(new Set());
  const [successIds, setSuccessIds] = useState<Set<number>>(new Set());
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

  const toggleMutation = useMutation({
    mutationFn: mailAccountsApi.toggle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mail-accounts'] });
    },
  });

  const clearErrorMutation = useMutation({
    mutationFn: mailAccountsApi.clearError,
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

  const handleToggle = async (id: number) => {
    try {
      await toggleMutation.mutateAsync(id);
    } catch {
      alert('Failed to update account');
    }
  };

  const handlePullNow = async (id: number) => {
    setPullingIds((prev) => new Set(prev).add(id));
    try {
      await mailAccountsApi.pullNow(id);
      setSuccessIds((prev) => new Set(prev).add(id));
      setTimeout(() => {
        setSuccessIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      }, 2000);
    } catch {
      alert('Failed to queue pull');
    } finally {
      setPullingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
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
                  className={`bg-white rounded-lg shadow-md border overflow-hidden transition-opacity ${
                    account.is_enabled ? 'border-gray-200' : 'border-gray-200 opacity-60'
                  }`}
                >
                  {/* Provider logo banner – full-width strip that accommodates any aspect ratio */}
                  <ProviderLogoBanner providerName={account.provider_name} email={account.email_address} />

                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="min-w-0 flex-1">
                        <h3 className="text-lg font-semibold text-gray-900 mb-1 truncate">
                          {account.name}
                        </h3>
                        <p className="text-sm text-gray-500 truncate">{account.email_address}</p>
                      </div>
                      <div className="flex items-center gap-2 ml-2 flex-shrink-0">
                        {account.is_enabled ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                            <CheckCircle className="h-3 w-3" />
                            Enabled
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                            <XCircle className="h-3 w-3" />
                            Disabled
                          </span>
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

                    {account.last_check_at && (
                      <div className="mb-4 text-xs text-gray-500">
                        Last checked: {new Date(account.last_check_at).toLocaleString()}
                      </div>
                    )}

                    {account.last_error_message && (
                      <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-start min-w-0">
                            <AlertTriangle className="h-4 w-4 text-red-500 mr-2 mt-0.5 flex-shrink-0" />
                            <p className="text-xs text-red-700">{account.last_error_message}</p>
                          </div>
                          <button
                            onClick={() => clearErrorMutation.mutate(account.id)}
                            disabled={clearErrorMutation.isPending}
                            title="Clear error status"
                            className="flex-shrink-0 flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-600 bg-red-100 hover:bg-red-200 rounded transition-colors disabled:opacity-50"
                          >
                            <RotateCcw className="h-3 w-3" />
                            Clear
                          </button>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-2 pt-4 border-t border-gray-200">
                      <button
                        onClick={() => handleToggle(account.id)}
                        disabled={toggleMutation.isPending}
                        title={account.is_enabled ? 'Disable account' : 'Enable account'}
                        className={`flex items-center justify-center px-3 py-2 text-sm font-medium rounded-md transition-colors disabled:opacity-50 ${
                          account.is_enabled
                            ? 'text-yellow-600 bg-yellow-50 hover:bg-yellow-100'
                            : 'text-green-600 bg-green-50 hover:bg-green-100'
                        }`}
                      >
                        <Power className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handlePullNow(account.id)}
                        disabled={!account.is_enabled || pullingIds.has(account.id)}
                        title="Fetch new emails from this account now"
                        aria-label="Fetch emails now"
                        className={`flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md transition-colors disabled:opacity-50 ${
                          successIds.has(account.id)
                            ? 'text-green-600 bg-green-50 hover:bg-green-100'
                            : 'text-indigo-600 bg-indigo-50 hover:bg-indigo-100'
                        }`}
                      >
                        <RefreshCw className={`h-4 w-4 ${pullingIds.has(account.id) ? 'animate-spin' : ''}`} />
                        <span>
                          {pullingIds.has(account.id)
                            ? 'Fetching…'
                            : successIds.has(account.id)
                            ? 'Queued!'
                            : 'Fetch'}
                        </span>
                      </button>
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
