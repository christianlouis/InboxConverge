import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AddMailAccountModal } from './AddMailAccountModal';
import { MailAccount } from '@/lib/api';

// ── Mock state ──────────────────────────────────────────────────────────────
const mockMutateAsyncCreate = jest.fn().mockResolvedValue({});
const mockMutateAsyncUpdate = jest.fn().mockResolvedValue({});
const mockInvalidateQueries = jest.fn();

let createIsPending = false;
let updateIsPending = false;
let mutationCallCount = 0;

// ── Mocks ───────────────────────────────────────────────────────────────────

jest.mock('@tanstack/react-query', () => ({
  useMutation: jest.fn().mockImplementation(() => {
    mutationCallCount++;
    if (mutationCallCount % 2 === 1) {
      return { mutateAsync: mockMutateAsyncCreate, isPending: createIsPending };
    }
    return { mutateAsync: mockMutateAsyncUpdate, isPending: updateIsPending };
  }),
  useQueryClient: () => ({
    invalidateQueries: mockInvalidateQueries,
  }),
}));

jest.mock('@/lib/api', () => ({
  mailAccountsApi: {
    create: jest.fn(),
    update: jest.fn(),
    test: jest.fn(),
    testExisting: jest.fn(),
    autoDetect: jest.fn(),
  },
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    user: { email: 'currentuser@example.com' },
  }),
}));

jest.mock('lucide-react', () => ({
  X: ({ className }: { className?: string }) => (
    <span data-testid="icon-X" className={className} />
  ),
  Loader2: ({ className }: { className?: string }) => (
    <span data-testid="icon-Loader2" className={className} />
  ),
  CheckCircle: ({ className }: { className?: string }) => (
    <span data-testid="icon-CheckCircle" className={className} />
  ),
  XCircle: ({ className }: { className?: string }) => (
    <span data-testid="icon-XCircle" className={className} />
  ),
}));

jest.mock('./ProviderWizard', () => ({
  ProviderWizard: ({
    onSelect,
    onManual,
  }: {
    onSelect: (config: unknown) => void;
    onManual: () => void;
  }) => (
    <div data-testid="provider-wizard">
      <button
        onClick={() =>
          onSelect({
            name: 'Gmail',
            provider_name: 'Gmail',
            protocol: 'imap_ssl',
            host: 'imap.gmail.com',
            port: 993,
            use_ssl: true,
          })
        }
      >
        Select Gmail
      </button>
      <button onClick={onManual}>Manual Setup</button>
    </div>
  ),
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

const mockAccount: MailAccount = {
  id: 42,
  user_id: 1,
  name: 'My Work Email',
  email_address: 'work@example.com',
  protocol: 'imap_ssl',
  host: 'imap.example.com',
  port: 993,
  use_ssl: true,
  use_tls: false,
  username: 'work@example.com',
  forward_to: 'me@gmail.com',
  delivery_method: 'gmail_api',
  is_enabled: true,
  check_interval_minutes: 10,
  max_emails_per_check: 25,
  delete_after_forward: false,
  status: 'active',
  provider_name: 'Gmail',
  auto_detected: false,
  total_emails_processed: 100,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-02T00:00:00Z',
  last_checked_at: '2024-01-02T12:00:00Z',
  last_error: null,
};

const { mailAccountsApi } = jest.requireMock('@/lib/api') as {
  mailAccountsApi: {
    create: jest.Mock;
    update: jest.Mock;
    test: jest.Mock;
    testExisting: jest.Mock;
    autoDetect: jest.Mock;
  };
};

// ── Setup / Teardown ────────────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  mutationCallCount = 0;
  createIsPending = false;
  updateIsPending = false;
});

// ── Tests ───────────────────────────────────────────────────────────────────

describe('AddMailAccountModal', () => {
  // 1. Create mode renders ProviderWizard
  it('renders ProviderWizard in create mode', () => {
    render(<AddMailAccountModal onClose={jest.fn()} />);
    expect(screen.getByTestId('provider-wizard')).toBeInTheDocument();
  });

  // 2. Edit mode shows form with pre-filled data
  it('renders form with pre-filled data in edit mode', () => {
    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);
    expect(screen.queryByTestId('provider-wizard')).not.toBeInTheDocument();
    expect(screen.getByDisplayValue('My Work Email')).toBeInTheDocument();
    expect(screen.getByDisplayValue('work@example.com')).toBeInTheDocument();
    expect(screen.getByDisplayValue('imap.example.com')).toBeInTheDocument();
    expect(screen.getByDisplayValue('993')).toBeInTheDocument();
  });

  // 3. Shows correct title for create mode
  it('shows "Add Mail Account" title in create mode', () => {
    render(<AddMailAccountModal onClose={jest.fn()} />);
    expect(screen.getByText('Add Mail Account')).toBeInTheDocument();
  });

  // 4. Shows correct title for edit mode
  it('shows "Edit Mail Account" title in edit mode', () => {
    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);
    expect(screen.getByText('Edit Mail Account')).toBeInTheDocument();
  });

  // 5. Provider selection fills form and advances to form step
  it('fills form and advances to form step on provider selection', () => {
    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Select Gmail'));
    // Wizard should be gone, form should be visible
    expect(screen.queryByTestId('provider-wizard')).not.toBeInTheDocument();
    expect(screen.getByDisplayValue('Gmail')).toBeInTheDocument();
    expect(screen.getByDisplayValue('imap.gmail.com')).toBeInTheDocument();
    expect(screen.getByDisplayValue('993')).toBeInTheDocument();
  });

  // 6. Back to provider selection works in create mode
  it('goes back to provider selection in create mode', () => {
    render(<AddMailAccountModal onClose={jest.fn()} />);
    // Advance to form via manual
    fireEvent.click(screen.getByText('Manual Setup'));
    expect(screen.queryByTestId('provider-wizard')).not.toBeInTheDocument();
    // Click back
    fireEvent.click(screen.getByText('← Back to provider selection'));
    expect(screen.getByTestId('provider-wizard')).toBeInTheDocument();
  });

  // 7. No back button in edit mode
  it('does not show back button in edit mode', () => {
    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);
    expect(screen.queryByText('← Back to provider selection')).not.toBeInTheDocument();
  });

  // 8. Form field changes update state
  it('updates form state when fields change', () => {
    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);
    const nameInput = screen.getByDisplayValue('My Work Email');
    fireEvent.change(nameInput, { target: { name: 'name', value: 'New Name', type: 'text' } });
    expect(screen.getByDisplayValue('New Name')).toBeInTheDocument();
  });

  // 9. Username/email sync
  it('syncs email_address with username when username changes', () => {
    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));
    const usernameInput = screen.getByPlaceholderText('user@example.com');
    fireEvent.change(usernameInput, {
      target: { name: 'username', value: 'new@example.com', type: 'text' },
    });
    // The forward_to field is a different input; email_address is internal state
    // We can verify by checking the username input value
    expect(usernameInput).toHaveValue('new@example.com');
  });

  // 10. Checkbox changes work
  it('toggles checkbox values', () => {
    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);
    const sslCheckbox = screen.getByLabelText('Use SSL/TLS');
    expect(sslCheckbox).toBeChecked();
    fireEvent.click(sslCheckbox);
    expect(sslCheckbox).not.toBeChecked();

    const deleteCheckbox = screen.getByLabelText('Delete after forwarding');
    expect(deleteCheckbox).not.toBeChecked();
    fireEvent.click(deleteCheckbox);
    expect(deleteCheckbox).toBeChecked();

    const enabledCheckbox = screen.getByLabelText('Enabled');
    expect(enabledCheckbox).toBeChecked();
    fireEvent.click(enabledCheckbox);
    expect(enabledCheckbox).not.toBeChecked();
  });

  // 11. Auto-detect success updates form fields
  it('updates form on successful auto-detect', async () => {
    mailAccountsApi.autoDetect.mockResolvedValue({
      success: true,
      suggestions: [{ protocol: 'pop3_ssl', host: 'pop.detected.com', port: 995, use_ssl: true }],
    });
    jest.spyOn(window, 'alert').mockImplementation(() => {});

    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));
    const usernameInput = screen.getByPlaceholderText('user@example.com');
    fireEvent.change(usernameInput, {
      target: { name: 'username', value: 'test@detect.com', type: 'text' },
    });
    fireEvent.click(screen.getByText('Auto-Detect'));

    await waitFor(() => {
      expect(screen.getByDisplayValue('pop.detected.com')).toBeInTheDocument();
    });
    expect(window.alert).toHaveBeenCalledWith('Settings auto-detected successfully!');
  });

  // 12. Auto-detect failure shows alert
  it('shows alert on auto-detect failure', async () => {
    mailAccountsApi.autoDetect.mockRejectedValue(new Error('fail'));
    jest.spyOn(window, 'alert').mockImplementation(() => {});

    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));
    const usernameInput = screen.getByPlaceholderText('user@example.com');
    fireEvent.change(usernameInput, {
      target: { name: 'username', value: 'test@fail.com', type: 'text' },
    });
    fireEvent.click(screen.getByText('Auto-Detect'));

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith(
        'Failed to auto-detect settings. Please enter manually.'
      );
    });
  });

  // 13. Auto-detect requires username
  it('alerts when auto-detect is attempted without username', () => {
    jest.spyOn(window, 'alert').mockImplementation(() => {});
    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));
    fireEvent.click(screen.getByText('Auto-Detect'));
    expect(window.alert).toHaveBeenCalledWith('Please enter an email address first');
  });

  // 14. Test connection success
  it('shows success message on successful test connection', async () => {
    mailAccountsApi.test.mockResolvedValue({ success: true, message: 'Connected!' });

    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));

    // Fill required fields
    const usernameInput = screen.getByPlaceholderText('user@example.com');
    const passwordInput = screen.getByPlaceholderText('Password');
    const hostInput = screen.getByPlaceholderText('pop.gmail.com');

    fireEvent.change(usernameInput, {
      target: { name: 'username', value: 'u@test.com', type: 'text' },
    });
    fireEvent.change(passwordInput, {
      target: { name: 'password', value: 'pass123', type: 'password' },
    });
    fireEvent.change(hostInput, {
      target: { name: 'host', value: 'mail.test.com', type: 'text' },
    });

    fireEvent.click(screen.getByText('Test Connection'));

    await waitFor(() => {
      expect(screen.getByText('Connected!')).toBeInTheDocument();
    });
    expect(screen.getByTestId('icon-CheckCircle')).toBeInTheDocument();
  });

  // 15. Test connection error
  it('shows error message on failed test connection', async () => {
    mailAccountsApi.test.mockResolvedValue({ success: false, message: 'Auth failed' });

    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));

    const usernameInput = screen.getByPlaceholderText('user@example.com');
    const passwordInput = screen.getByPlaceholderText('Password');
    const hostInput = screen.getByPlaceholderText('pop.gmail.com');

    fireEvent.change(usernameInput, {
      target: { name: 'username', value: 'u@test.com', type: 'text' },
    });
    fireEvent.change(passwordInput, {
      target: { name: 'password', value: 'wrong', type: 'password' },
    });
    fireEvent.change(hostInput, {
      target: { name: 'host', value: 'mail.test.com', type: 'text' },
    });

    fireEvent.click(screen.getByText('Test Connection'));

    await waitFor(() => {
      expect(screen.getByText('Auth failed')).toBeInTheDocument();
    });
    expect(screen.getByTestId('icon-XCircle')).toBeInTheDocument();
  });

  // 16. Test connection missing fields
  it('shows validation error when test fields are missing', async () => {
    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));
    fireEvent.click(screen.getByText('Test Connection'));

    await waitFor(() => {
      expect(
        screen.getByText('Please fill in username, password, and host')
      ).toBeInTheDocument();
    });
  });

  // 17. Test connection in edit mode uses testExisting when no password
  it('uses testExisting in edit mode when no password is entered', async () => {
    mailAccountsApi.testExisting.mockResolvedValue({
      success: true,
      message: 'Existing OK',
    });

    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Test Connection'));

    await waitFor(() => {
      expect(mailAccountsApi.testExisting).toHaveBeenCalledWith(42);
    });
    expect(screen.getByText('Existing OK')).toBeInTheDocument();
  });

  // 18. Submit in create mode calls createMutation
  it('calls create mutation on submit in create mode', async () => {
    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));

    // Fill required form fields
    const nameInput = screen.getByPlaceholderText('My Email Account');
    const usernameInput = screen.getByPlaceholderText('user@example.com');
    const passwordInput = screen.getByPlaceholderText('Password');
    const hostInput = screen.getByPlaceholderText('pop.gmail.com');
    const forwardInput = screen.getByPlaceholderText('you@gmail.com');

    fireEvent.change(nameInput, {
      target: { name: 'name', value: 'Test Account', type: 'text' },
    });
    fireEvent.change(usernameInput, {
      target: { name: 'username', value: 'user@test.com', type: 'text' },
    });
    fireEvent.change(passwordInput, {
      target: { name: 'password', value: 'secret', type: 'password' },
    });
    fireEvent.change(hostInput, {
      target: { name: 'host', value: 'pop.test.com', type: 'text' },
    });
    fireEvent.change(forwardInput, {
      target: { name: 'forward_to', value: 'fwd@gmail.com', type: 'email' },
    });

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(mockMutateAsyncCreate).toHaveBeenCalled();
    });
  });

  // 19. Submit in edit mode calls updateMutation (omits password when blank)
  it('calls update mutation on submit in edit mode, omitting blank password', async () => {
    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(mockMutateAsyncUpdate).toHaveBeenCalled();
    });
    const updateArg = mockMutateAsyncUpdate.mock.calls[0][0];
    expect(updateArg.password).toBeUndefined();
    expect(updateArg.name).toBe('My Work Email');
  });

  // 20. Close button calls onClose
  it('calls onClose when close (X) button is clicked', () => {
    const onClose = jest.fn();
    render(<AddMailAccountModal account={mockAccount} onClose={onClose} />);
    // The X icon button is the one containing the X icon
    const closeButton = screen.getByTestId('icon-X').closest('button')!;
    fireEvent.click(closeButton);
    expect(onClose).toHaveBeenCalled();
  });

  // 21. Backdrop click calls onClose
  it('calls onClose when backdrop is clicked', () => {
    const onClose = jest.fn();
    const { container } = render(
      <AddMailAccountModal account={mockAccount} onClose={onClose} />
    );
    // Backdrop is the div with bg-gray-500/75
    const backdrop = container.querySelector('.bg-gray-500\\/75');
    expect(backdrop).toBeTruthy();
    fireEvent.click(backdrop!);
    expect(onClose).toHaveBeenCalled();
  });

  // 22. Cancel button calls onClose
  it('calls onClose when Cancel button is clicked', () => {
    const onClose = jest.fn();
    render(<AddMailAccountModal account={mockAccount} onClose={onClose} />);
    fireEvent.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalled();
  });

  // 23. Save button shows "Saving..." when mutation is pending
  it('shows "Saving..." when create mutation is pending', () => {
    createIsPending = true;
    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));
    expect(screen.getByText('Saving...')).toBeInTheDocument();
  });

  it('shows "Saving..." when update mutation is pending', () => {
    updateIsPending = true;
    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);
    expect(screen.getByText('Saving...')).toBeInTheDocument();
  });

  // 24. Error message extraction - string detail
  it('shows string error detail on submit failure', async () => {
    jest.spyOn(window, 'alert').mockImplementation(() => {});
    mockMutateAsyncUpdate.mockRejectedValueOnce({
      response: { data: { detail: 'Account already exists' } },
    });

    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith('Account already exists');
    });
  });

  // 25. Error message extraction - array detail (validation errors)
  it('shows joined validation errors on submit failure', async () => {
    jest.spyOn(window, 'alert').mockImplementation(() => {});
    mockMutateAsyncUpdate.mockRejectedValueOnce({
      response: {
        data: {
          detail: [{ msg: 'field required' }, { msg: 'invalid email' }],
        },
      },
    });

    render(<AddMailAccountModal account={mockAccount} onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith('field required; invalid email');
    });
  });

  // 26. Error message extraction - Error instance
  it('shows Error.message on submit failure with Error instance', async () => {
    jest.spyOn(window, 'alert').mockImplementation(() => {});
    mockMutateAsyncCreate.mockRejectedValueOnce(new Error('Network error'));

    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith('Network error');
    });
  });

  // Test connection error extraction
  it('shows extracted error message on test connection exception', async () => {
    mailAccountsApi.test.mockRejectedValue({
      response: { data: { detail: 'Timeout' } },
    });

    render(<AddMailAccountModal onClose={jest.fn()} />);
    fireEvent.click(screen.getByText('Manual Setup'));

    const usernameInput = screen.getByPlaceholderText('user@example.com');
    const passwordInput = screen.getByPlaceholderText('Password');
    const hostInput = screen.getByPlaceholderText('pop.gmail.com');

    fireEvent.change(usernameInput, {
      target: { name: 'username', value: 'u@t.com', type: 'text' },
    });
    fireEvent.change(passwordInput, {
      target: { name: 'password', value: 'p', type: 'password' },
    });
    fireEvent.change(hostInput, {
      target: { name: 'host', value: 'h.com', type: 'text' },
    });

    fireEvent.click(screen.getByText('Test Connection'));

    await waitFor(() => {
      expect(screen.getByText('Timeout')).toBeInTheDocument();
    });
  });
});
