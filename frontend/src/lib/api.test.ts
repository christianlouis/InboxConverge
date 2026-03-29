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
// eslint-disable-next-line @typescript-eslint/no-require-imports
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

// ── API Object Tests ────────────────────────────────────────────────────

/* eslint-disable @typescript-eslint/no-require-imports */
const {
  authApi,
  userApi,
  mailAccountsApi,
  processingRunsApi,
  gmailApi,
  smtpApi,
  adminApi,
  notificationsApi,
  adminNotificationsApi,
  versionApi,
} = require('./api');

// ── authApi ─────────────────────────────────────────────────────────────

describe('authApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('login should post form data to /auth/login', async () => {
    const tokenData = { access_token: 'tok', refresh_token: 'ref', token_type: 'bearer' };
    mockAxiosInstance.post.mockResolvedValue({ data: tokenData });

    const result = await authApi.login({ username: 'u@test.com', password: 'pw' });

    expect(mockAxiosInstance.post).toHaveBeenCalledWith(
      '/auth/login',
      expect.any(URLSearchParams),
      expect.objectContaining({
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
    );
    const formData: URLSearchParams = mockAxiosInstance.post.mock.calls[0][1];
    expect(formData.get('username')).toBe('u@test.com');
    expect(formData.get('password')).toBe('pw');
    expect(result).toEqual(tokenData);
  });

  it('register should post user data to /auth/register', async () => {
    const user = { id: 1, email: 'u@test.com', full_name: 'Test' };
    mockAxiosInstance.post.mockResolvedValue({ data: user });

    const result = await authApi.register({ email: 'u@test.com', password: 'pw', full_name: 'Test' });

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/register', {
      email: 'u@test.com',
      password: 'pw',
      full_name: 'Test',
    });
    expect(result).toEqual(user);
  });

  it('googleAuth should post code and redirect_uri to /auth/google', async () => {
    const tokenData = { access_token: 'tok', refresh_token: 'ref', token_type: 'bearer' };
    mockAxiosInstance.post.mockResolvedValue({ data: tokenData });

    const result = await authApi.googleAuth('code123', 'http://redirect');

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/google', {
      code: 'code123',
      redirect_uri: 'http://redirect',
    });
    expect(result).toEqual(tokenData);
  });

  it('getGoogleAuthUrl should get authorization URL with redirect_uri param', async () => {
    mockAxiosInstance.get.mockResolvedValue({
      data: { authorization_url: 'https://google.com/auth' },
    });

    const result = await authApi.getGoogleAuthUrl('http://redirect');

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/auth/google/authorize-url', {
      params: { redirect_uri: 'http://redirect' },
    });
    expect(result).toBe('https://google.com/auth');
  });
});

// ── userApi ─────────────────────────────────────────────────────────────

describe('userApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('getCurrentUser should get /users/me', async () => {
    const user = { id: 1, email: 'u@test.com' };
    mockAxiosInstance.get.mockResolvedValue({ data: user });

    const result = await userApi.getCurrentUser();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/users/me');
    expect(result).toEqual(user);
  });

  it('updateProfile should put data to /users/me', async () => {
    const user = { id: 1, email: 'new@test.com', full_name: 'New' };
    mockAxiosInstance.put.mockResolvedValue({ data: user });

    const result = await userApi.updateProfile({ full_name: 'New', email: 'new@test.com' });

    expect(mockAxiosInstance.put).toHaveBeenCalledWith('/users/me', {
      full_name: 'New',
      email: 'new@test.com',
    });
    expect(result).toEqual(user);
  });
});

// ── mailAccountsApi ─────────────────────────────────────────────────────

describe('mailAccountsApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('list should get /mail-accounts', async () => {
    const accounts = [{ id: 1, name: 'acc1' }];
    mockAxiosInstance.get.mockResolvedValue({ data: accounts });

    const result = await mailAccountsApi.list();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/mail-accounts');
    expect(result).toEqual(accounts);
  });

  it('create should post data to /mail-accounts', async () => {
    const account = { id: 1, name: 'new' };
    const createData = {
      name: 'new',
      email_address: 'a@b.com',
      protocol: 'imap',
      host: 'imap.b.com',
      port: 993,
      use_ssl: true,
      username: 'a@b.com',
      password: 'secret',
      forward_to: 'c@d.com',
    };
    mockAxiosInstance.post.mockResolvedValue({ data: account });

    const result = await mailAccountsApi.create(createData);

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/mail-accounts', createData);
    expect(result).toEqual(account);
  });

  it('update should put data to /mail-accounts/:id', async () => {
    const account = { id: 5, name: 'updated' };
    mockAxiosInstance.put.mockResolvedValue({ data: account });

    const result = await mailAccountsApi.update(5, { name: 'updated' });

    expect(mockAxiosInstance.put).toHaveBeenCalledWith('/mail-accounts/5', { name: 'updated' });
    expect(result).toEqual(account);
  });

  it('toggle should patch /mail-accounts/:id/toggle', async () => {
    const account = { id: 3, is_enabled: false };
    mockAxiosInstance.patch.mockResolvedValue({ data: account });

    const result = await mailAccountsApi.toggle(3);

    expect(mockAxiosInstance.patch).toHaveBeenCalledWith('/mail-accounts/3/toggle');
    expect(result).toEqual(account);
  });

  it('pullNow should post to /mail-accounts/:id/pull-now', async () => {
    const msg = { message: 'Pull initiated' };
    mockAxiosInstance.post.mockResolvedValue({ data: msg });

    const result = await mailAccountsApi.pullNow(7);

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/mail-accounts/7/pull-now');
    expect(result).toEqual(msg);
  });

  it('delete should delete /mail-accounts/:id', async () => {
    mockAxiosInstance.delete.mockResolvedValue({});

    await mailAccountsApi.delete(4);

    expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/mail-accounts/4');
  });

  it('test should post config to /mail-accounts/test', async () => {
    const response = { success: true, message: 'OK' };
    const config = {
      host: 'imap.test.com',
      port: 993,
      protocol: 'imap',
      username: 'user',
      password: 'pass',
      use_ssl: true,
    };
    mockAxiosInstance.post.mockResolvedValue({ data: response });

    const result = await mailAccountsApi.test(config);

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/mail-accounts/test', config);
    expect(result).toEqual(response);
  });

  it('testExisting should post to /mail-accounts/:id/test', async () => {
    const response = { success: true, message: 'Connected' };
    mockAxiosInstance.post.mockResolvedValue({ data: response });

    const result = await mailAccountsApi.testExisting(10);

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/mail-accounts/10/test');
    expect(result).toEqual(response);
  });

  it('autoDetect should post email address to /mail-accounts/auto-detect', async () => {
    const response = { success: true, suggestions: [{ protocol: 'imap', host: 'imap.x.com' }] };
    mockAxiosInstance.post.mockResolvedValue({ data: response });

    const result = await mailAccountsApi.autoDetect('user@x.com');

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/mail-accounts/auto-detect', {
      email_address: 'user@x.com',
    });
    expect(result).toEqual(response);
  });
});

// ── processingRunsApi ───────────────────────────────────────────────────

describe('processingRunsApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('list should get /processing-runs with params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const params = { page: 1, page_size: 20, status: 'completed' };
    const result = await processingRunsApi.list(params);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/processing-runs', { params });
    expect(result).toEqual(paginated);
  });

  it('list should work without params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const result = await processingRunsApi.list();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/processing-runs', { params: undefined });
    expect(result).toEqual(paginated);
  });

  it('get should get /processing-runs/:id', async () => {
    const run = { id: 42, status: 'completed' };
    mockAxiosInstance.get.mockResolvedValue({ data: run });

    const result = await processingRunsApi.get(42);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/processing-runs/42');
    expect(result).toEqual(run);
  });

  it('getLogs should get /processing-runs/:id/logs with params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 50, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const params = { page: 2, page_size: 50 };
    const result = await processingRunsApi.getLogs(42, params);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/processing-runs/42/logs', { params });
    expect(result).toEqual(paginated);
  });

  it('getLogs should work without params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const result = await processingRunsApi.getLogs(10);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/processing-runs/10/logs', {
      params: undefined,
    });
    expect(result).toEqual(paginated);
  });

  it('listForAccount should get /mail-accounts/:id/processing-runs with params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const params = { page: 1, page_size: 20, status: 'failed' };
    const result = await processingRunsApi.listForAccount(5, params);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/mail-accounts/5/processing-runs', {
      params,
    });
    expect(result).toEqual(paginated);
  });

  it('listLogsForAccount should get /mail-accounts/:id/logs with params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const params = { page: 1, page_size: 20, level: 'error' };
    const result = await processingRunsApi.listLogsForAccount(3, params);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/mail-accounts/3/logs', { params });
    expect(result).toEqual(paginated);
  });
});

// ── gmailApi ────────────────────────────────────────────────────────────

describe('gmailApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('getAuthorizeUrl should get /providers/gmail/authorize-url with redirect_uri', async () => {
    mockAxiosInstance.get.mockResolvedValue({
      data: { authorization_url: 'https://accounts.google.com/o/oauth2' },
    });

    const result = await gmailApi.getAuthorizeUrl('http://localhost/callback');

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/providers/gmail/authorize-url', {
      params: { redirect_uri: 'http://localhost/callback' },
    });
    expect(result).toBe('https://accounts.google.com/o/oauth2');
  });

  it('saveCallback should post code and redirect_uri to /providers/gmail/callback', async () => {
    const credential = { id: 1, gmail_email: 'test@gmail.com', is_valid: true };
    mockAxiosInstance.post.mockResolvedValue({ data: credential });

    const result = await gmailApi.saveCallback('authcode', 'http://localhost/callback');

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/providers/gmail/callback', {
      code: 'authcode',
      redirect_uri: 'http://localhost/callback',
    });
    expect(result).toEqual(credential);
  });

  it('getCredential should get /providers/gmail-credential', async () => {
    const credential = { id: 1, gmail_email: 'test@gmail.com', is_valid: true };
    mockAxiosInstance.get.mockResolvedValue({ data: credential });

    const result = await gmailApi.getCredential();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/providers/gmail-credential');
    expect(result).toEqual(credential);
  });

  it('disconnect should delete /providers/gmail-credential', async () => {
    mockAxiosInstance.delete.mockResolvedValue({});

    await gmailApi.disconnect();

    expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/providers/gmail-credential');
  });

  it('sendDebugEmail should post to /providers/gmail/debug-email', async () => {
    const response = {
      message: 'Sent',
      message_id: 'msg1',
      thread_id: 'thr1',
      label_ids: ['INBOX'],
    };
    mockAxiosInstance.post.mockResolvedValue({ data: response });

    const result = await gmailApi.sendDebugEmail();

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/providers/gmail/debug-email');
    expect(result).toEqual(response);
  });

  it('updateImportLabels should put label templates to /providers/gmail-credential/labels', async () => {
    const credential = { id: 1, import_label_templates: ['Label1'] };
    mockAxiosInstance.put.mockResolvedValue({ data: credential });

    const result = await gmailApi.updateImportLabels(['Label1']);

    expect(mockAxiosInstance.put).toHaveBeenCalledWith('/providers/gmail-credential/labels', {
      import_label_templates: ['Label1'],
    });
    expect(result).toEqual(credential);
  });
});

// ── smtpApi ─────────────────────────────────────────────────────────────

describe('smtpApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('get should get /users/smtp-config', async () => {
    const config = { id: 1, host: 'smtp.test.com', port: 587 };
    mockAxiosInstance.get.mockResolvedValue({ data: config });

    const result = await smtpApi.get();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/users/smtp-config');
    expect(result).toEqual(config);
  });

  it('save should put config to /users/smtp-config', async () => {
    const config = { id: 1, host: 'smtp.test.com', port: 587 };
    const saveData = { host: 'smtp.test.com', port: 587, username: 'user', use_tls: true };
    mockAxiosInstance.put.mockResolvedValue({ data: config });

    const result = await smtpApi.save(saveData);

    expect(mockAxiosInstance.put).toHaveBeenCalledWith('/users/smtp-config', saveData);
    expect(result).toEqual(config);
  });

  it('remove should delete /users/smtp-config', async () => {
    mockAxiosInstance.delete.mockResolvedValue({});

    await smtpApi.remove();

    expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/users/smtp-config');
  });
});

// ── adminApi ────────────────────────────────────────────────────────────

describe('adminApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('getStats should get /admin/stats', async () => {
    const stats = { total_users: 10, total_mail_accounts: 20, total_processing_runs: 100 };
    mockAxiosInstance.get.mockResolvedValue({ data: stats });

    const result = await adminApi.getStats();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/stats');
    expect(result).toEqual(stats);
  });

  it('listUsers should get /admin/users with skip and limit', async () => {
    const users = [{ id: 1, email: 'a@b.com' }];
    mockAxiosInstance.get.mockResolvedValue({ data: users });

    const result = await adminApi.listUsers(10, 50);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/users', {
      params: { skip: 10, limit: 50 },
    });
    expect(result).toEqual(users);
  });

  it('listUsers should use defaults for skip and limit', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: [] });

    await adminApi.listUsers();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/users', {
      params: { skip: 0, limit: 100 },
    });
  });

  it('getUser should get /admin/users/:id', async () => {
    const user = { id: 5, email: 'u@t.com' };
    mockAxiosInstance.get.mockResolvedValue({ data: user });

    const result = await adminApi.getUser(5);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/users/5');
    expect(result).toEqual(user);
  });

  it('updateUser should put data to /admin/users/:id', async () => {
    const user = { id: 5, is_active: false };
    mockAxiosInstance.put.mockResolvedValue({ data: user });

    const result = await adminApi.updateUser(5, { is_active: false });

    expect(mockAxiosInstance.put).toHaveBeenCalledWith('/admin/users/5', { is_active: false });
    expect(result).toEqual(user);
  });

  it('deleteUser should delete /admin/users/:id', async () => {
    mockAxiosInstance.delete.mockResolvedValue({});

    await adminApi.deleteUser(5);

    expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/admin/users/5');
  });

  it('listPlans should get /admin/plans', async () => {
    const plans = [{ id: 1, tier: 'free' }];
    mockAxiosInstance.get.mockResolvedValue({ data: plans });

    const result = await adminApi.listPlans();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/plans');
    expect(result).toEqual(plans);
  });

  it('createPlan should post data to /admin/plans', async () => {
    const plan = { id: 1, tier: 'pro', name: 'Pro Plan' };
    const createData = {
      tier: 'pro',
      name: 'Pro Plan',
      price_monthly: 9.99,
      max_mail_accounts: 10,
      max_emails_per_day: 1000,
      check_interval_minutes: 5,
      support_level: 'email',
      is_active: true,
    };
    mockAxiosInstance.post.mockResolvedValue({ data: plan });

    const result = await adminApi.createPlan(createData);

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/plans', createData);
    expect(result).toEqual(plan);
  });

  it('updatePlan should put data to /admin/plans/:id', async () => {
    const plan = { id: 2, name: 'Updated Plan' };
    mockAxiosInstance.put.mockResolvedValue({ data: plan });

    const result = await adminApi.updatePlan(2, { name: 'Updated Plan' });

    expect(mockAxiosInstance.put).toHaveBeenCalledWith('/admin/plans/2', { name: 'Updated Plan' });
    expect(result).toEqual(plan);
  });

  it('deletePlan should delete /admin/plans/:id', async () => {
    mockAxiosInstance.delete.mockResolvedValue({});

    await adminApi.deletePlan(3);

    expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/admin/plans/3');
  });

  it('listProcessingRuns should get /admin/processing-runs with params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const params = { page: 1, page_size: 20, user_id: 5 };
    const result = await adminApi.listProcessingRuns(params);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/processing-runs', { params });
    expect(result).toEqual(paginated);
  });

  it('listProcessingRuns should work without params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const result = await adminApi.listProcessingRuns();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/processing-runs', {
      params: undefined,
    });
    expect(result).toEqual(paginated);
  });

  it('listProcessingLogs should get /admin/processing-logs with params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const params = { page: 1, page_size: 20, level: 'error' };
    const result = await adminApi.listProcessingLogs(params);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/processing-logs', { params });
    expect(result).toEqual(paginated);
  });

  it('listProcessingLogs should work without params', async () => {
    const paginated = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    mockAxiosInstance.get.mockResolvedValue({ data: paginated });

    const result = await adminApi.listProcessingLogs();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/processing-logs', {
      params: undefined,
    });
    expect(result).toEqual(paginated);
  });
});

// ── notificationsApi ────────────────────────────────────────────────────

describe('notificationsApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('list should get /notifications', async () => {
    const configs = [{ id: 1, name: 'Notif 1' }];
    mockAxiosInstance.get.mockResolvedValue({ data: configs });

    const result = await notificationsApi.list();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/notifications');
    expect(result).toEqual(configs);
  });

  it('create should post data to /notifications', async () => {
    const config = { id: 1, name: 'New Notif', channel: 'email' };
    const createData = { name: 'New Notif', channel: 'email' };
    mockAxiosInstance.post.mockResolvedValue({ data: config });

    const result = await notificationsApi.create(createData);

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/notifications', createData);
    expect(result).toEqual(config);
  });

  it('update should put data to /notifications/:id', async () => {
    const config = { id: 2, name: 'Updated' };
    mockAxiosInstance.put.mockResolvedValue({ data: config });

    const result = await notificationsApi.update(2, { name: 'Updated' });

    expect(mockAxiosInstance.put).toHaveBeenCalledWith('/notifications/2', { name: 'Updated' });
    expect(result).toEqual(config);
  });

  it('delete should delete /notifications/:id', async () => {
    mockAxiosInstance.delete.mockResolvedValue({});

    await notificationsApi.delete(3);

    expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/notifications/3');
  });

  it('test should post apprise_url to /notifications/test', async () => {
    const response = { success: true, message: 'Test sent' };
    mockAxiosInstance.post.mockResolvedValue({ data: response });

    const result = await notificationsApi.test('apprise://slack/webhook');

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/notifications/test', {
      apprise_url: 'apprise://slack/webhook',
    });
    expect(result).toEqual(response);
  });
});

// ── adminNotificationsApi ───────────────────────────────────────────────

describe('adminNotificationsApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('list should get /admin/notifications', async () => {
    const configs = [{ id: 1, name: 'Admin Notif' }];
    mockAxiosInstance.get.mockResolvedValue({ data: configs });

    const result = await adminNotificationsApi.list();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/notifications');
    expect(result).toEqual(configs);
  });

  it('create should post data to /admin/notifications', async () => {
    const config = { id: 1, name: 'Admin Notif', apprise_url: 'apprise://test' };
    const createData = { name: 'Admin Notif', apprise_url: 'apprise://test' };
    mockAxiosInstance.post.mockResolvedValue({ data: config });

    const result = await adminNotificationsApi.create(createData);

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/notifications', createData);
    expect(result).toEqual(config);
  });

  it('update should put data to /admin/notifications/:id', async () => {
    const config = { id: 2, name: 'Updated Admin' };
    mockAxiosInstance.put.mockResolvedValue({ data: config });

    const result = await adminNotificationsApi.update(2, { name: 'Updated Admin' });

    expect(mockAxiosInstance.put).toHaveBeenCalledWith('/admin/notifications/2', {
      name: 'Updated Admin',
    });
    expect(result).toEqual(config);
  });

  it('delete should delete /admin/notifications/:id', async () => {
    mockAxiosInstance.delete.mockResolvedValue({});

    await adminNotificationsApi.delete(4);

    expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/admin/notifications/4');
  });

  it('test should post apprise_url to /admin/notifications/test', async () => {
    const response = { success: true, message: 'Admin test sent' };
    mockAxiosInstance.post.mockResolvedValue({ data: response });

    const result = await adminNotificationsApi.test('apprise://discord/webhook');

    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/notifications/test', {
      apprise_url: 'apprise://discord/webhook',
    });
    expect(result).toEqual(response);
  });
});

// ── versionApi ──────────────────────────────────────────────────────────

describe('versionApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('get should get /version', async () => {
    const versionInfo = { version: '1.2.3', build_date: '2024-01-01' };
    mockAxiosInstance.get.mockResolvedValue({ data: versionInfo });

    const result = await versionApi.get();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/version');
    expect(result).toEqual(versionInfo);
  });
});
