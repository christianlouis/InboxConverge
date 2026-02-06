'use client';

import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';

export default function SettingsPage() {
  return (
    <AuthGuard>
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-600">Settings page coming soon...</p>
          </div>
        </div>
      </DashboardLayout>
    </AuthGuard>
  );
}
