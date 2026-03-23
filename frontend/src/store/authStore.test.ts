import { describe, it, expect, beforeEach } from 'bun:test';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
});

// Import the actual store
import { useAuthStore } from './authStore';

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear();
    // Reset store state
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,
    });
  });

  it('should have initial state', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(true);
  });

  it('should set user and update isAuthenticated and isLoading', () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      full_name: 'Test User',
      is_active: true,
      subscription_tier: 'free',
      subscription_status: 'active',
      created_at: new Date().toISOString()
    };

    useAuthStore.getState().setUser(mockUser);

    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
  });

  it('should clear user on setUser(null)', () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      full_name: 'Test User',
      is_active: true,
      subscription_tier: 'free',
      subscription_status: 'active',
      created_at: new Date().toISOString()
    };
    useAuthStore.getState().setUser(mockUser);

    useAuthStore.getState().setUser(null);

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('should set token and update isAuthenticated', () => {
    const mockToken = 'fake-token';

    useAuthStore.getState().setToken(mockToken);

    const state = useAuthStore.getState();
    expect(state.token).toBe(mockToken);
    expect(state.isAuthenticated).toBe(true);
    expect(localStorage.getItem('access_token')).toBe(mockToken);
  });

  it('should update loading state', () => {
    useAuthStore.getState().setLoading(false);
    expect(useAuthStore.getState().isLoading).toBe(false);

    useAuthStore.getState().setLoading(true);
    expect(useAuthStore.getState().isLoading).toBe(true);
  });

  it('should logout and clear localStorage', () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      full_name: 'Test User',
      is_active: true,
      subscription_tier: 'free',
      subscription_status: 'active',
      created_at: new Date().toISOString()
    };
    localStorage.setItem('access_token', 'fake-token');
    localStorage.setItem('user', JSON.stringify(mockUser));

    useAuthStore.getState().setUser(mockUser);

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull(); // Note: logout should also clear token in state
    expect(state.isAuthenticated).toBe(false);
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
  });
});
