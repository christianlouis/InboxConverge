/**
 * Tests for the Axios API instance configuration — interceptors and
 * default headers.  We use jest.mock to stub axios.create so we can
 * inspect the interceptor callbacks that api.ts registers.
 */

// Capture interceptor callbacks registered by api.ts
type InterceptorFn = (config: Record<string, unknown>) => unknown;
type ErrorFn = (error: unknown) => unknown;

let requestInterceptor: InterceptorFn | null = null;
let responseSuccessInterceptor: InterceptorFn | null = null;
let responseErrorInterceptor: ErrorFn | null = null;

const mockCreate = jest.fn();

const mockAxiosInstance = {
  interceptors: {
    request: {
      use: jest.fn((fn: InterceptorFn) => {
        requestInterceptor = fn;
      }),
    },
    response: {
      use: jest.fn((successFn: InterceptorFn, errorFn: ErrorFn) => {
        responseSuccessInterceptor = successFn;
        responseErrorInterceptor = errorFn;
      }),
    },
  },
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  patch: jest.fn(),
  delete: jest.fn(),
};

mockCreate.mockReturnValue(mockAxiosInstance);

jest.mock('axios', () => ({
  __esModule: true,
  default: {
    create: mockCreate,
  },
}));

// Force module initialization to capture interceptors
require('./api');

describe('API module setup', () => {
  it('should create an axios instance with correct baseURL', () => {
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        baseURL: '/api/v1',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    );
  });

  it('should register request and response interceptors', () => {
    expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();
    expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled();
  });
});

describe('Request interceptor', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should attach Authorization header when access_token exists', () => {
    localStorage.setItem('access_token', 'test-jwt-token');
    const config = { headers: {} as Record<string, string> };
    const result = requestInterceptor!(config) as typeof config;
    expect(result.headers.Authorization).toBe('Bearer test-jwt-token');
  });

  it('should not attach Authorization header when no token exists', () => {
    const config = { headers: {} as Record<string, string> };
    const result = requestInterceptor!(config) as typeof config;
    expect(result.headers.Authorization).toBeUndefined();
  });
});

describe('Response interceptor', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should pass through successful responses', () => {
    const response = { data: { ok: true }, status: 200 };
    const result = responseSuccessInterceptor!(response);
    expect(result).toBe(response);
  });

  it('should clear auth state on 401', async () => {
    localStorage.setItem('access_token', 'expired-token');
    localStorage.setItem('user', '{"id":1}');

    const error = { response: { status: 401 } };
    await expect(responseErrorInterceptor!(error)).rejects.toBe(error);

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
  });

  it('should not clear auth state for non-401 errors', async () => {
    localStorage.setItem('access_token', 'valid-token');

    const error = { response: { status: 500 } };
    await expect(responseErrorInterceptor!(error)).rejects.toBe(error);

    expect(localStorage.getItem('access_token')).toBe('valid-token');
  });

  it('should reject with the error for non-401 errors', async () => {
    const error = { response: { status: 403 } };
    await expect(responseErrorInterceptor!(error)).rejects.toBe(error);
  });

  it('should handle errors without a response object', async () => {
    const error = new Error('Network error');
    await expect(responseErrorInterceptor!(error)).rejects.toBe(error);
  });
});
