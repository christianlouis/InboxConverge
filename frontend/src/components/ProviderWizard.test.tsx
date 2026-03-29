import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProviderWizard } from './ProviderWizard';

// Mock next/image
jest.mock('next/image', () => {
  return function MockImage({ alt, ...props }: { alt: string; [key: string]: unknown }) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img alt={alt} {...props} />;
  };
});

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Mail: ({ className }: { className?: string }) => <span data-testid="icon-Mail" className={className} />,
  ArrowLeft: ({ className }: { className?: string }) => <span data-testid="icon-ArrowLeft" className={className} />,
}));

const mockOnSelect = jest.fn();
const mockOnManual = jest.fn();

describe('ProviderWizard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── Provider List ──────────────────────────────────────────────────────

  describe('Provider List', () => {
    it('should render all email providers', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      expect(screen.getByText('Gmail')).toBeInTheDocument();
      expect(screen.getByText('GMX')).toBeInTheDocument();
      expect(screen.getByText('WEB.DE')).toBeInTheDocument();
      expect(screen.getByText('Outlook / Hotmail')).toBeInTheDocument();
      expect(screen.getByText('Yahoo Mail')).toBeInTheDocument();
      expect(screen.getByText('AOL Mail')).toBeInTheDocument();
      expect(screen.getByText('T-Online')).toBeInTheDocument();
      expect(screen.getByText('1&1 / IONOS')).toBeInTheDocument();
      expect(screen.getByText('Freenet')).toBeInTheDocument();
      expect(screen.getByText('iCloud Mail')).toBeInTheDocument();
      expect(screen.getByText('Posteo')).toBeInTheDocument();
      expect(screen.getByText('Proton Mail')).toBeInTheDocument();
    });

    it('should show the quick setup heading', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      expect(screen.getByText('Quick Setup — Select Your Email Provider')).toBeInTheDocument();
    });

    it('should show Configure Manually button', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      expect(screen.getByText('Configure Manually')).toBeInTheDocument();
    });

    it('should call onManual when Configure Manually is clicked', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Configure Manually'));
      expect(mockOnManual).toHaveBeenCalled();
    });
  });

  // ── Provider Detail ────────────────────────────────────────────────────

  describe('Provider Detail (after selecting a provider)', () => {
    it('should show provider details when Gmail is selected', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Gmail'));
      expect(screen.getByText(/gmail\.com, googlemail\.com/)).toBeInTheDocument();
      expect(screen.getByText(/Enable IMAP\/POP3 in Gmail settings/)).toBeInTheDocument();
    });

    it('should show protocol selection buttons', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Gmail'));
      expect(screen.getByText('IMAP (Recommended)')).toBeInTheDocument();
      expect(screen.getByText('POP3')).toBeInTheDocument();
    });

    it('should show IMAP server details for Gmail', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Gmail'));
      expect(screen.getByText('imap.gmail.com:993')).toBeInTheDocument();
      expect(screen.getByText('pop.gmail.com:995')).toBeInTheDocument();
    });

    it('should show Back to providers button', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Gmail'));
      expect(screen.getByText('Back to providers')).toBeInTheDocument();
    });

    it('should go back to provider list when Back is clicked', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Gmail'));
      fireEvent.click(screen.getByText('Back to providers'));
      expect(screen.getByText('Quick Setup — Select Your Email Provider')).toBeInTheDocument();
    });

    it('should show Use button with provider name', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Gmail'));
      expect(screen.getByText('Use Gmail Settings')).toBeInTheDocument();
    });
  });

  // ── Provider Selection Callback ────────────────────────────────────────

  describe('onSelect callback', () => {
    it('should call onSelect with IMAP config when IMAP is chosen for Gmail', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Gmail'));
      // IMAP is selected by default
      fireEvent.click(screen.getByText('Use Gmail Settings'));
      expect(mockOnSelect).toHaveBeenCalledWith({
        name: 'Gmail',
        provider_name: 'Gmail',
        protocol: 'imap_ssl',
        host: 'imap.gmail.com',
        port: 993,
        use_ssl: true,
      });
    });

    it('should call onSelect with POP3 config when POP3 is chosen for Gmail', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Gmail'));
      fireEvent.click(screen.getByText('POP3'));
      fireEvent.click(screen.getByText('Use Gmail Settings'));
      expect(mockOnSelect).toHaveBeenCalledWith({
        name: 'Gmail',
        provider_name: 'Gmail',
        protocol: 'pop3_ssl',
        host: 'pop.gmail.com',
        port: 995,
        use_ssl: true,
      });
    });

    it('should call onSelect with correct config for Outlook', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Outlook / Hotmail'));
      fireEvent.click(screen.getByText('Use Outlook / Hotmail Settings'));
      expect(mockOnSelect).toHaveBeenCalledWith({
        name: 'Outlook / Hotmail',
        provider_name: 'Outlook / Hotmail',
        protocol: 'imap_ssl',
        host: 'outlook.office365.com',
        port: 993,
        use_ssl: true,
      });
    });

    it('should call onSelect with correct config for GMX', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('GMX'));
      fireEvent.click(screen.getByText('Use GMX Settings'));
      expect(mockOnSelect).toHaveBeenCalledWith({
        name: 'GMX',
        provider_name: 'GMX',
        protocol: 'imap_ssl',
        host: 'imap.gmx.net',
        port: 993,
        use_ssl: true,
      });
    });
  });

  // ── IMAP-only providers ────────────────────────────────────────────────

  describe('IMAP-only providers', () => {
    it('should only show IMAP option for iCloud', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('iCloud Mail'));
      expect(screen.getByText('IMAP (Recommended)')).toBeInTheDocument();
      expect(screen.queryByText('POP3')).not.toBeInTheDocument();
    });

    it('should only show IMAP option for Posteo', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Posteo'));
      expect(screen.getByText('IMAP (Recommended)')).toBeInTheDocument();
      expect(screen.queryByText('POP3')).not.toBeInTheDocument();
    });

    it('should auto-select IMAP for iCloud and call onSelect correctly', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('iCloud Mail'));
      fireEvent.click(screen.getByText('Use iCloud Mail Settings'));
      expect(mockOnSelect).toHaveBeenCalledWith({
        name: 'iCloud Mail',
        provider_name: 'iCloud Mail',
        protocol: 'imap_ssl',
        host: 'imap.mail.me.com',
        port: 993,
        use_ssl: true,
      });
    });
  });

  // ── Proton Mail (Bridge) ───────────────────────────────────────────────

  describe('Proton Mail (Bridge)', () => {
    it('should show Proton Mail Bridge notes', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Proton Mail'));
      expect(screen.getByText(/Requires Proton Mail Bridge/)).toBeInTheDocument();
    });

    it('should show localhost connection details', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Proton Mail'));
      expect(screen.getByText('127.0.0.1:1143')).toBeInTheDocument();
      expect(screen.getByText('127.0.0.1:1144')).toBeInTheDocument();
    });

    it('should call onSelect with localhost config', () => {
      render(<ProviderWizard onSelect={mockOnSelect} onManual={mockOnManual} />);
      fireEvent.click(screen.getByText('Proton Mail'));
      fireEvent.click(screen.getByText('Use Proton Mail Settings'));
      expect(mockOnSelect).toHaveBeenCalledWith({
        name: 'Proton Mail',
        provider_name: 'Proton Mail',
        protocol: 'imap_ssl',
        host: '127.0.0.1',
        port: 1143,
        use_ssl: true,
      });
    });
  });
});
