import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationWizard } from './NotificationWizard';

// Mock lucide-react icons as simple spans
jest.mock('lucide-react', () => ({
  ArrowLeft: ({ className }: { className?: string }) => <span data-testid="icon-ArrowLeft" className={className} />,
  Bell: ({ className }: { className?: string }) => <span data-testid="icon-Bell" className={className} />,
  Check: ({ className }: { className?: string }) => <span data-testid="icon-Check" className={className} />,
  Eye: ({ className }: { className?: string }) => <span data-testid="icon-Eye" className={className} />,
  EyeOff: ({ className }: { className?: string }) => <span data-testid="icon-EyeOff" className={className} />,
  Send: ({ className }: { className?: string }) => <span data-testid="icon-Send" className={className} />,
}));

const mockOnComplete = jest.fn();
const mockOnCancel = jest.fn();

describe('NotificationWizard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── Step 1: Channel Selection ──────────────────────────────────────────

  describe('Step 1 - Channel Selection', () => {
    it('should render all channel options', () => {
      render(<NotificationWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);
      expect(screen.getByText('Telegram')).toBeInTheDocument();
      expect(screen.getByText('Discord')).toBeInTheDocument();
      expect(screen.getByText('Slack')).toBeInTheDocument();
      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('Webhook')).toBeInTheDocument();
      expect(screen.getByText('Custom Apprise URL')).toBeInTheDocument();
    });

    it('should show the channel selection heading', () => {
      render(<NotificationWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);
      expect(screen.getByText('Choose Notification Channel')).toBeInTheDocument();
    });

    it('should call onCancel when Cancel button is clicked', () => {
      render(<NotificationWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);
      fireEvent.click(screen.getByText('Cancel'));
      expect(mockOnCancel).toHaveBeenCalled();
    });

    it('should navigate to step 2 when a channel is selected', () => {
      render(<NotificationWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);
      fireEvent.click(screen.getByText('Telegram'));
      // Step 2 shows field labels
      expect(screen.getByText('Bot Token')).toBeInTheDocument();
      expect(screen.getByText('Chat ID')).toBeInTheDocument();
    });
  });

  // ── Step 2: Field Entry ────────────────────────────────────────────────

  describe('Step 2 - Field Entry', () => {
    function goToStep2(channel: string) {
      render(<NotificationWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);
      fireEvent.click(screen.getByText(channel));
    }

    it('should show Telegram fields', () => {
      goToStep2('Telegram');
      expect(screen.getByText('Bot Token')).toBeInTheDocument();
      expect(screen.getByText('Chat ID')).toBeInTheDocument();
    });

    it('should show Discord fields', () => {
      goToStep2('Discord');
      expect(screen.getByText('Discord Webhook URL')).toBeInTheDocument();
    });

    it('should show Slack fields', () => {
      goToStep2('Slack');
      expect(screen.getByText('Slack Webhook URL')).toBeInTheDocument();
    });

    it('should show Email fields', () => {
      goToStep2('Email');
      expect(screen.getByText('Username / Email')).toBeInTheDocument();
      expect(screen.getByText('SMTP Password')).toBeInTheDocument();
      expect(screen.getByText('SMTP Host')).toBeInTheDocument();
      expect(screen.getByText('SMTP Port')).toBeInTheDocument();
    });

    it('should show Webhook fields', () => {
      goToStep2('Webhook');
      expect(screen.getByText('Webhook URL')).toBeInTheDocument();
    });

    it('should show Custom Apprise URL fields', () => {
      goToStep2('Custom Apprise URL');
      expect(screen.getByText('Apprise URL')).toBeInTheDocument();
    });

    it('should go back to step 1 when Back button is clicked', () => {
      goToStep2('Telegram');
      fireEvent.click(screen.getByText('Back to channel selection'));
      expect(screen.getByText('Choose Notification Channel')).toBeInTheDocument();
    });

    it('should disable Next button when required fields are empty', () => {
      goToStep2('Telegram');
      const nextButton = screen.getByText('Next').closest('button');
      expect(nextButton).toBeDisabled();
    });

    it('should enable Next button when required fields are filled', () => {
      goToStep2('Telegram');
      const inputs = screen.getAllByRole('textbox');
      fireEvent.change(inputs[0], { target: { value: '110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw' } });
      fireEvent.change(inputs[1], { target: { value: '12345678' } });
      const nextButton = screen.getByText('Next').closest('button');
      expect(nextButton).not.toBeDisabled();
    });

    it('should call onCancel when Cancel is clicked on step 2', () => {
      goToStep2('Telegram');
      fireEvent.click(screen.getByText('Cancel'));
      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  // ── Step 3: Preview + Preferences ──────────────────────────────────────

  describe('Step 3 - Preview and Preferences', () => {
    function goToStep3WithTelegram() {
      render(<NotificationWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);
      // Step 1: select Telegram
      fireEvent.click(screen.getByText('Telegram'));
      // Step 2: fill fields
      const inputs = screen.getAllByRole('textbox');
      fireEvent.change(inputs[0], { target: { value: 'mybot:AAHdqTcvCH1vGWJx' } });
      fireEvent.change(inputs[1], { target: { value: '12345678' } });
      // Go to step 3
      fireEvent.click(screen.getByText('Next').closest('button')!);
    }

    it('should show Final Setup heading', () => {
      goToStep3WithTelegram();
      expect(screen.getByText('Final Setup')).toBeInTheDocument();
    });

    it('should show Channel Name input', () => {
      goToStep3WithTelegram();
      expect(screen.getByText('Channel Name')).toBeInTheDocument();
    });

    it('should show notification preference checkboxes', () => {
      goToStep3WithTelegram();
      expect(screen.getByText('Email processing errors occur')).toBeInTheDocument();
      expect(screen.getByText('Emails are successfully forwarded')).toBeInTheDocument();
    });

    it('should have errors checkbox checked by default', () => {
      goToStep3WithTelegram();
      const checkboxes = screen.getAllByRole('checkbox');
      // First checkbox is "notify on errors" (default: true)
      expect(checkboxes[0]).toBeChecked();
      // Second is "notify on success" (default: false)
      expect(checkboxes[1]).not.toBeChecked();
    });

    it('should disable Save button when name is empty', () => {
      goToStep3WithTelegram();
      const saveButton = screen.getByText('Save Channel').closest('button');
      expect(saveButton).toBeDisabled();
    });

    it('should enable Save button when name is filled', () => {
      goToStep3WithTelegram();
      const nameInput = screen.getByPlaceholderText('e.g. My Telegram Alert');
      fireEvent.change(nameInput, { target: { value: 'My Alert' } });
      const saveButton = screen.getByText('Save Channel').closest('button');
      expect(saveButton).not.toBeDisabled();
    });

    it('should call onComplete with correct data on Save', () => {
      goToStep3WithTelegram();
      const nameInput = screen.getByPlaceholderText('e.g. My Telegram Alert');
      fireEvent.change(nameInput, { target: { value: 'My Telegram Alert' } });
      fireEvent.click(screen.getByText('Save Channel').closest('button')!);

      expect(mockOnComplete).toHaveBeenCalledWith({
        name: 'My Telegram Alert',
        channel: 'telegram',
        apprise_url: 'tgram://mybot:AAHdqTcvCH1vGWJx/12345678/',
        notify_on_errors: true,
        notify_on_success: false,
      });
    });

    it('should toggle notification preferences', () => {
      goToStep3WithTelegram();
      const checkboxes = screen.getAllByRole('checkbox');

      // Uncheck errors
      fireEvent.click(checkboxes[0]);
      // Check success
      fireEvent.click(checkboxes[1]);

      const nameInput = screen.getByPlaceholderText('e.g. My Telegram Alert');
      fireEvent.change(nameInput, { target: { value: 'Test' } });
      fireEvent.click(screen.getByText('Save Channel').closest('button')!);

      expect(mockOnComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          notify_on_errors: false,
          notify_on_success: true,
        })
      );
    });

    it('should toggle URL visibility', () => {
      goToStep3WithTelegram();
      // URL should be hidden by default (masked with dots)
      const urlText = screen.getByText(/^•+$/);
      expect(urlText).toBeInTheDocument();

      // Click the show/hide button
      const toggleButton = screen.getByLabelText('Show URL');
      fireEvent.click(toggleButton);

      // Now the URL should be visible
      expect(screen.getByText(/^tgram:\/\//)).toBeInTheDocument();
    });

    it('should go back to step 2 when Back is clicked', () => {
      goToStep3WithTelegram();
      fireEvent.click(screen.getByText('Back to configuration'));
      // Should be back on step 2 with Telegram fields
      expect(screen.getByText('Bot Token')).toBeInTheDocument();
    });
  });

  // ── buildAppriseUrl via component behavior ─────────────────────────────

  describe('Apprise URL generation', () => {
    function fillAndSubmit(channel: string, fields: Record<string, string>) {
      render(<NotificationWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);
      fireEvent.click(screen.getByText(channel));

      const inputs = screen.getAllByRole('textbox');
      const passwordInputs = document.querySelectorAll('input[type="password"]');
      const allInputs = [...Array.from(inputs), ...Array.from(passwordInputs)];

      Object.values(fields).forEach((value, i) => {
        fireEvent.change(allInputs[i], { target: { value } });
      });

      fireEvent.click(screen.getByText('Next').closest('button')!);

      const nameInput = screen.getByPlaceholderText('e.g. My Telegram Alert');
      fireEvent.change(nameInput, { target: { value: 'Test' } });
      fireEvent.click(screen.getByText('Save Channel').closest('button')!);

      return mockOnComplete.mock.calls[0][0].apprise_url;
    }

    it('should build correct Telegram URL', () => {
      const url = fillAndSubmit('Telegram', {
        bot_token: '110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw',
        chat_id: '12345678',
      });
      expect(url).toBe('tgram://110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw/12345678/');
    });

    it('should build correct Discord URL from webhook', () => {
      const url = fillAndSubmit('Discord', {
        webhook_url: 'https://discord.com/api/webhooks/123456789/abcdefghij',
      });
      expect(url).toBe('discord://123456789/abcdefghij/');
    });

    it('should build correct Slack URL from webhook', () => {
      const url = fillAndSubmit('Slack', {
        webhook_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXX',
      });
      expect(url).toBe('slack://T00000000/B00000000/XXXXXXXXXXXXXXXX/');
    });

    it('should build correct Webhook URL', () => {
      const url = fillAndSubmit('Webhook', {
        url: 'https://hooks.example.com/notify',
      });
      expect(url).toBe('https://hooks.example.com/notify');
    });

    it('should pass through Custom Apprise URL', () => {
      const url = fillAndSubmit('Custom Apprise URL', {
        apprise_url: 'tgram://mybot/mychat/',
      });
      expect(url).toBe('tgram://mybot/mychat/');
    });
  });

  // ── Edit mode (initialData) ────────────────────────────────────────────

  describe('Edit mode with initialData', () => {
    const initialData = {
      name: 'My Existing Alert',
      channel: 'telegram',
      apprise_url: 'tgram://existingbot/existingchat/',
      notify_on_errors: true,
      notify_on_success: true,
    };

    it('should start on step 3 when initialData is provided', () => {
      render(
        <NotificationWizard
          onComplete={mockOnComplete}
          onCancel={mockOnCancel}
          initialData={initialData}
        />
      );
      expect(screen.getByText('Final Setup')).toBeInTheDocument();
    });

    it('should pre-fill the name from initialData', () => {
      render(
        <NotificationWizard
          onComplete={mockOnComplete}
          onCancel={mockOnCancel}
          initialData={initialData}
        />
      );
      const nameInput = screen.getByPlaceholderText('e.g. My Telegram Alert') as HTMLInputElement;
      expect(nameInput.value).toBe('My Existing Alert');
    });

    it('should pre-set notification preferences from initialData', () => {
      render(
        <NotificationWizard
          onComplete={mockOnComplete}
          onCancel={mockOnCancel}
          initialData={initialData}
        />
      );
      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes[0]).toBeChecked(); // notify_on_errors
      expect(checkboxes[1]).toBeChecked(); // notify_on_success
    });
  });
});
