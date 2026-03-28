'use client';

import { useState } from 'react';
import { Mail, ArrowLeft } from 'lucide-react';

interface ProviderPreset {
  id: string;
  name: string;
  logo: string;
  domains: string[];
  imap_ssl?: { host: string; port: number } | null;
  pop3_ssl?: { host: string; port: number } | null;
  notes?: string;
}

interface ProviderConfig {
  name: string;
  protocol: string;
  host: string;
  port: number;
  use_ssl: boolean;
}

interface ProviderWizardProps {
  onSelect: (config: ProviderConfig) => void;
  onManual: () => void;
}

const PROVIDERS: ProviderPreset[] = [
  {
    id: 'gmail',
    name: 'Gmail',
    logo: '/providers/gmail.svg',
    domains: ['gmail.com', 'googlemail.com'],
    imap_ssl: { host: 'imap.gmail.com', port: 993 },
    pop3_ssl: { host: 'pop.gmail.com', port: 995 },
    notes: 'Enable IMAP/POP3 in Gmail settings. Use an App Password if 2FA is enabled.',
  },
  {
    id: 'gmx',
    name: 'GMX',
    logo: '/providers/gmx.svg',
    domains: ['gmx.de', 'gmx.net', 'gmx.at', 'gmx.ch', 'gmx.com'],
    imap_ssl: { host: 'imap.gmx.net', port: 993 },
    pop3_ssl: { host: 'pop.gmx.net', port: 995 },
    notes: 'Enable POP3/IMAP in GMX settings under E-Mail > POP3/IMAP Abruf.',
  },
  {
    id: 'webde',
    name: 'WEB.DE',
    logo: '/providers/webde.svg',
    domains: ['web.de'],
    imap_ssl: { host: 'imap.web.de', port: 993 },
    pop3_ssl: { host: 'pop3.web.de', port: 995 },
    notes: 'Enable POP3/IMAP in WEB.DE settings under E-Mail > POP3/IMAP Abruf.',
  },
  {
    id: 'outlook',
    name: 'Outlook / Hotmail',
    logo: '/providers/outlook.svg',
    domains: ['outlook.com', 'hotmail.com', 'live.com', 'msn.com', 'outlook.de'],
    imap_ssl: { host: 'outlook.office365.com', port: 993 },
    pop3_ssl: { host: 'outlook.office365.com', port: 995 },
    notes: 'Use your Microsoft account credentials.',
  },
  {
    id: 'yahoo',
    name: 'Yahoo Mail',
    logo: '/providers/yahoo.svg',
    domains: ['yahoo.com', 'yahoo.de', 'yahoo.co.uk', 'ymail.com'],
    imap_ssl: { host: 'imap.mail.yahoo.com', port: 993 },
    pop3_ssl: { host: 'pop.mail.yahoo.com', port: 995 },
    notes: 'Generate an App Password in Yahoo account security settings.',
  },
  {
    id: 'aol',
    name: 'AOL Mail',
    logo: '/providers/aol.svg',
    domains: ['aol.com', 'aim.com'],
    imap_ssl: { host: 'imap.aol.com', port: 993 },
    pop3_ssl: { host: 'pop.aol.com', port: 995 },
    notes: 'Generate an App Password in AOL account security settings.',
  },
  {
    id: 'tonline',
    name: 'T-Online',
    logo: '/providers/tonline.svg',
    domains: ['t-online.de'],
    imap_ssl: { host: 'secureimap.t-online.de', port: 993 },
    pop3_ssl: { host: 'securepop.t-online.de', port: 995 },
    notes: 'Use your T-Online E-Mail-Passwort (not your Telekom login password).',
  },
  {
    id: 'ionos',
    name: '1&1 / IONOS',
    logo: '/providers/ionos.svg',
    domains: ['online.de', 'onlinehome.de', '1und1.de'],
    imap_ssl: { host: 'imap.ionos.de', port: 993 },
    pop3_ssl: { host: 'pop.ionos.de', port: 995 },
    notes: 'Use your IONOS email credentials.',
  },
  {
    id: 'freenet',
    name: 'Freenet',
    logo: '/providers/freenet.svg',
    domains: ['freenet.de'],
    imap_ssl: { host: 'mx.freenet.de', port: 993 },
    pop3_ssl: { host: 'mx.freenet.de', port: 995 },
    notes: 'Use your Freenet email credentials.',
  },
  {
    id: 'icloud',
    name: 'iCloud Mail',
    logo: '/providers/icloud.svg',
    domains: ['icloud.com', 'me.com', 'mac.com'],
    imap_ssl: { host: 'imap.mail.me.com', port: 993 },
    pop3_ssl: null,
    notes: 'Generate an app-specific password at appleid.apple.com. IMAP only.',
  },
  {
    id: 'posteo',
    name: 'Posteo',
    logo: '/providers/posteo.svg',
    domains: ['posteo.de', 'posteo.net'],
    imap_ssl: { host: 'posteo.de', port: 993 },
    pop3_ssl: null,
    notes: 'Posteo supports IMAP only.',
  },
  {
    id: 'protonmail',
    name: 'Proton Mail',
    logo: '/providers/protonmail.svg',
    domains: ['proton.me', 'protonmail.com', 'protonmail.ch', 'pm.me'],
    imap_ssl: { host: '127.0.0.1', port: 1143 },
    pop3_ssl: { host: '127.0.0.1', port: 1144 },
    notes: 'Requires Proton Mail Bridge running locally. Use your Bridge password (not your Proton account password). Default Bridge ports: IMAP 127.0.0.1:1143, POP3 127.0.0.1:1144.',
  },
];

export function ProviderWizard({ onSelect, onManual }: ProviderWizardProps) {
  const [selectedProvider, setSelectedProvider] = useState<ProviderPreset | null>(null);
  const [selectedProtocol, setSelectedProtocol] = useState<'imap_ssl' | 'pop3_ssl'>('imap_ssl');

  const handleProviderClick = (provider: ProviderPreset) => {
    setSelectedProvider(provider);

    // If only one protocol, auto-select it
    if (!provider.pop3_ssl && provider.imap_ssl) {
      setSelectedProtocol('imap_ssl');
    } else if (provider.pop3_ssl && !provider.imap_ssl) {
      setSelectedProtocol('pop3_ssl');
    }
  };

  const handleConfirm = () => {
    if (!selectedProvider) return;

    const config = selectedProvider[selectedProtocol];
    if (!config) return;

    onSelect({
      name: selectedProvider.name,
      protocol: selectedProtocol === 'imap_ssl' ? 'imap_ssl' : 'pop3_ssl',
      host: config.host,
      port: config.port,
      use_ssl: true,
    });
  };

  if (selectedProvider) {
    return (
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => setSelectedProvider(null)}
          className="flex items-center text-sm text-blue-600 hover:text-blue-800"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to providers
        </button>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
            <div className="h-6 flex items-center flex-shrink-0">
              <img
                src={selectedProvider.logo}
                alt={selectedProvider.name}
                style={{ maxHeight: '100%', maxWidth: '80px', objectFit: 'contain' }}
              />
            </div>
            {selectedProvider.name}
          </h4>
          <p className="text-sm text-blue-700 mb-1">
            Domains: {selectedProvider.domains.join(', ')}
          </p>
          {selectedProvider.notes && (
            <p className="text-sm text-blue-600 mt-2 italic">{selectedProvider.notes}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Protocol
          </label>
          <div className="grid grid-cols-2 gap-3">
            {selectedProvider.imap_ssl && (
              <button
                type="button"
                onClick={() => setSelectedProtocol('imap_ssl')}
                className={`p-3 rounded-lg border-2 text-left transition-colors ${
                  selectedProtocol === 'imap_ssl'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-medium text-gray-900">IMAP (Recommended)</div>
                <div className="text-xs text-gray-500 mt-1">
                  {selectedProvider.imap_ssl.host}:{selectedProvider.imap_ssl.port}
                </div>
              </button>
            )}
            {selectedProvider.pop3_ssl && (
              <button
                type="button"
                onClick={() => setSelectedProtocol('pop3_ssl')}
                className={`p-3 rounded-lg border-2 text-left transition-colors ${
                  selectedProtocol === 'pop3_ssl'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-medium text-gray-900">POP3</div>
                <div className="text-xs text-gray-500 mt-1">
                  {selectedProvider.pop3_ssl.host}:{selectedProvider.pop3_ssl.port}
                </div>
              </button>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={handleConfirm}
          className="w-full py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Use {selectedProvider.name} Settings
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">
          Quick Setup — Select Your Email Provider
        </h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {PROVIDERS.map((provider) => (
            <button
              key={provider.id}
              type="button"
              onClick={() => handleProviderClick(provider)}
              className="flex flex-col items-center gap-2 p-3 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors text-center"
            >
              {/* Fixed-height logo container – logo scales to its natural aspect ratio */}
              <div className="h-8 w-full flex items-center justify-center">
                <img
                  src={provider.logo}
                  alt={provider.name}
                  style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }}
                />
              </div>
              <div className="text-xs font-medium text-gray-900 truncate w-full">{provider.name}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-white text-gray-500">or</span>
        </div>
      </div>

      <button
        type="button"
        onClick={onManual}
        className="w-full flex items-center justify-center gap-2 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <Mail className="h-4 w-4" />
        Configure Manually
      </button>
    </div>
  );
}
