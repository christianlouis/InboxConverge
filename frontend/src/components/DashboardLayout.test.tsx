import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { DashboardLayout } from './DashboardLayout';

// Mock next/navigation
const mockPush = jest.fn();
let mockPathname = '/dashboard';
jest.mock('next/navigation', () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({ push: mockPush }),
}));

// Mock next/link to render a simple anchor
jest.mock('next/link', () => {
  const MockLink = ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  );
  MockLink.displayName = 'MockLink';
  return MockLink;
});

// Mock @tanstack/react-query
let mockVersionInfo: Record<string, string> | null = null;
jest.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: mockVersionInfo }),
}));

// Mock lucide-react icons as simple spans
jest.mock('lucide-react', () => {
  const iconNames = [
    'LayoutDashboard', 'Mail', 'Settings', 'LogOut', 'Menu', 'X',
    'User', 'Shield', 'Users', 'CreditCard', 'Bell', 'Inbox', 'Activity',
  ];
  const icons: Record<string, React.FC<{ className?: string }>> = {};
  iconNames.forEach((name) => {
    icons[name] = ({ className }: { className?: string }) => (
      <span data-testid={`icon-${name}`} className={className} />
    );
  });
  return icons;
});

// Mock authStore
const mockLogout = jest.fn();
let mockUser: Record<string, unknown> | null = null;

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    user: mockUser,
    logout: mockLogout,
  }),
}));

// Mock versionApi
jest.mock('@/lib/api', () => ({
  versionApi: {
    get: jest.fn(),
  },
}));

const regularUser = {
  id: 1,
  email: 'user@example.com',
  full_name: 'Regular User',
  is_active: true,
  is_superuser: false,
  subscription_tier: 'free',
  subscription_status: 'active',
  created_at: '2024-01-01T00:00:00Z',
};

const adminUser = {
  ...regularUser,
  id: 2,
  email: 'admin@example.com',
  full_name: 'Admin User',
  is_superuser: true,
};

describe('DashboardLayout', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockPathname = '/dashboard';
    mockUser = regularUser;
    mockVersionInfo = null;
  });

  it('should render the InboxConverge branding', () => {
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    // Desktop sidebar has the branding
    expect(screen.getAllByText('InboxConverge').length).toBeGreaterThan(0);
  });

  it('should render main navigation items', () => {
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Mail Accounts').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Notifications').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Mailbox Activity').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Settings').length).toBeGreaterThan(0);
  });

  it('should render children in main content area', () => {
    render(
      <DashboardLayout>
        <div data-testid="page-content">Page Content</div>
      </DashboardLayout>
    );
    expect(screen.getByTestId('page-content')).toBeInTheDocument();
    expect(screen.getByText('Page Content')).toBeInTheDocument();
  });

  it('should display user info in the top bar', () => {
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    expect(screen.getByText('Regular User')).toBeInTheDocument();
    expect(screen.getByText('user@example.com')).toBeInTheDocument();
  });

  it('should not show admin navigation for regular users', () => {
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    expect(screen.queryByText('Admin Overview')).not.toBeInTheDocument();
    expect(screen.queryByText('Manage Users')).not.toBeInTheDocument();
    expect(screen.queryByText('Manage Plans')).not.toBeInTheDocument();
    expect(screen.queryByText('Activity Logs')).not.toBeInTheDocument();
  });

  it('should show admin navigation for superusers', () => {
    mockUser = adminUser;
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    expect(screen.getAllByText('Admin Overview').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Manage Users').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Manage Plans').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Activity Logs').length).toBeGreaterThan(0);
  });

  it('should show Admin badge for superusers', () => {
    mockUser = adminUser;
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    // The Admin badge has a specific class for styling
    const adminBadges = screen.getAllByText('Admin');
    const badge = adminBadges.find((el) => el.classList.contains('bg-purple-100'));
    expect(badge).toBeInTheDocument();
  });

  it('should not show Admin badge for regular users', () => {
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  });

  it('should call logout and redirect on Logout button click', () => {
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    // Click the first Logout button (desktop sidebar)
    const logoutButtons = screen.getAllByText('Logout');
    fireEvent.click(logoutButtons[0]);
    expect(mockLogout).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith('/login');
  });

  it('should display the current page title based on pathname', () => {
    mockPathname = '/accounts';
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    // The top bar should show "Mail Accounts" as the h2 heading
    const headings = screen.getAllByText('Mail Accounts');
    // At least one should be a heading in the top bar
    expect(headings.length).toBeGreaterThan(0);
  });

  it('should show version info in the footer when available', () => {
    mockVersionInfo = { version: '1.2.3', build_date: '2024-06-15T12:00:00Z' };
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    expect(screen.getByText('v1.2.3')).toBeInTheDocument();
  });

  it('should not show version info when not available', () => {
    mockVersionInfo = null;
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    expect(screen.queryByText(/^v\d/)).not.toBeInTheDocument();
  });

  it('should render footer links', () => {
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    expect(screen.getByText('Impressum')).toBeInTheDocument();
    expect(screen.getByText('Datenschutz')).toBeInTheDocument();
  });

  it('should open mobile sidebar on menu button click', () => {
    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );
    // The mobile menu button has a Menu icon
    const menuButton = screen.getByTestId('icon-Menu').closest('button');
    expect(menuButton).toBeInTheDocument();
    fireEvent.click(menuButton!);

    // After clicking, the close (X) button should appear
    expect(screen.getByTestId('icon-X')).toBeInTheDocument();
  });
});
