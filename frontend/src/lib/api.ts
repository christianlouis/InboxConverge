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
    data: Partial<MailAccountCreate>
  ): Promise<MailAccount> {
    const response = await api.put<MailAccount>(`/mail-accounts/${id}`, data);
    return response.data;
  },

  async toggle(id: number): Promise<MailAccount> {
    const response = await api.patch<MailAccount>(`/mail-accounts/${id}/toggle`);
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
  async list(): Promise<ProcessingRun[]> {
    // TODO: Add a dedicated /processing-runs endpoint to the backend
    // For now, return empty array since no user-facing endpoint exists yet
    return [];
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

export default api;
