'use client';

import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { userApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { CheckCircle, Loader2, User, Mail, Shield } from 'lucide-react';

export default function SettingsPage() {
  return (
    <AuthGuard>
      <DashboardLayout>
        <SettingsContent />
      </DashboardLayout>
    </AuthGuard>
  );
}

function SettingsContent() {
  const queryClient = useQueryClient();
  const { user, setUser } = useAuthStore();

  const [profileForm, setProfileForm] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
  });
  const [profileSaved, setProfileSaved] = useState(false);

  // Refresh user data from the server
  const { data: currentUser } = useQuery({
    queryKey: ['current-user'],
    queryFn: userApi.getCurrentUser,
    initialData: user ?? undefined,
  });

  // Sync form when server data arrives
  useEffect(() => {
    if (currentUser) {
      setProfileForm({
        full_name: currentUser.full_name || '',
        email: currentUser.email || '',
      });
    }
  }, [currentUser]);

  const updateProfileMutation = useMutation({
    mutationFn: (data: { full_name: string; email: string }) =>
      userApi.updateProfile(data),
    onSuccess: (updatedUser) => {
      setUser(updatedUser);
      queryClient.invalidateQueries({ queryKey: ['current-user'] });
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    },
  });

  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setProfileForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateProfileMutation.mutateAsync({
        full_name: profileForm.full_name,
        email: profileForm.email,
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      alert(errorMessage || 'Failed to update profile');
    }
  };

  const displayUser = currentUser ?? user;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Profile Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <User className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900">Profile</h2>
        </div>
        <form onSubmit={handleProfileSubmit} className="px-6 py-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Full Name
            </label>
            <input
              type="text"
              name="full_name"
              value={profileForm.full_name}
              onChange={handleProfileChange}
              className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Your full name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email Address
            </label>
            <input
              type="email"
              name="email"
              value={profileForm.email}
              onChange={handleProfileChange}
              className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="you@example.com"
            />
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={updateProfileMutation.isPending}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {updateProfileMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving…
                </>
              ) : (
                'Save Changes'
              )}
            </button>
            {profileSaved && (
              <span className="flex items-center text-sm text-green-600">
                <CheckCircle className="h-4 w-4 mr-1" />
                Saved successfully
              </span>
            )}
          </div>
        </form>
      </div>

      {/* Account Information */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <Mail className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900">Account Information</h2>
        </div>
        <div className="px-6 py-6 space-y-3">
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-40">Subscription tier:</span>
            <span className="font-medium text-gray-900 capitalize">
              {displayUser?.subscription_tier ?? '—'}
            </span>
          </div>
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-40">Subscription status:</span>
            <span className="font-medium text-gray-900 capitalize">
              {displayUser?.subscription_status ?? '—'}
            </span>
          </div>
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-40">Member since:</span>
            <span className="text-gray-900">
              {displayUser?.created_at
                ? new Date(displayUser.created_at).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })
                : '—'}
            </span>
          </div>
          {displayUser?.oauth_provider && (
            <div className="flex items-center text-sm">
              <span className="text-gray-500 w-40">Linked account:</span>
              <span className="font-medium text-gray-900 capitalize">
                {displayUser.oauth_provider}
              </span>
            </div>
          )}
          {displayUser?.last_login_at && (
            <div className="flex items-center text-sm">
              <span className="text-gray-500 w-40">Last login:</span>
              <span className="text-gray-900">
                {new Date(displayUser.last_login_at).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Security Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <Shield className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900">Security</h2>
        </div>
        <div className="px-6 py-6">
          <p className="text-sm text-gray-600">
            Password change and two-factor authentication settings are coming soon.
          </p>
          {displayUser?.oauth_provider === 'google' && (
            <p className="mt-2 text-sm text-gray-500">
              Your account is authenticated via Google OAuth — password management is handled by Google.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
