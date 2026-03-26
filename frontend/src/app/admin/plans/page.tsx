'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  adminApi,
  SubscriptionPlan,
  SubscriptionPlanCreate,
  SubscriptionPlanUpdate,
} from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Shield, Plus, Pencil, Trash2, X, Check } from 'lucide-react';

const TIERS = ['free', 'basic', 'pro', 'enterprise'];

const DEFAULT_FORM: SubscriptionPlanCreate = {
  tier: 'free',
  name: '',
  description: '',
  price_monthly: 0,
  price_yearly: undefined,
  max_mail_accounts: 1,
  max_emails_per_day: 1000,
  check_interval_minutes: 5,
  support_level: 'community',
  is_active: true,
};

function PlanFormModal({
  plan,
  onClose,
  onCreate,
  onUpdate,
}: {
  plan: SubscriptionPlan | null;
  onClose: () => void;
  onCreate?: (data: SubscriptionPlanCreate) => void;
  onUpdate?: (data: SubscriptionPlanUpdate) => void;
}) {
  const isEdit = plan !== null;
  const [form, setForm] = useState<SubscriptionPlanCreate>(
    plan
      ? {
          tier: plan.tier,
          name: plan.name,
          description: plan.description ?? '',
          price_monthly: plan.price_monthly,
          price_yearly: plan.price_yearly ?? undefined,
          max_mail_accounts: plan.max_mail_accounts,
          max_emails_per_day: plan.max_emails_per_day,
          check_interval_minutes: plan.check_interval_minutes,
          support_level: plan.support_level,
          is_active: plan.is_active,
        }
      : DEFAULT_FORM
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6 overflow-y-auto max-h-[90vh]">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEdit ? 'Edit Plan' : 'Create Plan'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-4">
          {!isEdit && (
            <div>
              <label className="block text-sm font-medium text-gray-700">Tier</label>
              <select
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                value={form.tier}
                onChange={(e) => setForm({ ...form, tier: e.target.value })}
              >
                {TIERS.map((t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700">Name</label>
            <input
              type="text"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea
              rows={2}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={form.description ?? ''}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Monthly Price ($)</label>
              <input
                type="number"
                min={0}
                step={0.01}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                value={form.price_monthly}
                onChange={(e) => setForm({ ...form, price_monthly: parseFloat(e.target.value) || 0 })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Yearly Price ($)</label>
              <input
                type="number"
                min={0}
                step={0.01}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                value={form.price_yearly ?? ''}
                onChange={(e) =>
                  setForm({
                    ...form,
                    price_yearly: e.target.value ? parseFloat(e.target.value) : undefined,
                  })
                }
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Max Mailboxes</label>
              <input
                type="number"
                min={1}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                value={form.max_mail_accounts}
                onChange={(e) =>
                  setForm({ ...form, max_mail_accounts: parseInt(e.target.value) || 1 })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Max Emails/Day</label>
              <input
                type="number"
                min={1}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                value={form.max_emails_per_day}
                onChange={(e) =>
                  setForm({ ...form, max_emails_per_day: parseInt(e.target.value) || 1 })
                }
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Check Interval (min)</label>
              <input
                type="number"
                min={1}
                max={1440}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                value={form.check_interval_minutes}
                onChange={(e) =>
                  setForm({ ...form, check_interval_minutes: parseInt(e.target.value) || 5 })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Support Level</label>
              <select
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                value={form.support_level}
                onChange={(e) => setForm({ ...form, support_level: e.target.value })}
              >
                {['community', 'email', 'priority'].map((s) => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
            <input
              type="checkbox"
              className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Active (visible to users)
          </label>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (isEdit && onUpdate) {
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const { tier: _tier, ...updateFields } = form;
                onUpdate(updateFields);
              } else if (!isEdit && onCreate) {
                onCreate(form);
              }
            }}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700"
          >
            {isEdit ? 'Save Changes' : 'Create Plan'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminPlansPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editingPlan, setEditingPlan] = useState<SubscriptionPlan | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  useEffect(() => {
    if (user && !user.is_superuser) {
      router.replace('/dashboard');
    }
  }, [user, router]);

  const { data: plans, isLoading } = useQuery({
    queryKey: ['admin-plans'],
    queryFn: adminApi.listPlans,
    enabled: !!user?.is_superuser,
  });

  const createMutation = useMutation({
    mutationFn: (data: SubscriptionPlanCreate) => adminApi.createPlan(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-plans'] });
      setShowCreate(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: SubscriptionPlanUpdate }) =>
      adminApi.updatePlan(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-plans'] });
      setEditingPlan(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deletePlan(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-plans'] });
      setDeleteConfirm(null);
    },
  });

  // AuthGuard must always render (see admin/page.tsx for explanation).
  return (
    <AuthGuard>
      <DashboardLayout>
        {!user?.is_superuser ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
          </div>
        ) : (
          <>
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <Shield className="h-6 w-6 text-purple-600" />
                    Manage Plans
                  </h1>
                  <p className="mt-1 text-sm text-gray-500">
                    Configure subscription plans, limits, and pricing.
                  </p>
                </div>
                <button
                  onClick={() => setShowCreate(true)}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700"
                >
                  <Plus className="h-4 w-4" />
                  New Plan
                </button>
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
                          {['Tier', 'Name', 'Price/mo', 'Mailboxes', 'Emails/day', 'Interval', 'Support', 'Status', 'Actions'].map((h) => (
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
                        {(plans ?? []).map((p) => (
                          <tr key={p.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                                {p.tier}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm font-medium text-gray-900">{p.name}</td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              ${p.price_monthly.toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500 text-center">
                              {p.max_mail_accounts}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500 text-center">
                              {p.max_emails_per_day.toLocaleString()}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500 text-center">
                              {p.check_interval_minutes}m
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500 capitalize">
                              {p.support_level}
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                  p.is_active
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-gray-100 text-gray-500'
                                }`}
                              >
                                {p.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => setEditingPlan(p)}
                                  className="p-1.5 text-gray-400 hover:text-purple-600 rounded hover:bg-purple-50"
                                  title="Edit plan"
                                >
                                  <Pencil className="h-4 w-4" />
                                </button>
                                {deleteConfirm === p.id ? (
                                  <div className="flex items-center gap-1">
                                    <button
                                      onClick={() => deleteMutation.mutate(p.id)}
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
                                    onClick={() => setDeleteConfirm(p.id)}
                                    className="p-1.5 text-gray-400 hover:text-red-600 rounded hover:bg-red-50"
                                    title="Delete plan"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {(plans ?? []).length === 0 && (
                      <div className="text-center py-12 text-gray-500 text-sm">
                        No plans found. Create one to get started.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {showCreate && (
              <PlanFormModal
                plan={null}
                onClose={() => setShowCreate(false)}
                onCreate={(data) => createMutation.mutate(data)}
              />
            )}
            {editingPlan && (
              <PlanFormModal
                plan={editingPlan}
                onClose={() => setEditingPlan(null)}
                onUpdate={(data) =>
                  updateMutation.mutate({ id: editingPlan.id, data })
                }
              />
            )}
          </>
        )}
      </DashboardLayout>
    </AuthGuard>
  );
}
