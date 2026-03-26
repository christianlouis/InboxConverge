'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi, AdminUser, AdminUserUpdate } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Shield, Pencil, Trash2, X, Check } from 'lucide-react';

const TIERS = ['free', 'basic', 'pro', 'enterprise'];
const STATUSES = ['active', 'canceled', 'past_due'];

function EditUserModal({
  user,
  onClose,
  onSave,
}: {
  user: AdminUser;
  onClose: () => void;
  onSave: (data: AdminUserUpdate) => void;
}) {
  const [form, setForm] = useState<AdminUserUpdate>({
    full_name: user.full_name ?? '',
    email: user.email,
    is_active: user.is_active,
    is_superuser: user.is_superuser,
    subscription_tier: user.subscription_tier,
    subscription_status: user.subscription_status,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Edit User</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Full Name</label>
            <input
              type="text"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={form.full_name ?? ''}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={form.email ?? ''}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Subscription Tier</label>
            <select
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={form.subscription_tier ?? 'free'}
              onChange={(e) => setForm({ ...form, subscription_tier: e.target.value })}
            >
              {TIERS.map((t) => (
                <option key={t} value={t}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Subscription Status</label>
            <select
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={form.subscription_status ?? 'active'}
              onChange={(e) => setForm({ ...form, subscription_status: e.target.value })}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1).replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                checked={form.is_active ?? true}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
              Active
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                checked={form.is_superuser ?? false}
                onChange={(e) => setForm({ ...form, is_superuser: e.target.checked })}
              />
              Admin (superuser)
            </label>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(form)}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminUsersPage() {
  const { user: currentUser } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  useEffect(() => {
    if (currentUser && !currentUser.is_superuser) {
      router.replace('/dashboard');
    }
  }, [currentUser, router]);

  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminApi.listUsers(),
    enabled: !!currentUser?.is_superuser,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: AdminUserUpdate }) =>
      adminApi.updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setEditingUser(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setDeleteConfirm(null);
    },
  });

  if (!currentUser?.is_superuser) return null;

  return (
    <AuthGuard>
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Shield className="h-6 w-6 text-purple-600" />
              Manage Users
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              View all registered users, assign plans, and manage admin privileges.
            </p>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      {['User', 'Plan', 'Status', 'Accounts', 'Last Login', 'Role', 'Actions'].map((h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {(users ?? []).map((u) => (
                      <tr key={u.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <div>
                            <p className="text-sm font-medium text-gray-900">{u.full_name || '—'}</p>
                            <p className="text-xs text-gray-500">{u.email}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                            {u.subscription_tier}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              u.is_active
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {u.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 text-center">
                          {u.mail_account_count}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500">
                          {u.last_login_at
                            ? new Date(u.last_login_at).toLocaleDateString()
                            : '—'}
                        </td>
                        <td className="px-4 py-3">
                          {u.is_superuser ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                              <Shield className="h-3 w-3" />
                              Admin
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">User</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setEditingUser(u)}
                              className="p-1.5 text-gray-400 hover:text-purple-600 rounded hover:bg-purple-50"
                              title="Edit user"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            {u.id !== currentUser?.id && (
                              deleteConfirm === u.id ? (
                                <div className="flex items-center gap-1">
                                  <button
                                    onClick={() => deleteMutation.mutate(u.id)}
                                    className="p-1.5 text-white bg-red-600 rounded hover:bg-red-700"
                                    title="Confirm delete"
                                  >
                                    <Check className="h-4 w-4" />
                                  </button>
                                  <button
                                    onClick={() => setDeleteConfirm(null)}
                                    className="p-1.5 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100"
                                    title="Cancel"
                                  >
                                    <X className="h-4 w-4" />
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => setDeleteConfirm(u.id)}
                                  className="p-1.5 text-gray-400 hover:text-red-600 rounded hover:bg-red-50"
                                  title="Delete user"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              )
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {(users ?? []).length === 0 && (
                  <div className="text-center py-12 text-gray-500 text-sm">No users found.</div>
                )}
              </div>
            )}
          </div>
        </div>

        {editingUser && (
          <EditUserModal
            user={editingUser}
            onClose={() => setEditingUser(null)}
            onSave={(data) => updateMutation.mutate({ id: editingUser.id, data })}
          />
        )}
      </DashboardLayout>
    </AuthGuard>
  );
}
