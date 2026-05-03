# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- version list -->

## v0.10.1 (2026-05-03)

### Bug Fixes

- Normalise naive UTC expiry from google-auth to tz-aware in GmailService
  ([`01a85eb`](https://github.com/christianlouis/InboxConverge/commit/01a85ebedef1508b13353c55aec073562ba367d6))


## v0.10.0 (2026-05-03)


## v0.9.2 (2026-05-03)

### Bug Fixes

- Address code review comments (type hints, loop var name, em dashes)
  ([`28a7592`](https://github.com/christianlouis/InboxConverge/commit/28a75927317a30aace2c8fda1db3c6afe4792440))

- IPv4 preference + DNS cache fallback for stable POP3/IMAP connections
  ([`45a2dd8`](https://github.com/christianlouis/InboxConverge/commit/45a2dd8be294dbf0b9c69a19c285ca56ec736fde))


## v0.9.1 (2026-05-03)

### Bug Fixes

- Add separate sender/recipient email fields for SMTP notification channel
  ([`c3e608d`](https://github.com/christianlouis/InboxConverge/commit/c3e608d82fc8d7459ca02865700ba99283cf348b))


## v0.9.0 (2026-05-03)

### Bug Fixes

- Apply black formatting to test_format_connection_error.py (--target-version py312)
  ([`79d664c`](https://github.com/christianlouis/InboxConverge/commit/79d664c0e4907159e6f2558f9449522411ecda73))

- Remove unused imports and bare f-string in test_format_connection_error.py (ruff F401/F541)
  ([`b1dd171`](https://github.com/christianlouis/InboxConverge/commit/b1dd1714f7e2d40826e03ccfd6e6868002f2699e))


## [Unreleased]

### Added

- **Send Test Email button for SMTP Fallback**: a new "Send Test Email" button
  appears on the Settings page next to the Save/Remove SMTP controls once a
  configuration is saved.  It calls a new `POST /users/smtp-config/test`
  endpoint that sends a test message to the user's registered email address
  using the stored SMTP credentials, and displays an inline success or error
  banner with the result.
- **IPv4 preference for all POP3 and IMAP connections**: The app now resolves
  every mail-server hostname to an IPv4 address before connecting.  This
  prevents `ENETUNREACH` / `Network is unreachable` errors and IMAP/POP3
  connection timeouts that occur on Docker hosts where IPv6 traffic is not
  routed to the internet but dual-stack DNS returns AAAA records first.

- **In-process DNS cache with automatic fallback** (`DNS_CACHE_FALLBACK_ENABLED`,
  enabled by default): The last successfully resolved IPv4 address for each
  mail-server hostname is stored in memory.  When a subsequent DNS lookup fails
  with `EAI_AGAIN` (Temporary failure in name resolution) the cached address is
  used instead, keeping mail delivery alive through transient resolver outages.
  Set `DNS_CACHE_FALLBACK_ENABLED=false` in the environment to disable.

- **Friendly error messages**: Introduced `_format_connection_error()` helper in
  `mail_processor.py` that translates raw OS/socket/SSL/POP3/IMAP exceptions into
  human-readable sentences including the host:port and actionable guidance (DNS
  failure, TLS error, connection timeout, authentication rejection, etc.).  The
  helper is applied at every `raise MailFetchError` / `raise MailConnectionError`
  site and in both `_test_pop3_connection` and `_test_imap_connection`.

- **Per-account debug logging** (`debug_logging` column on `MailAccount`): when
  enabled, the next processing run records a structured connection trace
  (connect timing, TLS details, auth, INBOX selection, message UIDs/sizes,
  elapsed milliseconds per phase) via the new `MailDebugRecorder` class.  The
  trace is persisted as a `ProcessingLog` row with `level="DEBUG"` and surfaced
  in the "Mailbox Activity" logs page as a collapsible "Connection trace" panel.
  Debug logging auto-disables after 5 completed runs in a 24-hour window.

- **"Clear error" button**: new `POST /api/v1/mail-accounts/{id}/clear-error`
  endpoint that nulls `last_error_message`/`last_error_at` and resets `status`
  to `ACTIVE` when currently `ERROR`.  Wired into the error banners on both the
  Accounts page and the Mailbox Activity (Logs) page.

- **Debug-logging toggle** in the account edit form (Add/Edit Account modal):
  checkbox labelled "Debug logging (auto-disables after 5 runs)".

- Alembic migration `0002_add_debug_logging.py` adding the `debug_logging`
  boolean column to `mail_accounts` (idempotent via `ADD COLUMN IF NOT EXISTS`).

### Fixed

- **Transient DNS errors now produce a clear, accurate message**: `EAI_AGAIN`
  errors (errno -3 – resolver temporarily unavailable) are now reported as
  "Temporary DNS failure while resolving '…'" instead of the misleading "check
  that the server address is correct" message that was shown for all DNS errors.

- **`asyncio.get_event_loop()` replaced with `asyncio.get_running_loop()`** in
  `_test_pop3_connection`, `_fetch_pop3_emails`, `post_process_pop3`, and
  `forward_email`, silencing deprecation warnings in Python ≥ 3.10 and avoiding
  potential `DeprecationWarning → RuntimeError` in a future Python release.

- **Empty IMAP error messages** — `IMAP fetch error:` with a blank suffix was
  caused by `asyncio.TimeoutError` and `aioimaplib.Abort` having an empty
  `str()`.  The new `_format_connection_error()` helper always produces a
  non-empty, human-readable message.

- **Cryptic DNS error** — `POP3 fetch error: [Errno -5] No address associated
  with hostname` is now surfaced as `Could not resolve hostname 'pop.web.de' —
  check that the server address is correct (DNS lookup failed: …)`.

- **Sticky ERROR status after transient fetch failures**: the `tasks.py`
  processing loop previously set `account.status = ERROR` and
  `last_error_message = "{N} emails failed to forward"` even when the
  connection and fetch succeeded but some individual email-forward operations
  failed.  Now, a successful fetch (no exception from `fetch_emails`) always
  clears `last_error_message`/`last_error_at` and sets `status = ACTIVE`,
  regardless of per-email forwarding failures.  Per-email failures continue to
  be tracked in `ProcessingLog` and the run's `emails_failed` counter.
### Fixed

- OAuth Google sign-in: added `exc_info=True` to the catch-all exception handler in `auth_service.py` so the full traceback is always emitted to the log instead of only `str(e)`.
- OAuth Google sign-in: added an endpoint-level try/except in the `/auth/google` handler to catch and log any unexpected errors (e.g. database failures) that occurred after the Google token exchange, which previously surfaced as silent 500s.

## v0.8.1 (2026-05-03)

### Bug Fixes

- Downgrade eslint to ^9 and typescript to ^5 for eslint-config-next compatibility
  ([`f39241a`](https://github.com/christianlouis/InboxConverge/commit/f39241a547662fa8ae4ad408d2565ff0e50d9d55))

### Chores

- **deps**: Bump react and @types/react in /frontend
  ([`00d06c6`](https://github.com/christianlouis/InboxConverge/commit/00d06c63de26f0bbbb5184ba219ad6b02eec4ec8))


## v0.8.0 (2026-05-03)

### Bug Fixes

- Bump react to 19.2.5 to match react-dom, resolve npm ci ERESOLVE
  ([`be812dd`](https://github.com/christianlouis/InboxConverge/commit/be812dda791fe36cb1cba5e4dce5de759de9153b))

- Combine f-strings, align product name in notification titles
  ([`3470213`](https://github.com/christianlouis/InboxConverge/commit/3470213fb3374fec1101b04447ba6d2a26c1ec41))

### Chores

- **deps**: Bump @tanstack/react-query in /frontend
  ([`b20da89`](https://github.com/christianlouis/InboxConverge/commit/b20da8940f682a83c37b9b80626eb6772f7ad246))

- **deps**: Bump @types/node from 25.5.2 to 25.6.0 in /frontend
  ([`641007d`](https://github.com/christianlouis/InboxConverge/commit/641007d51cdef8b0f01b9326a93a16d1197eaf0e))

- **deps**: Bump aiohttp from 3.13.4 to 3.13.5 in /backend
  ([`4c03352`](https://github.com/christianlouis/InboxConverge/commit/4c03352650d174a1c7903f45d18ff49a6e592c0d))

- **deps**: Bump axios from 1.14.0 to 1.15.0 in /frontend
  ([`0ed6256`](https://github.com/christianlouis/InboxConverge/commit/0ed6256fb7ac1d06376a12ba2d58e3405904ba3a))

- **deps**: Bump cryptography
  ([`222fc96`](https://github.com/christianlouis/InboxConverge/commit/222fc96effced50974e1f8cc4ffa1903461bda39))

- **deps**: Bump eslint-config-next from 16.2.2 to 16.2.3 in /frontend
  ([`45a237b`](https://github.com/christianlouis/InboxConverge/commit/45a237bdcb070ecd527709fc466e27497b12bb9d))

- **deps**: Bump fastapi from 0.135.2 to 0.135.3 in /backend
  ([`56a85e9`](https://github.com/christianlouis/InboxConverge/commit/56a85e9c9eab8cc8005c9a45aecb88c08cea4f28))

- **deps**: Bump google-auth from 2.49.1 to 2.49.2 in /backend
  ([`197d7fe`](https://github.com/christianlouis/InboxConverge/commit/197d7fe060c0eed423fa060f7ad19c0a87da3eac))

- **deps**: Bump lucide-react from 1.7.0 to 1.8.0 in /frontend
  ([`095ee10`](https://github.com/christianlouis/InboxConverge/commit/095ee1059c23e8f25ed43d2ea7def3f85d3f05ef))

- **deps**: Bump next
  ([`54ecd7f`](https://github.com/christianlouis/InboxConverge/commit/54ecd7f95c7b41492b3e5777e38a66ffadab5d3a))

- **deps**: Bump prometheus-client from 0.24.1 to 0.25.0 in /backend
  ([`8df1465`](https://github.com/christianlouis/InboxConverge/commit/8df1465a64ee25618ebc930e20d040c9f287de8b))

- **deps**: Bump pytest from 9.0.2 to 9.0.3 in /backend
  ([`8441f73`](https://github.com/christianlouis/InboxConverge/commit/8441f734784bb5279f2521334a5284e24bbcb95d))

- **deps**: Bump pytest-cov from 4.1.0 to 7.1.0 in /backend
  ([`24a85d6`](https://github.com/christianlouis/InboxConverge/commit/24a85d6554e213b4316de5abaf7826efe6b7e2b4))

- **deps**: Bump python-multipart from 0.0.24 to 0.0.26 in /backend
  ([`42c5900`](https://github.com/christianlouis/InboxConverge/commit/42c5900c0677ece8e094616881f1add17d7e20b2))

- **deps**: Bump react-dom from 19.2.4 to 19.2.5 in /frontend
  ([`d6d4df2`](https://github.com/christianlouis/InboxConverge/commit/d6d4df2df1d00940e8f0800235d650deffa5b834))

- **deps**: Bump schedule from 1.2.0 to 1.2.2 in /backend
  ([`06ea195`](https://github.com/christianlouis/InboxConverge/commit/06ea1958aa7bda8c6d127c82fc751a0b3ea059e7))

### Features

- Add in-depth OAuth logging across auth_service, auth, providers, gmail_service
  ([`075ba92`](https://github.com/christianlouis/InboxConverge/commit/075ba92f09f048c71d3f20ae70c8af0c69ac2339))

- Proactive Gmail token refresh, GmailAuthError, improved logging
  ([`992e157`](https://github.com/christianlouis/InboxConverge/commit/992e157f022ae334d938575e7cb63a5135fc12ec))


## v0.7.0 (2026-04-18)

### Features

- Add English privacy policy, ToS, and legal footer links for Google OAuth verification
  ([`78610ef`](https://github.com/christianlouis/InboxConverge/commit/78610ef09da6fa21db8c9c82190f85c400de541f))


## [Unreleased]

### Added

- **English Privacy Policy** (`/privacy`): comprehensive public privacy policy in English including a Google API Services Limited Use Disclosure, explaining how `gmail.insert`, `gmail.labels`, and `gmail.readonly` scopes are used. Required for Google OAuth consent screen verification.
- **Terms of Service** (`/terms`): full English terms of service covering acceptable use, Google API compliance, data, liability, and governing law.
- **Home page footer legal links**: Privacy Policy, Terms of Service, Impressum, and Datenschutz links added to the public landing page footer — directly resolves the Google verification rejection ("homepage does not contain a link to your privacy policy").
- **Login page footer**: now includes Privacy Policy and Terms of Service links alongside the existing Impressum / Datenschutz links.
- **Register page consent text**: "By creating an account you agree to our Terms of Service and Privacy Policy" notice added below the sign-up form.
- **Datenschutz cross-link**: German privacy page now links to the English `/privacy` page in section 2 and the bottom footer bar.
- **Proactive Gmail token refresh task** (`refresh_gmail_tokens`): new Celery Beat task running every 45 minutes that refreshes any Gmail access token expiring within the next 30 minutes. Tokens with unknown expiry are also refreshed. Revoked tokens are immediately detected, marked invalid, and the user is notified. This prevents the first email delivery after a long idle period from triggering a synchronous in-band token exchange.
- **In-depth OAuth logging**: added `DEBUG`/`INFO`/`WARNING`/`ERROR` log lines at every significant step of the OAuth flow across `auth_service.py`, `auth.py`, `providers.py`, and `gmail_service.py`. Logged events include: authorize-URL generation, code exchange (with scopes and `has_refresh_token` flag), user-profile fetch, API access verification, credential create/update/delete, label updates, debug-email injection, auto-refresh detection, and proactive refresh. Token values are never logged; only metadata (email, expiry, boolean presence, scopes) is recorded.

### Changed

- **`GmailAuthError` exception class** added to `gmail_service.py` (subclass of `GmailInjectionError`): raised specifically when `google.auth.exceptions.RefreshError` is caught (i.e. the refresh token was revoked or invalid). This gives callers a typed signal distinct from ordinary API errors.
- **Improved error logging** for Gmail token failures: log messages now include the token expiry timestamp and distinguish between "refresh token revoked" and "API HTTP error" scenarios, making it much easier to diagnose authentication problems in the application logs.
- **Structured exception handling** in `process_mail_account`: `GmailAuthError` is now caught separately from generic exceptions so that revocation is detected reliably even when the error does not contain "401", "403", or "invalid_grant" in its string representation.

## v0.6.5 (2026-04-07)

### Bug Fixes

- Remove duplicate MailProcessor import in test_mail_processor_imap.py
  ([`74ef362`](https://github.com/christianlouis/InboxConverge/commit/74ef362833824c844bb34daa4a8ceb8f0aa3bc36))

- Restore missing forward_email signature and reformat with black
  ([`3dd71cd`](https://github.com/christianlouis/InboxConverge/commit/3dd71cd61d069776df2c3908392057e49f2f29f7))

- Retry failed forwarded emails; only post-process successfully forwarded messages
  ([`ff7b50d`](https://github.com/christianlouis/InboxConverge/commit/ff7b50d944960d4da419ede988c2b1f24316b88d))


## v0.6.4 (2026-04-07)

### Bug Fixes

- Replace deprecated .dict() with .model_dump() and fix db.add() AsyncMock warnings
  ([`31dc059`](https://github.com/christianlouis/InboxConverge/commit/31dc059274f0e75f6ea46581b4b4ec0dca994d37))


## [Unreleased]

### Fixed
- Replace deprecated Pydantic V2 `.dict()` calls with `.model_dump()` in `admin.py` and `notifications.py` endpoints.
- Fix `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited` in `test_tasks.py` and `test_config_service.py` by marking `db.add` as a synchronous `MagicMock` in test helpers.

## v0.6.3 (2026-04-07)

### Bug Fixes

- **lint**: Specify explicit React version to fix ESLint 10 compatibility
  ([`efa553c`](https://github.com/christianlouis/InboxConverge/commit/efa553c8d52b2e7595318b5e4897baf13b4d847d))

### Chores

- **ci**: Bump docker/login-action from 3 to 4
  ([`6fe2f9a`](https://github.com/christianlouis/InboxConverge/commit/6fe2f9ad951a75d7c43bbb596cce9af552b82ece))

- **deps**: Bump @tanstack/react-query in /frontend
  ([`466e852`](https://github.com/christianlouis/InboxConverge/commit/466e852c8bb587ed9f98198c8ef7a570e4cb1aec))

- **deps**: Bump @types/node from 25.5.0 to 25.5.2 in /frontend
  ([`cc1edd8`](https://github.com/christianlouis/InboxConverge/commit/cc1edd8f5d1893eeecc83afb7795983fe5181b71))

- **deps**: Bump aiosmtplib from 3.0.1 to 5.1.0 in /backend
  ([`284fbba`](https://github.com/christianlouis/InboxConverge/commit/284fbba47f1082cc52a3d23ec82ef24d443f1c17))

- **deps**: Bump alembic from 1.13.1 to 1.18.4 in /backend
  ([`bd51a5b`](https://github.com/christianlouis/InboxConverge/commit/bd51a5b541db60610976d784e3518b00b04d9b65))

- **deps**: Bump email-validator from 2.1.0.post1 to 2.3.0 in /backend
  ([`6f414e1`](https://github.com/christianlouis/InboxConverge/commit/6f414e175a117aa1faa57844797be33b258ac380))

- **deps**: Bump eslint from 9.39.4 to 10.2.0 in /frontend
  ([`4bb92ac`](https://github.com/christianlouis/InboxConverge/commit/4bb92ac9d030aef180b2b358f4e824068a6c5c74))

- **deps**: Bump eslint-config-next from 16.2.1 to 16.2.2 in /frontend
  ([`9d53b11`](https://github.com/christianlouis/InboxConverge/commit/9d53b117d4c10282c1525312e048a509fba4aa00))

- **deps**: Bump faker from 22.6.0 to 40.12.0 in /backend
  ([`9553fae`](https://github.com/christianlouis/InboxConverge/commit/9553fae6b7a06a1780672a8c3ecd1d98b945731d))

- **deps**: Bump google-auth-httplib2 from 0.3.0 to 0.3.1 in /backend
  ([`233595e`](https://github.com/christianlouis/InboxConverge/commit/233595e5ddf3caf135ff36ab15a702955868b131))

- **deps**: Bump google-auth-oauthlib from 1.2.0 to 1.3.1 in /backend
  ([`3bb7a7c`](https://github.com/christianlouis/InboxConverge/commit/3bb7a7cd460d01356c89914681d3bb1344231dae))

- **deps**: Bump lucide-react from 0.577.0 to 1.7.0 in /frontend
  ([`bfaa639`](https://github.com/christianlouis/InboxConverge/commit/bfaa639eedf97df6e81620590b1a21e6e780b1e3))

- **deps**: Bump next from 16.2.1 to 16.2.2 in /frontend
  ([`a5d8700`](https://github.com/christianlouis/InboxConverge/commit/a5d87001194b9f0764875975e0d792b85e073ceb))

- **deps**: Bump python-multipart from 0.0.22 to 0.0.24 in /backend
  ([`f479974`](https://github.com/christianlouis/InboxConverge/commit/f479974a5a432183de01a5c58264ff9e35376d7d))

- **deps**: Bump sqlalchemy from 2.0.48 to 2.0.49 in /backend
  ([`6283d1c`](https://github.com/christianlouis/InboxConverge/commit/6283d1c4b4a46afb43cbafbfbb570e7be23cdef8))

- **deps**: Bump stripe from 14.4.1 to 15.0.1 in /backend
  ([`582311a`](https://github.com/christianlouis/InboxConverge/commit/582311a18e6ec02ef90b6d049c709ef0057bb837))

- **deps**: Bump uvicorn from 0.42.0 to 0.43.0 in /backend
  ([`b2d044d`](https://github.com/christianlouis/InboxConverge/commit/b2d044d8c209853f5ee2e58ab7e6b701ba462015))


## v0.6.2 (2026-04-05)

### Code Style

- Reformat test_gdpr.py and test_gmail_labels.py to fix black CI check
  ([`7afa33f`](https://github.com/christianlouis/InboxConverge/commit/7afa33f3758d289bb0971e3f83bcc30b39e436f1))


## [Unreleased]

### Added

- Expanded `gmail_service.py` unit test coverage: 10 new tests covering `inject_email` HttpError branch, `get_or_create_label` (existing/create/HttpError/generic-error), `inject_debug_email` full flow, `get_refreshed_token` (changed/unchanged), and `service` property lazy initialization — 24 total tests in `test_gmail_service.py`
- Expanded `api.ts` test coverage from 20% to near-complete: 56 new tests covering all 10 API objects (`authApi`, `userApi`, `mailAccountsApi`, `processingRunsApi`, `gmailApi`, `smtpApi`, `adminApi`, `notificationsApi`, `adminNotificationsApi`, `versionApi`) — 65 total tests in `api.test.ts`
- Unit tests for `AddMailAccountModal` component (`AddMailAccountModal.test.tsx`): 28 tests covering create/edit mode rendering, provider wizard flow, form field changes, checkbox toggles, auto-detect, test connection, submit mutations, error extraction, and modal close interactions
- Unit tests for provider endpoints (`test_providers.py`): 23 tests covering provider presets, Gmail credential CRUD, import labels, authorize URL, debug email, and OAuth callback
- Unit tests for mail account endpoints (`test_mail_accounts.py`): 30 tests covering CRUD, toggle, pull-now, test connection, auto-detect, processing runs, and processing logs
- Unit tests for authentication endpoints (`test_auth.py`): 22 tests covering register, login, Google OAuth, authorize-url, and helper functions
- **Backend test coverage expanded** (+150 tests, 361 → 511 total): added `test_gdpr.py` (GDPR masking utilities), `test_gmail_labels.py` (Gmail label helpers), `test_notification_service.py` (Apprise notification service), `test_auth_service.py` (OAuth service token exchange and token creation), `test_version_endpoint.py`, `test_auth_endpoints.py` (register, login, Google OAuth, authorize-url, domain helpers), `test_users_endpoints.py` (profile CRUD, SMTP config upsert/delete), `test_notifications_endpoints.py` (full CRUD + test-send), `test_logs_endpoints.py` (processing-runs pagination/filtering + run log retrieval), and `test_app_settings_endpoints.py` (list, upsert, delete, seed-defaults with bootstrap key guards).
## v0.6.1 (2026-04-05)

### Bug Fixes

- Upgrade pytest-asyncio to 1.3.0 for pytest 9.x compatibility
  ([`39052af`](https://github.com/christianlouis/InboxConverge/commit/39052af4e2a5df1dd29062b7dcced9b1f2f17baf))

### Chores

- **ci**: Bump actions/checkout from 4 to 6
  ([`68a6163`](https://github.com/christianlouis/InboxConverge/commit/68a6163fef8e81e250d6959d94be2174bf9fba31))

- **ci**: Bump codecov/codecov-action from 5 to 6
  ([`594e380`](https://github.com/christianlouis/InboxConverge/commit/594e3803013363c0360d32fc329e9b427fa62835))

- **ci**: Bump docker/build-push-action from 5 to 7
  ([`2c26c15`](https://github.com/christianlouis/InboxConverge/commit/2c26c156f63cc7335cf7799a443c63d734c047f7))

- **ci**: Bump docker/metadata-action from 5 to 6
  ([`0e87da8`](https://github.com/christianlouis/InboxConverge/commit/0e87da85a61b9c1a764313231b69882b9aa55137))

- **ci**: Bump mikefarah/yq from 4.44.6 to 4.52.5
  ([`f4c8e4a`](https://github.com/christianlouis/InboxConverge/commit/f4c8e4a1dc98d221eabd137bb71459ebec9de254))

- **deps**: Bump @tanstack/react-query in /frontend
  ([`348c347`](https://github.com/christianlouis/InboxConverge/commit/348c3477dcbb0c504681cc71df6d7d098ae378df))

- **deps**: Bump @types/node from 20.19.30 to 25.5.0 in /frontend
  ([`917dacc`](https://github.com/christianlouis/InboxConverge/commit/917dacc7cb9f1fa35a8dc2a72664b7d022039f2c))

- **deps**: Bump aiohttp from 3.13.3 to 3.13.4 in /backend
  ([`d919939`](https://github.com/christianlouis/InboxConverge/commit/d91993964783c6bfde48b6f115abb6d02b0eec5c))

- **deps**: Bump apprise from 1.7.1 to 1.9.9 in /backend
  ([`094b1e1`](https://github.com/christianlouis/InboxConverge/commit/094b1e177fcefc77b417a6715446fa13527c1a16))

- **deps**: Bump axios from 1.13.6 to 1.14.0 in /frontend
  ([`3b580c3`](https://github.com/christianlouis/InboxConverge/commit/3b580c36c751d962e4c164596ce65ef4e7ce5048))

- **deps**: Bump bcrypt from 4.3.0 to 5.0.0 in /backend
  ([`f0213a0`](https://github.com/christianlouis/InboxConverge/commit/f0213a0b03b05195329323d68a870a51e0a97150))

- **deps**: Bump celery from 5.6.2 to 5.6.3 in /backend
  ([`5992a9e`](https://github.com/christianlouis/InboxConverge/commit/5992a9e802686227675867a259771dcb3ecf41bb))

- **deps**: Bump httpx from 0.26.0 to 0.28.1 in /backend
  ([`c50cf6e`](https://github.com/christianlouis/InboxConverge/commit/c50cf6e0b32f2d115e9345054b777d3ab8a63f2b))

- **deps**: Bump next from 16.1.7 to 16.2.1 in /frontend
  ([`ec90cd6`](https://github.com/christianlouis/InboxConverge/commit/ec90cd600b03fd0aea64a9c395b11b7faaa0d52a))

- **deps**: Bump prometheus-client from 0.19.0 to 0.24.1 in /backend
  ([`77c8426`](https://github.com/christianlouis/InboxConverge/commit/77c84266fd5ea93f9c59e4ef3d9b37990f232883))

- **deps**: Bump pytest from 7.4.4 to 9.0.2 in /backend
  ([`4a6f93e`](https://github.com/christianlouis/InboxConverge/commit/4a6f93e5acf5a2f7766e25444a20e11a5918a2b6))

- **deps**: Bump python-dotenv from 1.0.0 to 1.2.2 in /backend
  ([`4dbe30b`](https://github.com/christianlouis/InboxConverge/commit/4dbe30b0eadb829e0d112b2c9ce877353b9d903e))

- **deps**: Bump redis from 7.3.0 to 7.4.0 in /backend
  ([`b914ac0`](https://github.com/christianlouis/InboxConverge/commit/b914ac0ecd8a14bb1c3a96a232de330622c93ac7))

- **deps**: Bump typescript from 5.9.3 to 6.0.2 in /frontend
  ([`726e089`](https://github.com/christianlouis/InboxConverge/commit/726e089c464b81e33ee872cd200b346cb996dcf6))

- **deps**: Bump uvicorn from 0.27.0 to 0.42.0 in /backend
  ([`ac6a837`](https://github.com/christianlouis/InboxConverge/commit/ac6a837522c1dcfee3fdc9b6e9dca2f94460053f))

### Documentation

- Fix CHANGELOG entry to only reference pytest-asyncio bump
  ([`0521c97`](https://github.com/christianlouis/InboxConverge/commit/0521c97394ff3f4e909f9b463bd15958ac06b76f))

- Fix secret key generation syntax in README quickstart
  ([`9c12555`](https://github.com/christianlouis/InboxConverge/commit/9c12555a8116e1db605d3fc3042de48d292b2be2))

- Rewrite README focused on Google 2026 POP/Gmailify shutdown replacement
  ([`06efeed`](https://github.com/christianlouis/InboxConverge/commit/06efeed7be70a2d1da3a9e55a63cb8c9556b8c31))


## [Unreleased]

### Changed

- Bumped `pytest-asyncio` from 0.23.3 to 1.3.0 to restore compatibility with pytest 9.0.2 in the backend test suite.

## v0.6.0 (2026-03-29)

### Chores

- Initial plan for frontend test coverage
  ([`7dd0b5f`](https://github.com/christianlouis/InboxConverge/commit/7dd0b5f6005b4d4c2db4cc0939fa6b4921ceff94))

### Features

- Add frontend test coverage for date-utils, api interceptors, AuthGuard, QueryProvider,
  DashboardLayout
  ([`63839c3`](https://github.com/christianlouis/InboxConverge/commit/63839c3886445527258d988ad65f869cf46387a5))

- Add NotificationWizard + ProviderWizard tests, fix lint, update docs
  ([`769907a`](https://github.com/christianlouis/InboxConverge/commit/769907a65b956048a77e5714b998a45426d08bf4))


## v0.5.1 (2026-03-28)

### Bug Fixes

- Convert jest.config.js to jest.config.mjs (ES module syntax)
  ([`0a0836e`](https://github.com/christianlouis/InboxConverge/commit/0a0836e993721a5702582c78d5b86bd52da96e44))


## [Unreleased]

### Changed

- **README rewrite**: Replaced README with a focused, marketing-oriented page targeting users affected by Google's 2026 shutdown of Gmail POP import ("Check mail from other accounts") and Gmailify. Fixed broken CI badge links (pointed to non-existent workflow files; now correctly references `ci.yml`). Removed verbose technical implementation sections in favour of a clear problem statement, comparison table, 5-minute quick-start, and concise delivery-method summary.

### Added

- **Celery tasks test coverage**: Added 40 unit tests for `backend/app/workers/tasks.py`, raising coverage from 9.22% to 96%. Tests cover `_as_utc` helper, `process_mail_account` (Gmail API and SMTP forwarding, credential revocation, empty-email detection, error handling), `process_all_enabled_accounts` (stale-run cleanup, interval checking), and `cleanup_old_logs` (data retention, stale-run recovery).

- **Admin endpoint test coverage**: Added 87 unit tests for `admin.py` covering all 17 endpoints (stats, user CRUD, plan CRUD, notification config CRUD, notification testing, processing runs/logs with GDPR masking and pagination). Coverage improved from 24% to 100%.
- **Domain-based logo fallback for mail accounts**: `ProviderLogoBanner` now shows provider logos even for accounts that have no `provider_name` set, by extracting the domain from the email address and matching it against a new `DOMAIN_ICON_MAP`. Covers Gmail, GMX, WEB.DE, Yahoo Mail, AOL, T-Online, Outlook/Hotmail, IONOS, Freenet, iCloud, Posteo, and Proton Mail.
- **Frontend test coverage**: Added 113 new tests across 7 new test suites covering all components, utility functions, and API interceptors. Installed `@testing-library/react`, `@testing-library/jest-dom`, and `@testing-library/user-event`. New suites: `date-utils.test.ts` (30 tests), `api.test.ts` (9 tests), `AuthGuard.test.tsx` (6 tests), `QueryProvider.test.tsx` (2 tests), `DashboardLayout.test.tsx` (14 tests), `NotificationWizard.test.tsx` (32 tests), `ProviderWizard.test.tsx` (20 tests). Total frontend: 119 tests across 8 suites.
- **Improved `mail_processor.py` test coverage**: Added 46 unit tests for POP3 connection testing, POP3 email fetching, IMAP edge cases (stale UID store failure, delete failure, MailFetchError re-raise, star-prefix line filtering), email forwarding (STARTTLS/SSL/multipart), and routing methods. Statement coverage increased from ~42% to 98%.

### Fixed

- **Test fixtures**: Fixed `conftest.py` admin user fixture using non-existent `is_admin`/`is_verified` fields (should be `is_superuser`), and JWT `sub` claim using email instead of user ID.
- Convert `frontend/jest.config.js` to `jest.config.mjs` using ES module `import`/`export` syntax to resolve ESLint `@typescript-eslint/no-require-imports` error.
- Suppress noisy `ignored untagged response` INFO log lines from `aioimaplib` in Celery workers by setting the `aioimaplib` logger to WARNING level in `celery_app.py`.
- Eliminate `file_cache is only supported with oauth2client<4.0.0` warnings by passing `cache_discovery=False` to `googleapiclient.discovery.build()` in `gmail_service.py`.

## v0.5.0 (2026-03-28)

### Features

- **ci**: Add Codecov integration with frontend Jest coverage and CODECOV_TOKEN
  ([`0645bc0`](https://github.com/christianlouis/InboxConverge/commit/0645bc046227332ebe1fdbf05538500587515ebf))


## v0.4.5 (2026-03-28)

### Bug Fixes

- **ci**: Replace safety scan with pip-audit to fix CI EOF error
  ([`8152635`](https://github.com/christianlouis/InboxConverge/commit/8152635238ab4167dc3c63b31b4d54d85ace76a2))


## [Unreleased]

### Added

- Codecov integration: frontend Jest test coverage (lcov) and backend pytest-cov (XML) are now uploaded to Codecov with `CODECOV_TOKEN` authentication and separate `frontend`/`backend` flags.

### Fixed

- CI: replaced `safety scan --json` (requires interactive login in Safety CLI v3) with `pip-audit` to fix EOF error in the security scan job

## v0.4.4 (2026-03-28)

### Bug Fixes

- Show proper error message instead of [object Object] in mail account wizard
  ([`191fee9`](https://github.com/christianlouis/InboxConverge/commit/191fee9be4a2fd77d76ee089d09717db85deeca3))


## v0.4.3 (2026-03-28)

### Bug Fixes

- Apply parseUTC to dashboard, unify date helpers in date-utils.ts
  ([`db3ce61`](https://github.com/christianlouis/InboxConverge/commit/db3ce6146797e9e3a54c434b54215d131dd5ce65))

- Drop empty emails, clear stale errors on success, harden IMAP extraction
  ([`0720901`](https://github.com/christianlouis/InboxConverge/commit/0720901265c53d05609787166dfecbcc6b0d2b1b))


## [Unreleased]

### Security

- Upgraded `fastapi` from `0.109.1` to `0.135.2`, pulling in `starlette>=1.0.0` and fixing 4 Denial-of-Service vulnerabilities present in `starlette<=0.35.1`.
- Updated CI security scan command from deprecated `safety check` to `safety scan`.
- Added `.safety-policy.yml` to document and suppress the two unfixable `ecdsa` side-channel CVEs (64396, 64459) that the upstream maintainers have acknowledged cannot be resolved in pure Python.
### Fixed

- **Add mail account wizard showed `[object Object]`** — FastAPI validation
  errors return `detail` as an array of objects, not a plain string.  The
  frontend error handler now inspects the type of `detail`: if it is a string
  it is used directly; if it is an array the individual `msg` fields are joined;
  otherwise the generic `Error.message` or a fallback string is shown.  The fix
  is applied to both the Save and Test-Connection error paths.

- **IMAP: fix all IMAP emails appearing empty** — `aioimaplib` stores RFC822
  literal data as `bytearray`, not `bytes`.  The FETCH extraction loop was
  checking `isinstance(line, bytes)` which returns `False` for `bytearray`,
  causing every email body to be silently skipped and the message to appear
  empty.  The check now accepts both types (`isinstance(line, (bytes,
  bytearray))`) and converts the result to plain `bytes` before returning,
  so the rest of the pipeline is unaffected.  This affected every IMAP
  account (T-Online, GMX, and others).
- **IMAP: fix T-Online BYE "Too many invalid IMAP commands"** — `UID STORE` flag
  arguments now use RFC 3501–required parentheses: `+FLAGS (\Seen)` and
  `+FLAGS (\Deleted)`.  Strict servers such as T-Online reject the bare
  `+FLAGS \Seen` syntax as a `BAD` command and forcefully drop the connection.
- **IMAP: fix `aioimaplib` crash on `UID SEARCH`** — `aioimaplib`'s `.uid()`
  wrapper explicitly blocks `"search"`, raising
  `command UID only possible with COPY, FETCH, EXPUNGE (w/UIDPLUS) or STORE`.
  The initial UNSEEN discovery now uses a plain `SEARCH UNSEEN` to obtain
  sequence numbers, followed by a lightweight `FETCH (UID)` to resolve them
  to stable UIDs; all subsequent operations (`FETCH`, `STORE`) continue to
  use the UID form.
- **IMAP: filter whitespace-only RFC822 responses** — the FETCH extraction
  loop now checks `email_data.strip()` so that trivially-empty byte payloads
  (e.g. `\r\n`) returned by servers like T-Online are rejected at the
  extraction layer rather than being forwarded as empty emails.
- **Tasks: drop completely empty emails with a warning** — after parsing
  each fetched email, the processing loop now checks whether the message has
  no subject, no From header, and no body.  Such emails are silently dropped
  (logged as `WARNING`, written to the processing log, UID recorded as seen
  so the message is not retried).  This handles cases where T-Online or
  other servers emit genuinely empty RFC822 responses that may indicate a
  server-side bug.
- **Status page: clear stale IMAP errors after a successful run** — on a
  successful processing run (`emails_failed == 0`), the account's
  `last_error_message` and `last_error_at` fields are now cleared.
  Previously a transient IMAP error would remain visible on the dashboard
  even after subsequent pulls completed without problems.
- **Dashboard: fix UTC hour-shift on "Last check" timestamps** — the dashboard
  page was using `new Date(iso)` which treats timezone-naive ISO strings from
  the backend as local time, shifting relative labels (e.g. "1h ago" instead
  of "Just now") for users outside UTC.  The dashboard now uses the same
  `parseUTC()` helper that the logs page already applied.  The helper functions
  `formatRelative`, `formatDate`, and `formatDuration` have been consolidated
  into `src/lib/date-utils.ts` and are imported by all pages.

## v0.4.2 (2026-03-28)

### Bug Fixes

- CI pipeline Node.js 20 deprecation, Codecov input, img lint errors
  ([`40c23c4`](https://github.com/christianlouis/InboxConverge/commit/40c23c43fe2e0c08eae8e714ce7782d0b1b12c29))

- Suppress bandit B104 false positive for 0.0.0.0 binding in config.py
  ([`c092dd9`](https://github.com/christianlouis/InboxConverge/commit/c092dd9ac62f17574345167f5a4a96ba7c15d65b))

### Code Style

- Apply black formatting to test_mail_processor_imap.py
  ([`3c8bb4b`](https://github.com/christianlouis/InboxConverge/commit/3c8bb4bfb6df209a1e90f628ab44b8af9f3601fd))


## v0.4.1 (2026-03-28)

### Bug Fixes

- Use UID-based IMAP commands and batch STORE operations to fix T-Online BYE errors
  ([`454452a`](https://github.com/christianlouis/InboxConverge/commit/454452a0b61cdc6176443be9a030effc4e1c9ba3))


## [Unreleased]

### Security

- Suppress bandit B104 false positive for `HOST = "0.0.0.0"` in `config.py`; binding to all interfaces is intentional for containerised deployments.

### Fixed

- CI: add `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` env to `ci.yml` to fix Node.js 20 deprecation warnings for `actions/checkout` and `actions/github-script`.
- CI: fix Codecov upload step — change invalid `file:` input to `files:` for `codecov/codecov-action@v5`.
- Frontend: replace `<img>` with `<Image />` from `next/image` in `ProviderWizard.tsx` to fix `no-img-element` ESLint errors.

- Fix timezone display in Mailbox Activity / Admin Logs pages: timestamps from the server were parsed as local time when no timezone indicator was present, causing relative times ("1h ago") and absolute dates to be shifted by the client's UTC offset.
- Worker tasks: use a fresh DB session for `send_user_notification` calls and move notifications after `db.commit()` to prevent the post-rollback `greenlet_spawn` SQLAlchemy error.
- Worker tasks: ensure `last_check_at` and error status are always committed before notifications, fixing accounts being endlessly re-queued after IMAP auth failures.
- Style: apply black formatting to `backend/tests/unit/test_mail_processor_imap.py` to fix CI black check failure.
## v0.4.0 (2026-03-28)

### Features

- **dashboard**: Replace per-run table with per-account Mailbox Status view
  ([`6afd7c8`](https://github.com/christianlouis/InboxConverge/commit/6afd7c871e7c694a93f119aa66f1b798c9b5b2bd))


## [Unreleased]

### Changed

- Dashboard "Recent Processing Runs" table replaced with a per-account **Mailbox Status** view: each account now shows its last-check status (OK / Error / Pending), relative last-check time, any error message, and lifetime processed/failed counters. The noisy per-run table is gone; full activity history remains available on the Logs page.
- Stats cards updated: "Emails Forwarded Today" → "Emails Processed" (all-time total from account records); "Errors" → "Accounts with Errors" (count of accounts currently showing an error).
- **IMAP: switched to UID-based commands** (`UID SEARCH`, `UID FETCH`, `UID STORE`) instead of volatile sequence-number-based commands.  Sequence numbers shift whenever other messages are expunged, causing the wrong messages to be targeted and triggering "Too many invalid IMAP commands" errors on strict servers like T-Online.  UIDs remain stable for the lifetime of a mailbox.
### Fixed
- Provider logos now appear on the Mail Accounts page: `provider_name` is correctly saved when creating accounts via the provider wizard and propagated through backend/frontend schemas.
- Fetch-emails button now shows a text label ("Fetch"), a descriptive tooltip, a "Fetching…" loading state, and a brief green "Queued!" confirmation after the action completes.
- **IMAP: eliminated redundant per-message `STORE +FLAGS \Seen`** — RFC822 FETCH implicitly marks a message as `\Seen` on IMAP servers, making the extra round-trip unnecessary.  This reduces the total command count by *N* per polling cycle.
- **IMAP: batch `STORE +FLAGS \Deleted`** — when `delete_after_forward` is enabled, all successfully fetched UIDs are now marked for deletion in a single `UID STORE uid1,uid2,…` command instead of one command per message.
- **IMAP: batch re-marking of stale UIDs** — UIDs already tracked in the database that still appear as UNSEEN on the server (e.g. because a previous STORE failed) are now re-marked `\Seen` with a single batch command instead of one STORE per message.
- **IMAP: graceful BYE handling** — the IMAP client is now stored in a variable so the `finally` block always attempts a clean `logout()`.  If the server has already sent `BYE` and closed the connection the logout failure is swallowed silently, preventing it from masking the original error.

## v0.3.2 (2026-03-28)

### Bug Fixes

- Resolve 21 mypy type errors across backend modules
  ([`0698eca`](https://github.com/christianlouis/InboxConverge/commit/0698eca62835d498135137176f4df7d0572cd033))


## v0.3.1 (2026-03-28)

### Bug Fixes

- Test connection always showed success; add per-account test endpoint
  ([`441e8b5`](https://github.com/christianlouis/InboxConverge/commit/441e8b54e958686fe52414393d715a18dfcda77c))
- Fixed 21 mypy type errors across `notification_service.py`, `mail_processor.py`, `auth.py`, `tasks.py`, `providers.py`, `mail_accounts.py`, and `main.py`


## v0.3.0 (2026-03-28)

### Features

- Mailbox-centric activity view, reduce log noise from empty polling cycles
  ([`dd4532f`](https://github.com/christianlouis/InboxConverge/commit/dd4532f6604e2e8c1fa27fd3da05cd5e62733842))


## v0.2.2 (2026-03-28)

### Bug Fixes

- **Test Connection always showed "success"**: frontend never checked the `success` field
  returned by the backend — any HTTP 200 response (including `{success: false}`) was
  displayed as "Connection successful!". Now the actual `success` value is checked and
  authentication failures are shown as errors with the server's message.
- **Test Connection in edit mode required password re-entry**: added backend endpoint
  `POST /mail-accounts/{account_id}/test` that decrypts and uses the stored credentials
  so existing accounts can be tested without re-typing the password.



### Bug Fixes

- Resolve semantic-release CHANGELOG.md not updating properly
  ([`d3e0ca4`](https://github.com/christianlouis/InboxConverge/commit/d3e0ca4e33779372b53884e25cf0d5cc3478848c))

### Chores

- **deps**: Bump cryptography
  ([`2fd018a`](https://github.com/christianlouis/InboxConverge/commit/2fd018afa109a2fa9d087da8590323c9a9d520ed))


## [Unreleased]

### Added
- **Pull Now**: Added a "Pull Now" button (⟳) to each mail account card on the Accounts page. Clicking it immediately queues a Celery `process_mail_account` task for that account via the new `POST /mail-accounts/{id}/pull-now` backend endpoint. The button shows a spinner while the request is in flight and is disabled for inactive accounts.
- **Provider logos**: Provider logos (Gmail, GMX, WEB.DE, Outlook, Yahoo, AOL, T-Online, IONOS, Freenet, Posteo, iCloud, Proton Mail) are displayed as a full-width banner at the top of each account card. Using `next/image` with `fill` + `object-contain` ensures every logo – from square icons to very wide wordmarks (up to 6:1 aspect ratio) – renders correctly without distortion.
- **Proton Mail**: Added Proton Mail as a provider preset (backend + ProviderWizard). Supports IMAP and POP3 via Proton Mail Bridge (default ports 127.0.0.1:1143 / 127.0.0.1:1144). Domains: `proton.me`, `protonmail.com`, `protonmail.ch`, `pm.me`.

### Changed
- **Mailbox Activity view**: The user-facing "Logs" page has been redesigned to a mailbox-centric
  layout (renamed "Mailbox Activity"). Each mail account is shown as a card with its last check
  status and error (if any). Only runs that actually fetched emails are shown in the pull history,
  eliminating noise from empty polling cycles. This mirrors Gmail's external POP pull UI.
- **Processing runs filter**: Added `has_emails` query parameter to `GET /processing-runs` and
  `GET /mail-accounts/{id}/processing-runs`. When `has_emails=true`, only runs with
  `emails_fetched > 0` are returned, allowing clients to suppress empty polling noise.

### Fixed
- **Processing log durations**: Runs that were killed by SIGKILL or failed before updating their
  own status (e.g. missing SMTP credentials) now always record a correct `completed_at` and
  `duration_seconds`. The error handler no longer accesses an expired SQLAlchemy ORM attribute
  (`run.started_at`) after a session rollback, which previously caused the handler to crash and
  left runs stuck in the `running` state indefinitely.
- **Celery datetime crash**: Fixed `TypeError: can't subtract offset-naive and offset-aware
  datetimes` in `process_all_enabled_accounts` by wrapping `account.last_check_at` with the
  existing `_as_utc()` helper before comparing against `datetime.now(timezone.utc)`. This
  crash silently prevented every mail account from being processed on every scheduled run.
- **Per-account polling interval**: Changed the Celery beat schedule for
  `process_all_enabled_accounts` from every 5 minutes (`*/5`) to every minute (`*`). The
  per-account `check_interval_minutes` field already gates whether an account actually gets
  processed, so accounts configured with a 1-minute interval are now polled as expected instead
  of being limited to 5-minute effective intervals.
- **Processing log early-exit path**: When a mail account has no delivery method configured
  (SMTP credentials missing and Gmail API not set up), the processing run now correctly sets
  `completed_at`, `duration_seconds`, and `account.last_check_at`, preventing the account from
  being re-queued on every scheduler tick and generating a flood of failed runs.
- **Stale-run detection moved to scheduler**: `process_all_enabled_accounts` (runs every 5 min)
  now marks orphaned `running` runs as `failed` immediately. Previously this only happened in the
  daily `cleanup_old_logs` task, meaning stale runs could show huge durations (hours/days).
- **Duration display rounding bug**: `formatDuration` in the frontend Processing Logs page now
  uses `Math.floor` instead of `Math.round` for the seconds component, eliminating the "60s"
  artefact that appeared for durations very close to a whole minute boundary.
- **Frontend dependency conflict**: Bumped `react` from `19.2.4` to `19.2.5` in `frontend/package.json` to match `react-dom@19.2.5`, resolving the `ERESOLVE` peer-dependency conflict that broke `npm ci`.

### Changed
- **Decoupled Gmail permissions from Google Sign-In**: The "Sign in with Google" OAuth flow now only requests basic profile scopes (`openid`, `email`, `profile`) instead of also requesting Gmail API scopes (`gmail.insert`, `gmail.labels`, `gmail.readonly`). Users can grant Gmail access separately via the "Connect Gmail" button in Settings. This results in a simpler, permission-free login experience.


## [0.2.1] - 2026-03-27

### Fixed
- **`SyntaxWarning` at startup**: Fixed invalid escape sequence `\S` in a docstring in `mail_processor.py` (changed to `\\S`). In Python 3.12+ this emits a `SyntaxWarning` and will become a `SyntaxError` in a future Python version.
- **Processing runs stuck in "running" state**: Fixed three related bugs in `tasks.py` that caused `ProcessingRun` records to remain in the `running` state indefinitely:
  1. The exception handler now calls `await db.rollback()` before attempting to write the `failed` status, ensuring the SQLAlchemy session is in a clean state even when the original exception occurred during a DB flush/commit.
  2. The error-handler `await db.commit()` is now wrapped in its own `try/except` so a commit failure inside the handler no longer propagates silently and leaves the run as `running`.
  3. `account.last_check_at` is now updated in the error path, throttling re-dispatch by `process_all_enabled_accounts` and preventing a cascade of new `running` runs on every scheduler tick.
- **Stale "running" run cleanup**: `cleanup_old_logs` now marks any `ProcessingRun` that has been in the `running` state for longer than 35 minutes (Celery hard time-limit is 30 min) as `failed` with an explanatory message. This recovers runs left behind by OOM kills, container restarts, or other SIGKILL events.

## [0.2.0] - 2026-03-27

### Added
- **Automatic release numbers** (`pyproject.toml`): Added `version_toml = ["pyproject.toml:project.version"]` to `[tool.semantic_release]` so that `python-semantic-release` now writes the computed version back into the `project.version` field of `pyproject.toml` on every release. The field is initialised to `0.0.0` and will be bumped automatically from that point forward.
- **Release badge** (`README.md`): Added a dynamic "GitHub Release" shield that always shows the latest published release tag.
- **Releases section** (`README.md`): Added a "Releases" section explaining the Semantic Versioning / Conventional Commits workflow and the version-bump rules.

### Fixed
- **CI `update-k8s-manifest` job**: Fixed image tag computation and `yq` update patterns to target `registry.cklnet.com` (private registry) instead of `ghcr.io`. The k8s manifest uses private registry image references, so the previous GHCR-based patterns never matched and no tag updates were applied.
- **CI `update-k8s-manifest` job**: Enhanced the PAT validation step to verify the token actually has read access to the `k8s-cluster-state` repository (via a GitHub API probe) before attempting checkout, preventing a 403 "Write access to repository not granted" failure when the PAT exists but lacks the necessary repository access.

## [0.1.2] - 2026-03-27

### Fixed
- **CI `update-k8s-manifest` job**: Added a `Check if GH_PAT is configured` step that emits a warning and skips the GitOps steps when the `GH_PAT` secret is absent or empty, preventing a 403 "Write access to repository not granted" failure that blocked the pipeline when the secret was not set.

## [0.1.1] - 2026-03-27

### Fixed
- **CI `update-k8s-manifest` job**: Fixed checkout of `k8s-cluster-state` repo by adding `ref: main` to the `actions/checkout` step, preventing a "Not Found" 404 error caused by the action's API call to determine the default branch. Also corrected the image tag format from `main-<sha>` to `sha-<sha>` to match the tags actually generated by `docker/metadata-action@v5` with `type=sha`.
- **`ProgrammingError` on `notification_configs`**: Added Alembic migration `0001` that runs `ALTER TABLE notification_configs ADD COLUMN IF NOT EXISTS` for the `name` and `apprise_url` columns introduced by the Apprise PR. SQLAlchemy's `create_all` does not ALTER existing tables, so existing deployments were missing these columns and crashing at runtime. The migration is idempotent (`IF NOT EXISTS`) so it is safe for fresh installs too. `app/main.py` lifespan now runs `alembic upgrade head` after `create_all`.
- **`/logs` page 404**: Created missing Next.js page at `src/app/logs/page.tsx`. The user-facing "Logs" sidebar link was pointing to `/logs` but no page existed. The new page lists all processing runs with expandable per-email log details and pagination.
- **`/admin/logs` page 404**: Created missing Next.js page at `src/app/admin/logs/page.tsx`. The admin "Activity Logs" sidebar link was pointing to `/admin/logs` but no page existed. The new page shows all processing runs across all users with status filtering and pagination.
- **Black formatting**: `backend/app/api/v1/endpoints/admin.py` was not formatted correctly; reformatted to pass `black --check`.

## [0.1.0] - 2026-03-26

### Added
- **Semantic Release** (`release.yml`): Automated versioning and GitHub Release creation on every push to `main` using `python-semantic-release`. Reads conventional-commit prefixes (`feat:`, `fix:`, etc.) to determine the next version and updates `CHANGELOG.md`.
- **`pyproject.toml`**: Project metadata and `[tool.semantic_release]` configuration for `python-semantic-release`.
- **GitOps auto-deployment** (step in `ci.yml`): After a successful Docker build on `main`, a new `update-k8s-manifest` job checks out `christianlouis/k8s-cluster-state` (using the `GH_PAT` secret) and updates the backend and frontend image tags in `apps/gmail-puller/preprod/gmail-puller-stack.yaml` to the new `main-<sha>` image, then commits and pushes.
- **Processing logs & reporting** — users can now view the full history of polling runs and per-email delivery status:
  - **`GET /processing-runs`** — paginated list of all processing runs for the authenticated user's mailboxes (filterable by account and status).
  - **`GET /processing-runs/{id}`** — details for a single run.
  - **`GET /processing-runs/{id}/logs`** — per-email log entries (subject, sender, size, delivery status, error details) for a given run.
  - **`GET /mail-accounts/{id}/processing-runs`** — runs scoped to a single mailbox.
  - **`GET /mail-accounts/{id}/logs`** — all per-email log entries for a single mailbox.
- **Admin log endpoints** (superuser only):
  - **`GET /admin/processing-runs`** — all runs across every user, filterable by user ID, account ID, or status. Account and user email addresses are GDPR-pseudonymised.
  - **`GET /admin/processing-logs`** — all per-email log entries system-wide, filterable by user, account, run, or log level. Sender (`From:`) headers are pseudonymised via `mask_from_header()`; subjects are shown as-is (user-owned content).
- **`backend/app/core/gdpr.py`** — GDPR masking utilities: `mask_email()`, `mask_name()`, `mask_from_header()` for pseudonymising PII in admin views.
- **Worker now writes `ProcessingLog` entries per email** — subject, sender, size, delivery outcome and error detail are captured for every email processed by `process_mail_account`.
- **`/logs` page** — user-facing log page with a paginated processing-run table; each row expands inline to show the per-email log for that run (subject, masked sender, size, status).
- **`/admin/logs` page** — admin view with two tabs: *Processing Runs* (expandable, fetches per-email logs on demand) and *Per-Email Logs* (flat table with GDPR-masked sender addresses). Filterable by user ID and status/level.
- **Sidebar navigation** — added *Logs* link (user) and *Activity Logs* link (admin) to `DashboardLayout`.
- **Admin overview** — added *Activity Logs* card to `/admin` page.
- **Dashboard** — "Recent Processing Runs" table now reads from the new `/processing-runs` endpoint; shows account name and a *View all logs* link.
- **Apprise alerting**: New `NotificationService` using [Apprise](https://github.com/caronc/apprise) for multi-channel push notifications (Telegram, Slack, Discord, webhooks, and 80+ other services via a single URL scheme).
  - `send_user_notification` — sends to all enabled per-user Apprise channels on processing errors or failures.
  - `send_admin_notification` — sends to all enabled admin-wide channels for system events.
  - `test_notification` — validates an Apprise URL by dispatching a test message.
- **`NotificationConfig` model**: Added `name` (friendly label) and `apprise_url` (nullable Apprise URL) columns.
- **`AdminNotificationConfig` model**: New table (`admin_notification_configs`) for system-wide admin alert channels with `name`, `apprise_url`, `is_enabled`, `notify_on_errors`, `notify_on_system_events`, and `description` fields.
- **Notifications API** (`/api/v1/notifications`): Full CRUD endpoints (GET/POST/PUT/DELETE) plus a `/test` endpoint for user notification configs.
- **Admin Notifications API** (`/api/v1/admin/notifications`): Full CRUD + `/test` endpoints for admin notification configs, superuser-only.
- **Task integration**: `process_mail_account` now calls `send_user_notification` on Gmail credential revocation, per-email forwarding failures, and unhandled processing exceptions.
- **Configurable Gmail import labels**: Users can now define which Gmail labels are applied to imported messages from the Settings page. The default setup is opinionated: `{{source_email}}` (rendered to the mailbox address each message came from) plus `imported`, and a reset button restores those defaults instantly.
- **Prometheus metrics** (`/metrics` endpoint on the FastAPI backend, scraped every 15 s):
  - **HTTP layer** — `http_requests_total` (counter, labelled `method`/`endpoint`/`status_code`) and `http_request_duration_seconds` (histogram). Path segments that are numeric IDs are normalised to `{id}` to avoid label-set explosion.
  - **Mail processing** — `mail_processing_runs_total` (counter, by `status`: `completed` / `partial_failure` / `failed`), `mail_processing_emails_total` (counter, by `operation`: `fetched` / `forwarded` / `failed`), `mail_processing_duration_seconds` (histogram), `active_mail_accounts_total` (gauge — set each scheduler cycle).
  - **Gmail API** — `gmail_api_requests_total` (counter, by `operation` and `status`), `gmail_api_duration_seconds` (histogram, by `operation`), `gmail_token_refreshes_total` (counter), `gmail_credentials_invalidated_total` (counter).
  - **Authentication / OAuth** — `auth_logins_total` (counter, `method` × `status`), `auth_registrations_total` (counter, `method` × `status`), `oauth_callbacks_total` (counter, `provider` × `status`).
  - **Celery tasks** — `celery_tasks_total` (counter, `task_name` × `status`) and `celery_task_duration_seconds` (histogram, by `task_name`).
- **All metrics** defined as module-level singletons in `backend/app/core/metrics.py` (imported by HTTP middleware, task workers, GmailService, and auth endpoints).
- **Prometheus service** added to `docker-compose.new.yml` (port 9090, 30-day retention, config from `monitoring/prometheus.yml`).
- **Grafana service** added to `docker-compose.new.yml` (port 3001, auto-provisioned datasource + pre-built dashboard). Default credentials: `admin` / `admin`.
- **Pre-built Grafana dashboard** (`monitoring/grafana/dashboards/inboxconverge.json`) with five sections: Mail Processing, Gmail API, Authentication & OAuth, HTTP API, and Celery Workers. Dashboard auto-refreshes every 30 s.
- **Admin interface**: Superusers now have access to a dedicated Admin section in the sidebar with three pages:
  - **Admin Overview** (`/admin`): System-wide stats (total users, mail accounts, processing runs).
  - **Manage Users** (`/admin/users`): Table of all registered users with their subscription tier, status, mail account count, and last login. Admins can edit any user's name, email, plan, active status, and promote/demote admin (superuser) privileges. Users can be deleted (with confirmation).
  - **Manage Plans** (`/admin/plans`): Full CRUD for subscription plans—create, edit, and delete plans with fields for tier, name, pricing, max mailboxes, max emails/day, check interval, and support level.
- **Auto-promotion of admin email**: When the user whose email matches the `ADMIN_EMAIL` environment variable logs in or registers (via email/password or Google OAuth), they are automatically promoted to superuser. Default value is `christian@inboxconverge.com` (configurable via the `ADMIN_EMAIL` env var).
- **`is_superuser` field in API responses**: `GET /users/me` and all admin user endpoints now include `is_superuser` so the frontend can conditionally show admin UI.
- **New admin API endpoints** (all require superuser role):
  - `GET /admin/users` – List all users with mail account counts.
  - `GET /admin/users/{id}` – Get a single user's details.
  - `PUT /admin/users/{id}` – Update user details, plan, active status, and superuser flag.
  - `DELETE /admin/users/{id}` – Delete a user.
  - `GET /admin/plans` – List all subscription plans (including zero-price / inactive).
  - `POST /admin/plans` – Create a new subscription plan.
  - `PUT /admin/plans/{id}` – Update a subscription plan.
  - `DELETE /admin/plans/{id}` – Delete a subscription plan.
- **Admin badge in top bar**: Admin users see a purple shield icon and an "Admin" badge next to their email in the top navigation bar.
- **`DEFAULT_USER_TIER` env var**: Controls the subscription tier assigned to every new user on registration. Defaults to `free`. Set to `enterprise` (or any other tier) for B2B / Google Workspace installations where all employees should start on a zero-rate plan.
- **`ALLOWED_DOMAINS` env var**: Comma-separated list of permitted email domains (e.g. `company.com,subsidiary.com`). When set, only addresses from those domains may register or log in. Superusers always bypass this check. Empty (default) = no restriction (normal B2C mode).
- **Dynamic pricing section on landing page**: The home page now fetches `GET /subscriptions/plans` and renders a pricing section only when paid plans exist. In enterprise / all-zero-rate deployments the pricing section is silently hidden — the page just shows features and a "Get started free" CTA.
- **B2C copy and branding**: App renamed to **InboxConverge** throughout. Landing page hero, feature cards, how-it-works, and footer rewritten in a personal, consumer-friendly tone. Pricing updated to €0.99 / €1.99 / €2.99 per month for Good / Better / Best plans.
- **Impressum & Datenschutz pages**: Added `/impressum` (legal notice per § 5 TMG) and `/datenschutz` (comprehensive privacy policy covering GDPR/DSGVO, CCPA, LGPD, and other international regulations) as public pages. Footer links to both pages were added to the dashboard layout and the login page.
- **Gmail Debug Email**: New "Send Debug Email" button in the Gmail API settings section. When clicked, it injects a test email into the user's Gmail inbox via the Gmail API. The message includes the current date in the subject line and is automatically labelled with `test` and `imported`. Useful for verifying end-to-end Gmail API delivery without requiring a full mail-account polling cycle.
- **Unified Google OAuth flow**: Google Sign-In now requests all Gmail API scopes (`gmail.insert`, `gmail.labels`, `gmail.readonly`) in the same consent screen, so users no longer need a separate "Connect Gmail" step after signing in with Google. Gmail credentials are stored automatically on successful sign-in.
- **Architecture Decision Records ADR-003 through ADR-010**: Added eight new ADRs covering FastAPI web framework (ADR-003), PostgreSQL database (ADR-004), Celery task retry strategy (ADR-005), key management in production (ADR-006), JWT authentication (ADR-007), Next.js frontend (ADR-008), Gmail API email delivery (ADR-009), and hybrid configuration model (ADR-010).
- **Account enable/disable toggle**: `PATCH /mail-accounts/{id}/toggle` backend endpoint and a Power-icon toggle button on each account card in the UI. Disabled accounts are visually dimmed. Re-enabling an account that was in ERROR state resets its status to ACTIVE so the scheduler picks it up again.
- **Message deduplication tracking** (`DownloadedMessageId` table): Both POP3 and IMAP fetch paths now track downloaded message UIDs so the same message is never delivered twice, even when `delete_after_forward=False`.
- **Gmail API "one-click" OAuth grant flow**: New `GET /providers/gmail/authorize-url` and `POST /providers/gmail/callback` endpoints with offline access and long-lived refresh tokens.
- **Gmail token auto-refresh and persistence**: `GmailService` now records whether the `google-auth` library refreshed the access token during a Celery run and persists any new access token back to `GmailCredential`, eliminating unnecessary extra refresh calls.
- **Per-user SMTP relay configuration** (`UserSmtpConfig` table): New `GET/PUT/DELETE /users/smtp-config` endpoints let each user store their own SMTP relay. The Celery task checks for per-user SMTP first; falls back to the global `AppSetting` SMTP config if none is set.
- **Settings page** — Gmail & SMTP sections: Shows a "Gmail API Delivery" card with connection status and connect/re-authorise/disconnect buttons, plus an "SMTP Fallback" card for per-user SMTP relay credentials.
- **Celery scheduling fix**: `process_all_enabled_accounts` now polls all `is_enabled = True` accounts regardless of status, so transient errors are retried automatically.
- **Backend URL logged at startup**: The Next.js server now logs the resolved `BACKEND_URL` via `src/instrumentation.ts` when the server starts, making it easy to diagnose `ECONNREFUSED` proxy errors.
- **Dual-registry Docker deployment**: CI now builds separate backend and frontend images and pushes to both GHCR (`ghcr.io`) and private registry (`registry.cklnet.com`) using a matrix strategy.
- **Database-backed configuration**: `AppSetting` model and `ConfigService` for hybrid config (DB-first, env-var fallback). Admin API endpoints for managing settings (`GET/PUT/DELETE /api/v1/settings`). Default settings seeded into database on first startup (SMTP, processing, Gmail API, notifications).
- Unit tests for `ConfigService` (24 tests covering resolution order, CRUD, SMTP helper, defaults).
- Security validation for `SECRET_KEY` and `ENCRYPTION_KEY` on startup.
- CSRF protection middleware and security headers middleware (X-Frame-Options, CSP, HSTS).
- Rate limiting per user/tier.
- Comprehensive test infrastructure setup, CI/CD pipeline, and Dependabot configuration for automated dependency updates.

### Changed
- **Project renamed to InboxConverge**: All user-visible strings, Docker container names, database defaults, Docker image paths, monitoring job names, Grafana dashboard titles, and documentation updated from the legacy names (`POP3 to Gmail Forwarder`, `InboxRescue`, `gmail-puller`, `pop3_forwarder`, etc.) to **InboxConverge** / `inboxconverge`.
- **Domain updated to `inboxconverge.com`**: All contact and administrative email addresses now default to `@inboxconverge.com` (e.g. `christian@inboxconverge.com`).
- **Configurable contact details**: Two new environment variables make contact information overridable at deployment time:
  - `CONTACT_EMAIL` (default: `christian@inboxconverge.com`) — used by the frontend legal pages (Impressum, Datenschutz) and surfaced in the backend `Settings`.
  - `APP_URL` (default: `https://inboxconverge.com`) — the canonical public URL of the deployment.
  - `NEXT_PUBLIC_APP_NAME` (default: `InboxConverge`) — the application name shown in frontend legal-page titles; readable by Next.js server components at runtime.
- **Legacy script renamed**: `pop3_forwarder.py` → `inboxconverge.py`; root `Dockerfile` and `Makefile` updated accordingly.
- **Grafana dashboard file renamed**: `monitoring/grafana/dashboards/inboxrescue.json` → `inboxconverge.json`.
- **Note on encryption salt**: The internal PBKDF2 salt `b"pop3_forwarder_0"` in `backend/app/core/security.py` is intentionally **not** renamed — changing it would invalidate all existing encrypted credentials stored in the database.
- `NotificationConfigBase` schema: `name` field now has a default of `"My Notification"` (previously required); `apprise_url` is optional; `config` (channel-specific JSON) is optional with a default of `{}`.
- Configuration system now supports database-backed settings in addition to environment variables.
- Celery tasks (`tasks.py`) use `ConfigService` for SMTP config instead of raw `os.getenv()` calls.
- Bumped Docker Python base image from `3.11-slim` to `3.14-slim` and CI Python version from 3.11 to 3.14.
- Bumped CI Node.js version from 18 to 20.
- Bumped GitHub Actions: `actions/setup-python` v5 → v6, `actions/setup-node` v4 → v6, `docker/setup-buildx-action` v3 → v4, `codecov/codecov-action` v3 → v5.
- Bumped backend dependencies: pydantic 2.5.3 → 2.12.5, pydantic-settings 2.1.0 → 2.9.1, asyncpg 0.29.0 → 0.31.0, stripe 7.11.0 → 14.4.1, celery 5.3.6 → 5.6.2, redis 5.0.1 → 7.3.0.
- Bumped frontend dependencies: react 19.2.3 → 19.2.4, axios ^1.13.5 → ^1.13.6, eslint-config-next 16.1.6 → 16.2.1.

### Fixed
- **ESLint parse error in `DashboardLayout.tsx`**: Missing comma after `Bell` in the `lucide-react` named import caused a TypeScript parse error (`',' expected` at line 19). Added the missing comma.
- **`/processing-runs` endpoint 404s**: Routes in `logs.py` had a redundant `/processing-runs` path segment (the router was already mounted at `/processing-runs` in `api.py`). All three user-facing log endpoints now return correct results.
- **`NotificationConfigCreate` schema test failure**: `NotificationConfigBase.name` was a required field (`...`) but the unit test and the database column both use a default of `"My Notification"`. Changed the Pydantic field to `default="My Notification"` to match the DB default and allow callers to omit the field.
- Test email sender name corrected from "Christian Loris" to "Christian Krakau-Louis".
- **Mailbox limit always hit at 1**: The `subscription_plans` table was never seeded, so the limit check fell back to the env-var default. Fixed by seeding four default `SubscriptionPlan` rows at startup (Free, Good, Better, Best) and rewriting the limit check to look up the user's active plan from the DB first.
- **Zero-price plans hidden from public marketing**: `GET /subscriptions/plans` now only returns plans with `price_monthly > 0`.
- **TypeError: can't subtract offset-naive and offset-aware datetimes** in `process_mail_account` task when computing `duration_seconds`. After a database refresh, `started_at` may be returned as a naive datetime; it is now normalized to UTC before subtraction.
- **Admin user not seeing admin dashboard**: Added startup auto-promotion in `main.py` lifespan handler so users matching `ADMIN_EMAIL` are promoted to superuser on every application start.
- **Blank page on direct navigation to `/admin`, `/admin/users`, `/admin/plans`**: Moved superuser guard inside the `<AuthGuard>/<DashboardLayout>` tree so authentication always runs first.
- **Mailbox edit form**: Multiple fixes including username field pre-population, silent credential overwrite prevention, and all connection fields made editable.
- **Wizard grey screen**: `bg-opacity-75` replaced with `/75` opacity modifier syntax for Tailwind CSS v4 compatibility.
- **Mail account creation always failing**: Added missing `email_address` and `forward_to` required fields to the `AddMailAccountModal` form.
- **Settings page**: Implemented the Settings page (was a placeholder showing "coming soon").
- **`sqlalchemy.exc.DBAPIError`**: Fixed timezone-naive vs timezone-aware datetime mismatch by changing all `DateTime` columns to `DateTime(timezone=True)`.
- **`ProgrammingError` (cached statement plan is invalid)**: Disabled asyncpg prepared statement cache (`prepared_statement_cache_size=0`) to fix DDL-at-startup scenarios.
- **`UndefinedTableError` on first boot**: Lifespan startup event now calls `Base.metadata.create_all()` before attempting to seed default settings.
- **Frontend API calls hardcoded to `localhost:8000`**: Replaced `NEXT_PUBLIC_API_URL` mechanism with a Next.js Route Handler proxy at `/api/v1/[...path]` that reads `BACKEND_URL` at server startup.
- **Infinite spinning wheel on home page**: `authStore` no longer initialises `isLoading` as `true` unconditionally — it is now `false` when no access token exists in `localStorage`.
- **`useSearchParams()` Suspense boundary**: Wrapped `useSearchParams()` in a `Suspense` boundary in `frontend/src/app/auth/callback/page.tsx`.
- Various TypeScript build errors in accounts page, auth callback, and dashboard pages.
- **Node.js base image**: Upgraded from `node:18-alpine` to `node:20-alpine` to satisfy Next.js requirements.
- **Build attestation step removed**: `actions/attest-build-provenance` is not available for private user-owned repositories; removed it to fix CI.
- **ESLint downgraded**: Downgraded ESLint from `^10` to `^9` to fix `TypeError: contextOrFilename.getFilename is not a function`.
- **SQLAlchemy upgraded**: Upgraded from `2.0.25` to `2.0.48` to fix `AssertionError` on Python 3.14.
- JWT `sub` claim now encoded as string per JWT spec.
- Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` throughout backend.
- Replaced deprecated FastAPI `@app.on_event()` handlers with modern `lifespan` context manager.
- Replaced deprecated Pydantic `class Config` with `model_config = ConfigDict(...)` in all schemas.
- Open redirect vulnerability in OAuth `redirect_uri` fixed.

### Removed
- Removed CodeQL analysis from CI pipeline (was blocking builds).

### Security
- Upgraded `python-jose` from 3.3.0 to 3.5.0 to fix CVE: algorithm confusion vulnerability with OpenSSH ECDSA keys.
- Security headers added to all API responses.
- CSRF protection middleware added.
- Input validation improved for all endpoints.
- Credential handling audited and improved.
- Restricted overly permissive CORS `allow_methods` in backend.

## [1.0.0] - 2026-02-01

> **Note**: This was a pre-rewrite baseline version. The current v0.x series begins from v0.1.0 (2026-03-26).

### Added
- Multi-tenant SaaS backend with FastAPI
- JWT and OAuth2 (Google Sign-In) authentication
- Encrypted credential storage with Fernet
- Subscription management with Stripe integration
- PostgreSQL database with SQLAlchemy ORM
- Redis for caching and session management
- Celery for background task processing
- Apprise for multi-channel notifications
- Docker and docker-compose support
- Comprehensive API documentation with OpenAPI

### Changed
- Upgraded from single-user script to multi-tenant platform

## [0.0.1] - 2025-12-15

> **Note**: Legacy single-user script release (previously labelled `[0.1.0] - 2025-12-15 (Legacy Version)`).

### Added
- Initial release of single-user `inbox_converge.py` script
- Docker support with docker-compose
- Multiple POP3 account support
- Gmail forwarding via SMTP
- Rate limiting and throttling
- Error notifications via Postmarkapp
- Environment-based configuration
- Basic logging
