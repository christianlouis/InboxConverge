import axios from "axios";

const api = axios.create({
  baseURL: `/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach auth token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle 401 responses by clearing auth state
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ── Types ───────────────────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  subscription_tier: string;
  subscription_status: string;
  created_at: string;
  google_id?: string | null;
  oauth_provider?: string | null;
  stripe_customer_id?: string | null;
  subscription_expires_at?: string | null;
  last_login_at?: string | null;
}

export interface MailAccount {
  id: number;
  user_id: number;
  name: string;
  email_address: string;
  protocol: string;
  host: string;
  port: number;
  use_ssl: boolean;
  use_tls: boolean;
  username: string;
  forward_to: string;
  delivery_method: string;
  is_enabled: boolean;
  check_interval_minutes: number;
  max_emails_per_check: number;
  delete_after_forward: boolean;
  status: string;
  provider_name?: string | null;
  auto_detected: boolean;
  total_emails_processed: number;
  total_emails_failed: number;
  last_check_at?: string | null;
  last_successful_check_at?: string | null;
  last_error_at?: string | null;
  last_error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MailAccountCreate {
  name: string;
  email_address: string;
  protocol: string;
  host: string;
  port: number;
  use_ssl: boolean;
  use_tls?: boolean;
  username: string;
  password: string;
  forward_to: string;
  delivery_method?: string;
  is_enabled?: boolean;
  check_interval_minutes?: number;
  max_emails_per_check?: number;
  delete_after_forward?: boolean;
}

export interface MailAccountUpdate {
  name?: string;
  email_address?: string;
  protocol?: string;
  host?: string;
  port?: number;
  use_ssl?: boolean;
  use_tls?: boolean;
  username?: string;
  password?: string;
  forward_to?: string;
  delivery_method?: string;
  is_enabled?: boolean;
  check_interval_minutes?: number;
  max_emails_per_check?: number;
  delete_after_forward?: boolean;
}

export interface ProcessingRun {
  id: number;
  mail_account_id: number;
  started_at: string;
  completed_at?: string | null;
  duration_seconds?: number | null;
  emails_fetched: number;
  emails_forwarded: number;
  emails_failed: number;
  status: string;
  error_message?: string | null;
  account_name?: string | null;
  account_email?: string | null;
}

export interface ProcessingLog {
  id: number;
  timestamp: string;
  level: string;
  message: string;
  email_subject?: string | null;
  email_from?: string | null;
  success: boolean;
  mail_account_id: number;
  processing_run_id?: number | null;
  email_size_bytes?: number | null;
  error_details?: Record<string, unknown> | null;
}

export interface PaginatedProcessingRuns {
  items: ProcessingRun[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PaginatedProcessingLogs {
  items: ProcessingLog[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AdminProcessingRun extends ProcessingRun {
  user_id?: number | null;
  user_email?: string | null;
}

export interface AdminProcessingLog extends ProcessingLog {
  user_id: number;
  user_email?: string | null;
}

export interface PaginatedAdminRuns {
  items: AdminProcessingRun[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PaginatedAdminLogsResponse {
  items: AdminProcessingLog[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AutoDetectSuggestion {
  protocol?: string;
  host?: string;
  port?: number;
  use_ssl?: boolean;
  [key: string]: unknown;
}

export interface GmailCredential {
  id: number;
  user_id: number;
  gmail_email: string;
  is_valid: boolean;
  import_label_templates: string[];
  default_import_label_templates: string[];
  last_verified_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GmailDebugEmailResponse {
  message: string;
  message_id: string | null;
  thread_id: string | null;
  label_ids: string[];
}

export interface UserSmtpConfig {
  id: number;
  user_id: number;
  host: string;
  port: number;
  username: string;
  use_tls: boolean;
  has_password: boolean;
  created_at: string;
  updated_at: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user?: User;
}

// ── Auth API ────────────────────────────────────────────────────────────

export const authApi = {
  async login(credentials: {
    username: string;
    password: string;
  }): Promise<TokenResponse> {
    const formData = new URLSearchParams();
    formData.append("username", credentials.username);
    formData.append("password", credentials.password);

    const response = await api.post<TokenResponse>("/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return response.data;
  },

  async register(data: {
    email: string;
    password: string;
    full_name?: string;
  }): Promise<User> {
    const response = await api.post<User>("/auth/register", data);
    return response.data;
  },

  async googleAuth(
    code: string,
    redirectUri: string
  ): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>("/auth/google", {
      code,
      redirect_uri: redirectUri,
    });
    return response.data;
  },

  async getGoogleAuthUrl(redirectUri: string): Promise<string> {
    const response = await api.get<{ authorization_url: string }>(
      "/auth/google/authorize-url",
      { params: { redirect_uri: redirectUri } }
    );
    return response.data.authorization_url;
  },
};

// ── User API ────────────────────────────────────────────────────────────

export const userApi = {
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/users/me");
    return response.data;
  },

  async updateProfile(data: { full_name?: string; email?: string }): Promise<User> {
    const response = await api.put<User>("/users/me", data);
    return response.data;
  },
};

// ── Mail Accounts API ───────────────────────────────────────────────────

export const mailAccountsApi = {
  async list(): Promise<MailAccount[]> {
    const response = await api.get<MailAccount[]>("/mail-accounts");
    return response.data;
  },

  async create(data: MailAccountCreate): Promise<MailAccount> {
    const response = await api.post<MailAccount>("/mail-accounts", data);
    return response.data;
  },

  async update(
    id: number,
    data: MailAccountUpdate
  ): Promise<MailAccount> {
    const response = await api.put<MailAccount>(`/mail-accounts/${id}`, data);
    return response.data;
  },

  async toggle(id: number): Promise<MailAccount> {
    const response = await api.patch<MailAccount>(`/mail-accounts/${id}/toggle`);
    return response.data;
  },

  async pullNow(id: number): Promise<{ message: string }> {
    const response = await api.post<{ message: string }>(`/mail-accounts/${id}/pull-now`);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/mail-accounts/${id}`);
  },

  async test(config: {
    host: string;
    port: number;
    protocol: string;
    username: string;
    password: string;
    use_ssl?: boolean;
    use_tls?: boolean;
  }): Promise<{ success: boolean; message: string }> {
    const response = await api.post<{ success: boolean; message: string }>(
      "/mail-accounts/test",
      config
    );
    return response.data;
  },

  async testExisting(accountId: number): Promise<{ success: boolean; message: string }> {
    const response = await api.post<{ success: boolean; message: string }>(
      `/mail-accounts/${accountId}/test`
    );
    return response.data;
  },

  async autoDetect(
    emailAddress: string
  ): Promise<{ success: boolean; suggestions: AutoDetectSuggestion[] }> {
    const response = await api.post<{
      success: boolean;
      suggestions: AutoDetectSuggestion[];
    }>("/mail-accounts/auto-detect", { email_address: emailAddress });
    return response.data;
  },
};

// ── Processing Runs API ─────────────────────────────────────────────────

export const processingRunsApi = {
  async list(params?: {
    page?: number;
    page_size?: number;
    account_id?: number;
    status?: string;
    has_emails?: boolean;
  }): Promise<PaginatedProcessingRuns> {
    const response = await api.get<PaginatedProcessingRuns>("/processing-runs", {
      params,
    });
    return response.data;
  },

  async get(runId: number): Promise<ProcessingRun> {
    const response = await api.get<ProcessingRun>(`/processing-runs/${runId}`);
    return response.data;
  },

  async getLogs(
    runId: number,
    params?: { page?: number; page_size?: number }
  ): Promise<PaginatedProcessingLogs> {
    const response = await api.get<PaginatedProcessingLogs>(
      `/processing-runs/${runId}/logs`,
      { params }
    );
    return response.data;
  },

  async listForAccount(
    accountId: number,
    params?: { page?: number; page_size?: number; status?: string; has_emails?: boolean }
  ): Promise<PaginatedProcessingRuns> {
    const response = await api.get<PaginatedProcessingRuns>(
      `/mail-accounts/${accountId}/processing-runs`,
      { params }
    );
    return response.data;
  },

  async listLogsForAccount(
    accountId: number,
    params?: { page?: number; page_size?: number; level?: string }
  ): Promise<PaginatedProcessingLogs> {
    const response = await api.get<PaginatedProcessingLogs>(
      `/mail-accounts/${accountId}/logs`,
      { params }
    );
    return response.data;
  },
};

// ── Gmail API ───────────────────────────────────────────────────────────

export const gmailApi = {
  /** Returns the Google OAuth2 URL the user should be redirected to. */
  async getAuthorizeUrl(redirectUri: string): Promise<string> {
    const response = await api.get<{ authorization_url: string }>(
      '/providers/gmail/authorize-url',
      { params: { redirect_uri: redirectUri } }
    );
    return response.data.authorization_url;
  },

  /** Exchange an OAuth2 code for Gmail tokens and persist them. */
  async saveCallback(code: string, redirectUri: string): Promise<GmailCredential> {
    const response = await api.post<GmailCredential>('/providers/gmail/callback', {
      code,
      redirect_uri: redirectUri,
    });
    return response.data;
  },

  /** Get the current user's stored Gmail credential status. */
  async getCredential(): Promise<GmailCredential> {
    const response = await api.get<GmailCredential>('/providers/gmail-credential');
    return response.data;
  },

  /** Remove stored Gmail credentials. */
  async disconnect(): Promise<void> {
    await api.delete('/providers/gmail-credential');
  },

  /** Inject a debug test email into the user's Gmail inbox. */
  async sendDebugEmail(): Promise<GmailDebugEmailResponse> {
    const response = await api.post<GmailDebugEmailResponse>('/providers/gmail/debug-email');
    return response.data;
  },

  /** Update the labels applied to imported Gmail messages. */
  async updateImportLabels(importLabelTemplates: string[]): Promise<GmailCredential> {
    const response = await api.put<GmailCredential>('/providers/gmail-credential/labels', {
      import_label_templates: importLabelTemplates,
    });
    return response.data;
  },
};

// ── SMTP Config API ─────────────────────────────────────────────────────

export const smtpApi = {
  async get(): Promise<UserSmtpConfig> {
    const response = await api.get<UserSmtpConfig>('/users/smtp-config');
    return response.data;
  },

  async save(data: {
    host: string;
    port: number;
    username: string;
    password?: string;
    use_tls: boolean;
  }): Promise<UserSmtpConfig> {
    const response = await api.put<UserSmtpConfig>('/users/smtp-config', data);
    return response.data;
  },

  async remove(): Promise<void> {
    await api.delete('/users/smtp-config');
  },
};

// ── Admin Types ─────────────────────────────────────────────────────────

export interface AdminUser {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  subscription_tier: string;
  subscription_status: string;
  google_id?: string | null;
  oauth_provider?: string | null;
  last_login_at?: string | null;
  created_at: string;
  mail_account_count: number;
}

export interface AdminUserUpdate {
  full_name?: string | null;
  email?: string;
  is_active?: boolean;
  is_superuser?: boolean;
  subscription_tier?: string;
  subscription_status?: string;
}

export interface SubscriptionPlan {
  id: number;
  tier: string;
  name: string;
  description?: string | null;
  price_monthly: number;
  price_yearly?: number | null;
  max_mail_accounts: number;
  max_emails_per_day: number;
  check_interval_minutes: number;
  support_level: string;
  features?: Record<string, unknown> | null;
  is_active: boolean;
}

export interface SubscriptionPlanCreate {
  tier: string;
  name: string;
  description?: string;
  price_monthly: number;
  price_yearly?: number;
  max_mail_accounts: number;
  max_emails_per_day: number;
  check_interval_minutes: number;
  support_level: string;
  features?: Record<string, unknown>;
  is_active: boolean;
}

export interface SubscriptionPlanUpdate {
  name?: string;
  description?: string;
  price_monthly?: number;
  price_yearly?: number;
  max_mail_accounts?: number;
  max_emails_per_day?: number;
  check_interval_minutes?: number;
  support_level?: string;
  features?: Record<string, unknown>;
  is_active?: boolean;
}

export interface AdminStats {
  total_users: number;
  total_mail_accounts: number;
  total_processing_runs: number;
}

// ── Admin API ───────────────────────────────────────────────────────────

export const adminApi = {
  async getStats(): Promise<AdminStats> {
    const response = await api.get<AdminStats>('/admin/stats');
    return response.data;
  },

  async listUsers(skip = 0, limit = 100): Promise<AdminUser[]> {
    const response = await api.get<AdminUser[]>('/admin/users', {
      params: { skip, limit },
    });
    return response.data;
  },

  async getUser(id: number): Promise<User> {
    const response = await api.get<User>(`/admin/users/${id}`);
    return response.data;
  },

  async updateUser(id: number, data: AdminUserUpdate): Promise<User> {
    const response = await api.put<User>(`/admin/users/${id}`, data);
    return response.data;
  },

  async deleteUser(id: number): Promise<void> {
    await api.delete(`/admin/users/${id}`);
  },

  async listPlans(): Promise<SubscriptionPlan[]> {
    const response = await api.get<SubscriptionPlan[]>('/admin/plans');
    return response.data;
  },

  async createPlan(data: SubscriptionPlanCreate): Promise<SubscriptionPlan> {
    const response = await api.post<SubscriptionPlan>('/admin/plans', data);
    return response.data;
  },

  async updatePlan(id: number, data: SubscriptionPlanUpdate): Promise<SubscriptionPlan> {
    const response = await api.put<SubscriptionPlan>(`/admin/plans/${id}`, data);
    return response.data;
  },

  async deletePlan(id: number): Promise<void> {
    await api.delete(`/admin/plans/${id}`);
  },

  async listProcessingRuns(params?: {
    page?: number;
    page_size?: number;
    user_id?: number;
    account_id?: number;
    status?: string;
  }): Promise<PaginatedAdminRuns> {
    const response = await api.get<PaginatedAdminRuns>('/admin/processing-runs', {
      params,
    });
    return response.data;
  },

  async listProcessingLogs(params?: {
    page?: number;
    page_size?: number;
    user_id?: number;
    account_id?: number;
    run_id?: number;
    level?: string;
  }): Promise<PaginatedAdminLogsResponse> {
    const response = await api.get<PaginatedAdminLogsResponse>('/admin/processing-logs', {
      params,
    });
    return response.data;
  },
};

// ── Notification Types ──────────────────────────────────────────────────

export interface NotificationConfig {
  id: number;
  user_id: number;
  name: string;
  channel: string;
  apprise_url: string | null;
  is_enabled: boolean;
  config: Record<string, unknown>;
  notify_on_errors: boolean;
  notify_on_success: boolean;
  notify_threshold: number;
  created_at: string;
  updated_at: string;
}

export interface NotificationConfigCreate {
  name: string;
  channel: string;
  apprise_url?: string | null;
  is_enabled?: boolean;
  config?: Record<string, unknown>;
  notify_on_errors?: boolean;
  notify_on_success?: boolean;
  notify_threshold?: number;
}

export interface NotificationConfigUpdate {
  name?: string;
  channel?: string;
  apprise_url?: string | null;
  is_enabled?: boolean;
  config?: Record<string, unknown>;
  notify_on_errors?: boolean;
  notify_on_success?: boolean;
  notify_threshold?: number;
}

export interface AdminNotificationConfig {
  id: number;
  name: string;
  apprise_url: string;
  is_enabled: boolean;
  notify_on_errors: boolean;
  notify_on_system_events: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminNotificationConfigCreate {
  name: string;
  apprise_url: string;
  is_enabled?: boolean;
  notify_on_errors?: boolean;
  notify_on_system_events?: boolean;
  description?: string | null;
}

export interface AdminNotificationConfigUpdate {
  name?: string;
  apprise_url?: string;
  is_enabled?: boolean;
  notify_on_errors?: boolean;
  notify_on_system_events?: boolean;
  description?: string | null;
}

// ── Notifications API ───────────────────────────────────────────────────

export const notificationsApi = {
  async list(): Promise<NotificationConfig[]> {
    const response = await api.get<NotificationConfig[]>('/notifications');
    return response.data;
  },

  async create(data: NotificationConfigCreate): Promise<NotificationConfig> {
    const response = await api.post<NotificationConfig>('/notifications', data);
    return response.data;
  },

  async update(id: number, data: NotificationConfigUpdate): Promise<NotificationConfig> {
    const response = await api.put<NotificationConfig>(`/notifications/${id}`, data);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/notifications/${id}`);
  },

  async test(apprise_url: string): Promise<{ success: boolean; message: string }> {
    const response = await api.post<{ success: boolean; message: string }>(
      '/notifications/test',
      { apprise_url }
    );
    return response.data;
  },
};

// ── Admin Notifications API ─────────────────────────────────────────────

export const adminNotificationsApi = {
  async list(): Promise<AdminNotificationConfig[]> {
    const response = await api.get<AdminNotificationConfig[]>('/admin/notifications');
    return response.data;
  },

  async create(data: AdminNotificationConfigCreate): Promise<AdminNotificationConfig> {
    const response = await api.post<AdminNotificationConfig>('/admin/notifications', data);
    return response.data;
  },

  async update(id: number, data: AdminNotificationConfigUpdate): Promise<AdminNotificationConfig> {
    const response = await api.put<AdminNotificationConfig>(`/admin/notifications/${id}`, data);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/admin/notifications/${id}`);
  },

  async test(apprise_url: string): Promise<{ success: boolean; message: string }> {
    const response = await api.post<{ success: boolean; message: string }>(
      '/admin/notifications/test',
      { apprise_url }
    );
    return response.data;
  },
};

// ── Version API ─────────────────────────────────────────────────────────

export interface VersionInfo {
  version: string;
  build_date: string | null;
}

export const versionApi = {
  async get(): Promise<VersionInfo> {
    const response = await api.get<VersionInfo>('/version');
    return response.data;
  },
};

export default api;
