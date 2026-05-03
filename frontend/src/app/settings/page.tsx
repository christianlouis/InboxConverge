'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AuthGuard } from '@/components/AuthGuard';
import { DashboardLayout } from '@/components/DashboardLayout';
import { userApi, gmailApi, smtpApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import {
  CheckCircle,
  Loader2,
  User,
  Mail,
  Shield,
  Server,
  AlertTriangle,
  XCircle,
  Bug,
  RotateCcw,
  Tags,
  Send,
} from 'lucide-react';

const DEFAULT_GMAIL_IMPORT_LABEL_TEMPLATES = ['{{source_email}}', 'imported'];

function parseImportLabelTemplates(input: string): string[] {
  return input
    .split('\n')
    .map((value) => value.trim())
    .filter((value, index, values) => value.length > 0 && values.indexOf(value) === index);
}

function GmailImportLabelsForm({
  gmailCredential,
  onSave,
  isSaving,
}: {
  gmailCredential: {
    gmail_email: string;
    import_label_templates: string[];
    default_import_label_templates: string[];
  };
  onSave: (labels: string[]) => void;
  isSaving: boolean;
}) {
  const [labelsInput, setLabelsInput] = useState(
    gmailCredential.import_label_templates.join('\n')
  );

  const defaultTemplates =
    gmailCredential.default_import_label_templates.length > 0
      ? gmailCredential.default_import_label_templates
      : DEFAULT_GMAIL_IMPORT_LABEL_TEMPLATES;
  const parsedLabels = parseImportLabelTemplates(labelsInput);
  const isDefaultSelection =
    parsedLabels.length === defaultTemplates.length &&
    parsedLabels.every((value, index) => value === defaultTemplates[index]);

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Tags className="h-4 w-4 text-gray-500" />
        <h3 className="text-sm font-semibold text-gray-900">Import labels</h3>
      </div>
      <p className="text-sm text-gray-600">
        One label is created per line. We recommend keeping{' '}
        <code className="rounded bg-white px-1 py-0.5 text-xs text-gray-700">
          {'{{source_email}}'}
        </code>{' '}
        so each imported message is tagged with the mailbox it came from, plus a
        catch-all label like <strong>imported</strong>.
      </p>
      <p className="mt-2 text-xs text-gray-500">
        Example: a mail pulled from <strong>billing@example.com</strong> will be
        labeled as <strong>billing@example.com</strong> when{' '}
        <code className="rounded bg-white px-1 py-0.5 text-xs text-gray-700">
          {'{{source_email}}'}
        </code>{' '}
        is present.
      </p>
      <textarea
        value={labelsInput}
        onChange={(e) => setLabelsInput(e.target.value)}
        rows={4}
        className="mt-4 w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
        placeholder={`{{source_email}}\nimported`}
      />
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-500">
        <span>Suggested defaults:</span>
        {defaultTemplates.map((label) => (
          <span
            key={label}
            className="rounded-full border border-gray-200 bg-white px-2 py-1 text-gray-700"
          >
            {label}
          </span>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => onSave(parsedLabels)}
          disabled={isSaving}
          className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
        >
          {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Save label setup
        </button>
        <button
          type="button"
          onClick={() => setLabelsInput(defaultTemplates.join('\n'))}
          disabled={isSaving || isDefaultSelection}
          className="flex items-center gap-2 rounded-md bg-white px-4 py-2 text-sm text-gray-700 ring-1 ring-gray-300 transition-colors hover:bg-gray-50 disabled:opacity-50"
        >
          <RotateCcw className="h-4 w-4" />
          Reset defaults
        </button>
      </div>
      <p className="mt-3 text-xs text-gray-500">
        Connected Gmail target: <strong>{gmailCredential.gmail_email}</strong>
      </p>
    </div>
  );
}

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

  // SMTP form state
  const [smtpForm, setSmtpForm] = useState({
    host: 'smtp.gmail.com',
    port: 587,
    username: '',
    sender_email: '',
    password: '',
    use_tls: true,
  });
  const [smtpSaved, setSmtpSaved] = useState(false);

  // Refresh user data from the server
  const { data: currentUser } = useQuery({
    queryKey: ['current-user'],
    queryFn: userApi.getCurrentUser,
    initialData: user ?? undefined,
  });

  // Gmail credential status
  const {
    data: gmailCredential,
    isLoading: gmailLoading,
    error: gmailError,
  } = useQuery({
    queryKey: ['gmail-credential'],
    queryFn: gmailApi.getCredential,
    retry: false,
  });

  // SMTP config
  const { data: smtpConfig, isLoading: smtpLoading } = useQuery({
    queryKey: ['smtp-config'],
    queryFn: smtpApi.get,
    retry: false,
  });

  // Pre-populate SMTP form when data loads
  const [smtpFormPopulated, setSmtpFormPopulated] = useState(false);
  if (smtpConfig && !smtpFormPopulated) {
    setSmtpFormPopulated(true);
    setSmtpForm((prev) => ({
      ...prev,
      host: smtpConfig.host,
      port: smtpConfig.port,
      username: smtpConfig.username,
      sender_email: smtpConfig.sender_email,
      use_tls: smtpConfig.use_tls,
      password: '', // never pre-fill password
    }));
  }

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

  const disconnectGmailMutation = useMutation({
    mutationFn: gmailApi.disconnect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gmail-credential'] });
    },
  });

  const [debugEmailResult, setDebugEmailResult] = useState<string | null>(null);
  const [gmailLabelsSaved, setGmailLabelsSaved] = useState(false);
  const sendDebugEmailMutation = useMutation({
    mutationFn: gmailApi.sendDebugEmail,
    onSuccess: () => {
      setDebugEmailResult('success');
      setTimeout(() => setDebugEmailResult(null), 5000);
    },
    onError: () => {
      setDebugEmailResult('error');
      setTimeout(() => setDebugEmailResult(null), 5000);
    },
  });

  const updateGmailLabelsMutation = useMutation({
    mutationFn: gmailApi.updateImportLabels,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gmail-credential'] });
      setGmailLabelsSaved(true);
      setTimeout(() => setGmailLabelsSaved(false), 3000);
    },
  });

  const saveSmtpMutation = useMutation({
    mutationFn: smtpApi.save,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['smtp-config'] });
      setSmtpSaved(true);
      setTimeout(() => setSmtpSaved(false), 3000);
    },
  });

  const deleteSmtpMutation = useMutation({
    mutationFn: smtpApi.remove,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['smtp-config'] });
      setSmtpForm({ host: 'smtp.gmail.com', port: 587, username: '', sender_email: '', password: '', use_tls: true });
    },
  });

  const [smtpTestResult, setSmtpTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const testSmtpMutation = useMutation({
    mutationFn: smtpApi.test,
    onSuccess: (result) => {
      setSmtpTestResult(result);
      setTimeout(() => setSmtpTestResult(null), 6000);
    },
    onError: () => {
      setSmtpTestResult({ success: false, message: 'Request failed. Check your network connection.' });
      setTimeout(() => setSmtpTestResult(null), 6000);
    },
  });

  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setProfileForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSmtpChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setSmtpForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked
              : name === 'port' ? Number(value)
              : value,
    }));
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

  const handleSmtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await saveSmtpMutation.mutateAsync({
        host: smtpForm.host,
        port: smtpForm.port,
        username: smtpForm.username,
        sender_email: smtpForm.sender_email,
        password: smtpForm.password || undefined,
        use_tls: smtpForm.use_tls,
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      alert(errorMessage || 'Failed to save SMTP settings');
    }
  };

  const handleConnectGmail = async () => {
    try {
      const redirectUri = `${window.location.origin}/auth/callback`;
      const url = await gmailApi.getAuthorizeUrl(redirectUri);
      window.location.href = url;
    } catch (error) {
      const errorMessage =
        error instanceof Error && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      alert(errorMessage || 'Failed to start Gmail authorization');
    }
  };

  const handleDisconnectGmail = async () => {
    if (confirm('Disconnect Gmail? Mail accounts using Gmail API delivery will fall back to SMTP.')) {
      try {
        await disconnectGmailMutation.mutateAsync();
      } catch {
        alert('Failed to disconnect Gmail');
      }
    }
  };

  const displayUser = currentUser ?? user;
  const gmailConnected = gmailCredential?.is_valid === true;
  // gmail 404 just means "not connected yet" — not a real error
  const gmailNotConnected = !gmailCredential && !gmailLoading;

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

      {/* Gmail API Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <Mail className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900">Gmail API Delivery</h2>
        </div>
        <div className="px-6 py-6">
          <p className="text-sm text-gray-600 mb-4">
            Grant this app permission to inject emails directly into your Gmail inbox.
            This is the preferred delivery method — emails arrive with original headers
            intact, bypassing SMTP entirely.
          </p>
          <p className="text-xs text-gray-500 mb-6">
            <strong>Token lifetime:</strong> Access tokens expire after 1 hour and are
            refreshed automatically. Refresh tokens do not expire unless you revoke
            access via your{' '}
            <a
              href="https://myaccount.google.com/permissions"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 underline"
            >
              Google Account permissions
            </a>
            . If revoked, click &ldquo;Connect Gmail&rdquo; again to re-authorise.
          </p>

          {gmailLoading && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Checking Gmail connection…
            </div>
          )}

          {!gmailLoading && gmailConnected && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      Connected as <span className="font-semibold">{gmailCredential.gmail_email}</span>
                    </p>
                    {gmailCredential.last_verified_at && (
                      <p className="text-xs text-gray-500">
                        Last verified: {new Date(gmailCredential.last_verified_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() => sendDebugEmailMutation.mutate()}
                    disabled={sendDebugEmailMutation.isPending}
                    title="Inject a test email into your Gmail inbox"
                    className="flex items-center gap-1.5 px-4 py-2 text-sm bg-amber-50 text-amber-700 rounded-md hover:bg-amber-100 transition-colors disabled:opacity-50"
                  >
                    {sendDebugEmailMutation.isPending ? (
                      <><Loader2 className="h-4 w-4 animate-spin" />Sending…</>
                    ) : (
                      <><Bug className="h-4 w-4" />Send Debug Email</>
                    )}
                  </button>
                  <button
                    onClick={handleConnectGmail}
                    className="px-4 py-2 text-sm bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors"
                  >
                    Re-authorise
                  </button>
                  <button
                    onClick={handleDisconnectGmail}
                    disabled={disconnectGmailMutation.isPending}
                    className="px-4 py-2 text-sm bg-red-50 text-red-700 rounded-md hover:bg-red-100 transition-colors disabled:opacity-50"
                  >
                    Disconnect
                  </button>
                </div>
              </div>
              {debugEmailResult === 'success' && (
                <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
                  <CheckCircle className="h-4 w-4 flex-shrink-0" />
                  Debug email injected successfully. Check your Gmail inbox for the
                  configured import labels plus a <strong className="mx-1">test</strong>{' '}
                  label.
                </div>
              )}
              {debugEmailResult === 'error' && (
                <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                  Failed to inject debug email. Check that Gmail API access is still valid.
                </div>
              )}
              <GmailImportLabelsForm
                key={gmailCredential.updated_at}
                gmailCredential={gmailCredential}
                isSaving={updateGmailLabelsMutation.isPending}
                onSave={(labels) => updateGmailLabelsMutation.mutate(labels)}
              />
              {gmailLabelsSaved && (
                <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
                  <CheckCircle className="h-4 w-4 flex-shrink-0" />
                  Gmail import labels saved.
                </div>
              )}
            </div>
          )}

          {!gmailLoading && gmailCredential && !gmailCredential.is_valid && (
            <div className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-md mb-4">
              <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-red-700">
                <strong>Gmail access was revoked.</strong> Click &ldquo;Re-authorise&rdquo; below to restore Gmail API delivery.
              </div>
            </div>
          )}

          {!gmailLoading && (gmailNotConnected || (gmailCredential && !gmailCredential.is_valid)) && (
            <button
              onClick={handleConnectGmail}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <Mail className="h-4 w-4" />
              {gmailError ? 'Connect Gmail' : 'Re-authorise Gmail'}
            </button>
          )}

          {!gmailLoading && gmailNotConnected && (
            <div className="mt-3 flex items-center gap-2 text-sm text-gray-500">
              <XCircle className="h-4 w-4 text-gray-400" />
              No Gmail account connected yet.
            </div>
          )}
        </div>
      </div>

      {/* SMTP Fallback Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <Server className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900">SMTP Fallback</h2>
        </div>
        <div className="px-6 py-6">
          <p className="text-sm text-gray-600 mb-6">
            Used when Gmail API is not connected or when a mail account is configured
            to use SMTP delivery. Your credentials are stored encrypted.
          </p>

          {smtpLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading SMTP settings…
            </div>
          ) : (
            <form onSubmit={handleSmtpSubmit} className="space-y-4 max-w-lg">
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">SMTP Host</label>
                  <input
                    type="text"
                    name="host"
                    value={smtpForm.host}
                    onChange={handleSmtpChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="smtp.gmail.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                  <input
                    type="number"
                    name="port"
                    value={smtpForm.port}
                    onChange={handleSmtpChange}
                    min={1}
                    max={65535}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input
                  type="text"
                  name="username"
                  value={smtpForm.username}
                  onChange={handleSmtpChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sender Email</label>
                <input
                  type="email"
                  name="sender_email"
                  value={smtpForm.sender_email}
                  onChange={handleSmtpChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="sender@example.com"
                />
                <p className="mt-1 text-xs text-gray-500">
                  The From: address used when forwarding mail. Required when your SMTP username is an API token rather than an email address (e.g. Postmark, SendGrid).
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  name="password"
                  value={smtpForm.password}
                  onChange={handleSmtpChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={smtpConfig?.has_password ? '••••••••  (leave blank to keep current)' : 'App password or SMTP password'}
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="smtp_use_tls"
                  name="use_tls"
                  checked={smtpForm.use_tls}
                  onChange={handleSmtpChange}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                />
                <label htmlFor="smtp_use_tls" className="text-sm text-gray-700">
                  Use STARTTLS (recommended for port 587)
                </label>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saveSmtpMutation.isPending}
                  className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {saveSmtpMutation.isPending ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Saving…</>
                  ) : (
                    'Save SMTP Settings'
                  )}
                </button>
                {smtpConfig && (
                  <button
                    type="button"
                    onClick={() => testSmtpMutation.mutate()}
                    disabled={testSmtpMutation.isPending}
                    title="Send a test email to your account address using these SMTP settings"
                    className="flex items-center gap-1.5 px-4 py-2 text-sm bg-amber-50 text-amber-700 rounded-md hover:bg-amber-100 disabled:opacity-50 transition-colors"
                  >
                    {testSmtpMutation.isPending ? (
                      <><Loader2 className="h-4 w-4 animate-spin" />Sending…</>
                    ) : (
                      <><Send className="h-4 w-4" />Send Test Email</>
                    )}
                  </button>
                )}
                {smtpConfig && (
                  <button
                    type="button"
                    onClick={() => deleteSmtpMutation.mutate()}
                    disabled={deleteSmtpMutation.isPending}
                    className="px-4 py-2 text-sm text-red-600 bg-red-50 rounded-md hover:bg-red-100 disabled:opacity-50 transition-colors"
                  >
                    Remove
                  </button>
                )}
                {smtpSaved && (
                  <span className="flex items-center text-sm text-green-600">
                    <CheckCircle className="h-4 w-4 mr-1" />
                    Saved
                  </span>
                )}
              </div>
              {smtpTestResult !== null && (
                <div
                  className={`flex items-center gap-2 text-sm rounded-md px-3 py-2 border ${
                    smtpTestResult.success
                      ? 'text-green-700 bg-green-50 border-green-200'
                      : 'text-red-700 bg-red-50 border-red-200'
                  }`}
                >
                  {smtpTestResult.success ? (
                    <CheckCircle className="h-4 w-4 flex-shrink-0" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                  )}
                  {smtpTestResult.message}
                </div>
              )}
            </form>
          )}
        </div>
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
