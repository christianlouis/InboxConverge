'use client';

import { useState } from 'react';
import { ArrowLeft, Bell, Check, Eye, EyeOff, Send } from 'lucide-react';

interface NotificationWizardProps {
  onComplete: (config: {
    name: string;
    channel: string;
    apprise_url: string;
    notify_on_errors: boolean;
    notify_on_success: boolean;
  }) => void;
  onCancel: () => void;
  initialData?: {
    name: string;
    channel: string;
    apprise_url: string | null;
    notify_on_errors: boolean;
    notify_on_success: boolean;
  } | null;
}

const CHANNEL_OPTIONS = [
  { id: 'telegram', icon: '🤖', label: 'Telegram', description: 'Instant messages via Telegram bot' },
  { id: 'discord', icon: '💬', label: 'Discord', description: 'Server notifications via Discord webhook' },
  { id: 'slack', icon: '💼', label: 'Slack', description: 'Team alerts via Slack webhook' },
  { id: 'email', icon: '📧', label: 'Email', description: 'Email notifications via SMTP' },
  { id: 'webhook', icon: '🔗', label: 'Webhook', description: 'POST to any HTTP endpoint' },
  { id: 'custom', icon: '⚙️', label: 'Custom Apprise URL', description: 'Advanced: any supported Apprise format' },
];

interface ChannelField {
  key: string;
  label: string;
  placeholder: string;
  type?: 'text' | 'password';
  hint?: string;
  optional?: boolean;
}

const CHANNEL_FIELDS: Record<string, ChannelField[]> = {
  telegram: [
    {
      key: 'bot_token',
      label: 'Bot Token',
      placeholder: '110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw',
      hint: 'Get from @BotFather on Telegram',
    },
    {
      key: 'chat_id',
      label: 'Chat ID',
      placeholder: '12345678',
      hint: 'Your Telegram chat or group ID',
    },
  ],
  discord: [
    {
      key: 'webhook_url',
      label: 'Discord Webhook URL',
      placeholder: 'https://discord.com/api/webhooks/123456789/abcdef...',
      hint: 'Paste the full webhook URL from Discord server settings → Integrations',
    },
  ],
  slack: [
    {
      key: 'webhook_url',
      label: 'Slack Webhook URL',
      placeholder: 'https://hooks.slack.com/services/T00000000/B00000000/XXXX...',
      hint: 'Create an Incoming Webhook in your Slack app settings',
    },
  ],
  email: [
    { key: 'username', label: 'Username / Email', placeholder: 'user@example.com' },
    { key: 'password', label: 'SMTP Password', placeholder: '••••••••', type: 'password' },
    { key: 'host', label: 'SMTP Host', placeholder: 'smtp.example.com' },
    { key: 'port', label: 'SMTP Port', placeholder: '587', optional: true },
  ],
  webhook: [
    {
      key: 'url',
      label: 'Webhook URL',
      placeholder: 'https://hooks.example.com/...',
      hint: 'Full HTTP(S) URL — receives a JSON POST with notification data',
    },
  ],
  custom: [
    {
      key: 'apprise_url',
      label: 'Apprise URL',
      placeholder: 'tgram://bot_token/chat_id/',
      hint: 'Any valid Apprise notification URL — see apprise.readthedocs.io',
    },
  ],
};

function buildAppriseUrl(channel: string, fields: Record<string, string>): string {
  switch (channel) {
    case 'telegram':
      if (!fields.bot_token || !fields.chat_id) return '';
      return `tgram://${fields.bot_token}/${fields.chat_id}/`;
    case 'discord': {
      const match = (fields.webhook_url ?? '').match(
        /discord\.com\/api\/webhooks\/(\d+)\/([^/?]+)/
      );
      if (match) return `discord://${match[1]}/${match[2]}/`;
      return '';
    }
    case 'slack': {
      const match = (fields.webhook_url ?? '').match(
        /hooks\.slack\.com\/services\/([^/]+)\/([^/]+)\/([^/?]+)/
      );
      if (match) return `slack://${match[1]}/${match[2]}/${match[3]}/`;
      return '';
    }
    case 'email':
      if (!fields.username || !fields.password || !fields.host) return '';
      return `mailtos://${encodeURIComponent(fields.username)}:${encodeURIComponent(fields.password)}@${fields.host}${
        fields.port ? `:${fields.port}` : ''
      }`;
    case 'webhook':
      return fields.url || '';
    case 'custom':
      return fields.apprise_url || '';
    default:
      return '';
  }
}

export function NotificationWizard({ onComplete, onCancel, initialData }: NotificationWizardProps) {
  const [step, setStep] = useState<1 | 2 | 3>(initialData ? 3 : 1);
  const [selectedChannel, setSelectedChannel] = useState<string>(initialData?.channel ?? '');
  const [fields, setFields] = useState<Record<string, string>>({});
  const [name, setName] = useState(initialData?.name ?? '');
  const [notifyOnErrors, setNotifyOnErrors] = useState(initialData?.notify_on_errors ?? true);
  const [notifyOnSuccess, setNotifyOnSuccess] = useState(initialData?.notify_on_success ?? false);
  const [showUrl, setShowUrl] = useState(false);

  const builtUrl = buildAppriseUrl(selectedChannel, fields);
  const effectiveUrl = builtUrl || initialData?.apprise_url || '';

  const handleChannelSelect = (channelId: string) => {
    setSelectedChannel(channelId);
    setFields({});
    setStep(2);
  };

  const handleFieldChange = (key: string, value: string) => {
    setFields((prev) => ({ ...prev, [key]: value }));
  };

  const canProceedStep2 = () => {
    const hasAnyField = Object.values(fields).some((v) => v.trim());
    if (initialData?.apprise_url && !hasAnyField) return true;
    const channelFields = CHANNEL_FIELDS[selectedChannel] ?? [];
    return channelFields.every((f) => f.optional || (fields[f.key] ?? '').trim().length > 0);
  };

  const handleSubmit = () => {
    if (!effectiveUrl || !name.trim()) return;
    onComplete({
      name: name.trim(),
      channel: selectedChannel,
      apprise_url: effectiveUrl,
      notify_on_errors: notifyOnErrors,
      notify_on_success: notifyOnSuccess,
    });
  };

  // ── Step 1: Choose channel ─────────────────────────────────────────────
  if (step === 1) {
    return (
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Bell className="h-5 w-5 text-blue-600" />
            Choose Notification Channel
          </h3>
          <p className="text-sm text-gray-500 mt-1">Select how you want to receive alerts.</p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {CHANNEL_OPTIONS.map((channel) => (
            <button
              key={channel.id}
              type="button"
              onClick={() => handleChannelSelect(channel.id)}
              className="flex flex-col items-start gap-2 p-4 rounded-lg border-2 border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors text-left"
            >
              <span className="text-2xl">{channel.icon}</span>
              <div>
                <p className="text-sm font-semibold text-gray-900">{channel.label}</p>
                <p className="text-xs text-gray-500 mt-0.5 leading-snug">{channel.description}</p>
              </div>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onCancel}
          className="w-full py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
        >
          Cancel
        </button>
      </div>
    );
  }

  // ── Step 2: Fill in fields ─────────────────────────────────────────────
  if (step === 2) {
    const channelOption = CHANNEL_OPTIONS.find((c) => c.id === selectedChannel);
    const channelFields = CHANNEL_FIELDS[selectedChannel] ?? [];

    return (
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => {
            setStep(1);
            setFields({});
          }}
          className="flex items-center text-sm text-blue-600 hover:text-blue-800"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to channel selection
        </button>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-3">
          <span className="text-2xl">{channelOption?.icon}</span>
          <div>
            <p className="font-semibold text-blue-900">{channelOption?.label}</p>
            <p className="text-xs text-blue-700">{channelOption?.description}</p>
          </div>
        </div>

        {initialData?.apprise_url && (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
            Leave all fields blank to keep the existing URL unchanged.
          </p>
        )}

        <div className="space-y-3">
          {channelFields.map((field) => (
            <div key={field.key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label}
                {field.optional && (
                  <span className="text-gray-400 font-normal ml-1">(optional)</span>
                )}
              </label>
              <input
                type={field.type === 'password' ? 'password' : 'text'}
                value={fields[field.key] ?? ''}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                placeholder={field.placeholder}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {field.hint && <p className="text-xs text-gray-500 mt-1">{field.hint}</p>}
            </div>
          ))}
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => setStep(3)}
            disabled={!canProceedStep2()}
            className="flex-1 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            Next
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    );
  }

  // ── Step 3: Preview + preferences ─────────────────────────────────────
  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={() => setStep(selectedChannel ? 2 : 1)}
        className="flex items-center text-sm text-blue-600 hover:text-blue-800"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to configuration
      </button>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Check className="h-5 w-5 text-green-600" />
          Final Setup
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Name your channel and set notification preferences.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Channel Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. My Telegram Alert"
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {effectiveUrl && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-medium text-gray-600">Apprise URL</p>
            <button
              type="button"
              onClick={() => setShowUrl((v) => !v)}
              className="text-gray-400 hover:text-gray-600"
              aria-label={showUrl ? 'Hide URL' : 'Show URL'}
            >
              {showUrl ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <p
            className={`text-xs font-mono break-all ${
              showUrl ? 'text-gray-800' : 'text-gray-400 select-none'
            }`}
          >
            {showUrl ? effectiveUrl : '•'.repeat(Math.min(effectiveUrl.length, 48))}
          </p>
        </div>
      )}

      <div className="space-y-3">
        <p className="text-sm font-medium text-gray-700">Notify me when:</p>
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={notifyOnErrors}
            onChange={(e) => setNotifyOnErrors(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div>
            <p className="text-sm font-medium text-gray-900">Email processing errors occur</p>
            <p className="text-xs text-gray-500">Get alerted when emails fail to forward</p>
          </div>
        </label>
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={notifyOnSuccess}
            onChange={(e) => setNotifyOnSuccess(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div>
            <p className="text-sm font-medium text-gray-900">Emails are successfully forwarded</p>
            <p className="text-xs text-gray-500">Get a notification for each successful batch</p>
          </div>
        </label>
      </div>

      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!name.trim() || !effectiveUrl}
          className="flex-1 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          <Check className="h-4 w-4" />
          Save Channel
        </button>
      </div>
    </div>
  );
}
