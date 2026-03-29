import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthGuard } from './AuthGuard';

// Mock next/navigation
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock userApi
const mockGetCurrentUser = jest.fn();
jest.mock('@/lib/api', () => ({
  userApi: {
    getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
  },
}));

// Mock authStore
const mockSetUser = jest.fn();
const mockSetLoading = jest.fn();
let mockUser: Record<string, unknown> | null = null;
let mockIsLoading = true;

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    user: mockUser,
    isLoading: mockIsLoading,
    setUser: mockSetUser,
    setLoading: mockSetLoading,
  }),
}));

const mockUserData = {
  id: 1,
  email: 'test@example.com',
  full_name: 'Test User',
  is_active: true,
  is_superuser: false,
  subscription_tier: 'free',
  subscription_status: 'active',
  created_at: '2024-01-01T00:00:00Z',
};

describe('AuthGuard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    mockUser = null;
    mockIsLoading = true;
  });

  it('should show loading spinner while isLoading is true', () => {
    mockIsLoading = true;
    localStorage.setItem('access_token', 'test-token');
    mockGetCurrentUser.mockResolvedValue(mockUserData);

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    // Should show spinner (via animate-spin class)
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('should render children when user is authenticated', () => {
    mockUser = mockUserData;
    mockIsLoading = false;
    localStorage.setItem('access_token', 'test-token');

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('should render nothing when not loading and no user', () => {
    mockUser = null;
    mockIsLoading = false;

    const { container } = render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    expect(container.innerHTML).toBe('');
  });

  it('should redirect to /login when no token exists', async () => {
    // No token in localStorage
    mockGetCurrentUser.mockResolvedValue(mockUserData);

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });

  it('should fetch user data when token exists', async () => {
    localStorage.setItem('access_token', 'valid-token');
    mockGetCurrentUser.mockResolvedValue(mockUserData);

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    await waitFor(() => {
      expect(mockGetCurrentUser).toHaveBeenCalled();
      expect(mockSetUser).toHaveBeenCalledWith(mockUserData);
    });
  });

  it('should redirect to /login when API call fails', async () => {
    localStorage.setItem('access_token', 'expired-token');
    mockGetCurrentUser.mockRejectedValue(new Error('Unauthorized'));

    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    await waitFor(() => {
      expect(mockSetUser).toHaveBeenCalledWith(null);
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });
});
