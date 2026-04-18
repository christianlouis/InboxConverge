import Link from 'next/link';
import type { Metadata } from 'next';

const APP_NAME = process.env.APP_NAME ?? 'InboxConverge';

export const metadata: Metadata = {
  title: `Privacy Policy – ${APP_NAME}`,
};

const LAST_UPDATED = 'April 18, 2026';
const CONTACT_EMAIL = process.env.CONTACT_EMAIL ?? 'christian@inboxconverge.com';

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
        <p className="text-sm text-gray-500 mb-8">Last updated: {LAST_UPDATED}</p>

        {/* TOC */}
        <nav className="mb-8 p-4 bg-gray-50 rounded-md text-sm text-blue-700 space-y-1">
          <p className="font-semibold text-gray-700 mb-2">Contents</p>
          {[
            'Who We Are',
            'Scope of This Policy',
            'What Data We Collect and Why',
            'Google API Services — Limited Use Disclosure',
            'Data Minimisation and Purpose Limitation',
            'Cookies and Similar Technologies',
            'Third-Party Services',
            'International Data Transfers',
            'Data Retention',
            'Data Security',
            'Your Rights (EU / EEA / UK / Switzerland)',
            'Additional Rights — United States (CCPA / CPRA)',
            'Additional Rights — Canada (PIPEDA / Law 25)',
            'Additional Rights — Other Jurisdictions',
            'Changes to This Policy',
            'Contact Us',
          ].map((title, i) => (
            <div key={i}>
              <a href={`#section-${i + 1}`} className="hover:underline">
                {i + 1}. {title}
              </a>
            </div>
          ))}
        </nav>

        {/* 1 */}
        <section id="section-1" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">1. Who We Are</h2>
          <p className="text-gray-700 mb-3">
            The data controller responsible for processing your personal data in
            accordance with the EU General Data Protection Regulation (GDPR) and
            equivalent data-protection laws worldwide is:
          </p>
          <p className="text-gray-700 mb-3">
            Christian Louis IT Beratung<br />
            Alter Steinweg 3, 20459 Hamburg, Germany
          </p>
          <p className="text-gray-700">
            Contact:{' '}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-blue-600 hover:text-blue-500"
            >
              {CONTACT_EMAIL}
            </a>
          </p>
          <p className="text-gray-700 mt-2">
            For all data-protection enquiries (access, erasure, correction,
            objection or complaints) please use the email address above. We
            respond within 30 days (or the period required by applicable law).
          </p>
        </section>

        {/* 2 */}
        <section id="section-2" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            2. Scope of This Policy
          </h2>
          <p className="text-gray-700">
            This policy applies to the {APP_NAME} web application and all
            associated services. It covers all users worldwide, including those
            in the European Union (EU), European Economic Area (EEA), United
            Kingdom, Switzerland, and the United States.
          </p>
          <p className="text-gray-700 mt-3">
            A German-language version of this policy is available at{' '}
            <Link href="/datenschutz" className="text-blue-600 hover:text-blue-500">
              /datenschutz
            </Link>
            .
          </p>
        </section>

        {/* 3 */}
        <section id="section-3" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            3. What Data We Collect and Why
          </h2>

          <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">
            3.1 Account and Authentication Data
          </h3>
          <p className="text-gray-700 mb-2">
            When you create an account or sign in with Google we may receive
            your name, email address, and profile picture from Google OAuth 2.0.
            We use this data solely to authenticate you and identify your
            account within {APP_NAME}.
          </p>
          <p className="text-gray-700 mb-3">
            Legal basis (GDPR Art. 6): (b) contract performance.
          </p>

          <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">
            3.2 Source Mailbox Credentials
          </h3>
          <p className="text-gray-700 mb-2">
            To fetch email from your legacy POP3 / IMAP accounts you provide
            server details and credentials. These are stored encrypted at rest
            using AES-256 and are never transmitted to any third party.
          </p>
          <p className="text-gray-700 mb-3">
            Legal basis (GDPR Art. 6): (b) contract performance.
          </p>

          <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">
            3.3 Gmail API OAuth Tokens
          </h3>
          <p className="text-gray-700 mb-2">
            To inject email into your Gmail account, {APP_NAME} requests the
            following Google OAuth 2.0 scopes:
          </p>
          <ul className="list-disc list-inside text-gray-700 space-y-2 mb-3">
            <li>
              <code className="text-xs bg-gray-100 px-1 rounded">
                https://www.googleapis.com/auth/gmail.insert
              </code>{' '}
              — inserts messages directly into your Gmail mailbox without
              sending them through SMTP.
            </li>
            <li>
              <code className="text-xs bg-gray-100 px-1 rounded">
                https://www.googleapis.com/auth/gmail.labels
              </code>{' '}
              — creates and manages Gmail labels so imported messages can be
              tagged (e.g. &ldquo;imported&rdquo;).
            </li>
            <li>
              <code className="text-xs bg-gray-100 px-1 rounded">
                https://www.googleapis.com/auth/gmail.readonly
              </code>{' '}
              — reads your Gmail profile (email address) to confirm the
              connection is working.
            </li>
          </ul>
          <p className="text-gray-700 mb-2">
            The resulting access and refresh tokens are stored encrypted at
            rest. Tokens are refreshed automatically by the service when they
            expire and the refreshed token is persisted back to the database.
            You can revoke access at any time from your{' '}
            <a
              href="https://myaccount.google.com/permissions"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-500"
            >
              Google Account permissions
            </a>{' '}
            page.
          </p>
          <p className="text-gray-700 mb-3">
            Legal basis (GDPR Art. 6): (b) contract performance.
          </p>

          <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">
            3.4 Email Content
          </h3>
          <p className="text-gray-700 mb-2">
            Email bodies and attachments are read from your source accounts and
            written to your Gmail account. They are processed in memory only;
            no email content is written to persistent storage other than within
            your own Gmail account.
          </p>
          <p className="text-gray-700 mb-3">
            Legal basis (GDPR Art. 6): (b) contract performance.
          </p>

          <h3 className="text-base font-semibold text-gray-700 mt-4 mb-2">
            3.5 Processing Logs
          </h3>
          <p className="text-gray-700 mb-2">
            We retain limited operational logs (message subject line, sender
            address, timestamp, success/failure flag) for up to 90 days. These
            are used to diagnose delivery problems and are accessible only to
            you and our operations team.
          </p>
          <p className="text-gray-700">
            Legal basis (GDPR Art. 6): (f) legitimate interests.
          </p>
        </section>

        {/* 4 — the critical Google Limited Use Disclosure */}
        <section id="section-4" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            4. Google API Services — Limited Use Disclosure
          </h2>
          <div className="border-l-4 border-blue-400 bg-blue-50 p-4 rounded-r-md mb-4">
            <p className="text-gray-800 font-medium mb-1">
              Limited Use Policy Compliance
            </p>
            <p className="text-gray-700 text-sm">
              {APP_NAME}&rsquo;s use of information received from Google APIs
              adheres to the{' '}
              <a
                href="https://developers.google.com/terms/api-services-user-data-policy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-500"
              >
                Google API Services User Data Policy
              </a>
              , including the Limited Use requirements.
            </p>
          </div>
          <p className="text-gray-700 mb-3">
            Specifically, {APP_NAME} commits to the following with respect to
            data obtained via Google APIs:
          </p>
          <ul className="list-disc list-inside text-gray-700 space-y-2">
            <li>
              <strong>Single purpose:</strong> Google user data is used only to
              deliver the core service — importing email from legacy mailboxes
              into your Gmail account.
            </li>
            <li>
              <strong>No transfer to third parties:</strong> We do not sell,
              rent, transfer, or disclose Google user data to third parties,
              except as necessary to provide the service (e.g. the Gmail API
              call itself) or as required by law.
            </li>
            <li>
              <strong>No advertising:</strong> We do not use Google user data
              to serve advertisements or for advertising-related purposes.
            </li>
            <li>
              <strong>No human reading:</strong> We do not allow humans to read
              your Gmail data unless you have given us explicit permission to do
              so (e.g. for diagnosing a reported technical problem), or it is
              required by law.
            </li>
            <li>
              <strong>No profiling:</strong> We do not use Google user data to
              build profiles, perform analytics, or engage in behavioural
              tracking beyond what is strictly necessary to operate the service.
            </li>
            <li>
              <strong>Security:</strong> All data obtained from Google APIs is
              stored with AES-256 encryption at rest and transmitted only over
              TLS-encrypted connections.
            </li>
          </ul>
        </section>

        {/* 5 */}
        <section id="section-5" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            5. Data Minimisation and Purpose Limitation
          </h2>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>
              We collect only the minimum personal data needed to operate the
              service.
            </li>
            <li>
              Email content is processed solely for the forwarding purpose you
              initiate.
            </li>
            <li>
              No advertising, behavioural tracking, or profiling is performed.
            </li>
            <li>No tracking cookies or analytics scripts are loaded.</li>
          </ul>
        </section>

        {/* 6 */}
        <section id="section-6" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            6. Cookies and Similar Technologies
          </h2>
          <p className="text-gray-700">
            The service uses only strictly necessary session cookies to
            maintain your authenticated session. These cookies are essential
            for the service to function and are exempt from prior-consent
            requirements under the EU ePrivacy Directive (Art. 5(3)). We do
            not use analytics cookies, advertising cookies, or tracking pixels.
          </p>
        </section>

        {/* 7 */}
        <section id="section-7" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            7. Third-Party Services
          </h2>
          <p className="text-gray-700 mb-2">
            <strong>Google OAuth / Gmail API:</strong> Authentication and Gmail
            delivery are handled via Google&rsquo;s APIs. Google processes your
            credentials according to its own{' '}
            <a
              href="https://policies.google.com/privacy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-500"
            >
              Privacy Policy
            </a>
            .
          </p>
          <p className="text-gray-700">
            <strong>No sale or sharing for advertising:</strong> We do not
            sell, rent, or share your personal data with third parties for
            advertising or marketing purposes.
          </p>
        </section>

        {/* 8 */}
        <section id="section-8" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            8. International Data Transfers
          </h2>
          <p className="text-gray-700">
            Where personal data is transferred outside the EEA we rely on
            appropriate safeguards, including Standard Contractual Clauses
            (SCCs) pursuant to EU Decision 2021/914/EU and European Commission
            adequacy decisions.
          </p>
        </section>

        {/* 9 */}
        <section id="section-9" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            9. Data Retention
          </h2>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>
              <strong>Session data:</strong> deleted on logout or session
              expiry.
            </li>
            <li>
              <strong>Account configuration and metadata:</strong> retained for
              the duration of your use of the service.
            </li>
            <li>
              <strong>Processing logs:</strong> retained for up to 90 days.
            </li>
            <li>
              <strong>OAuth tokens:</strong> stored encrypted and revocable at
              any time via your Google Account.
            </li>
            <li>
              <strong>Account deletion:</strong> all data associated with your
              account is permanently deleted within 30 days of account closure.
              You can request deletion by emailing{' '}
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="text-blue-600 hover:text-blue-500"
              >
                {CONTACT_EMAIL}
              </a>
              .
            </li>
          </ul>
        </section>

        {/* 10 */}
        <section id="section-10" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            10. Data Security
          </h2>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>AES-256 encryption of credentials at rest.</li>
            <li>TLS / HTTPS for all communications.</li>
            <li>Role-based access controls to protect personal data.</li>
            <li>CSRF protection for all state-changing requests.</li>
          </ul>
        </section>

        {/* 11 */}
        <section id="section-11" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            11. Your Rights (EU / EEA / UK / Switzerland)
          </h2>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>
              <strong>Right of access (Art. 15):</strong> a copy of the data
              held about you.
            </li>
            <li>
              <strong>Right to rectification (Art. 16):</strong> correction of
              inaccurate data.
            </li>
            <li>
              <strong>Right to erasure (Art. 17):</strong> deletion of your
              personal data.
            </li>
            <li>
              <strong>Right to restriction (Art. 18):</strong> temporary
              suspension of processing.
            </li>
            <li>
              <strong>Right to portability (Art. 20):</strong> data in a
              machine-readable format.
            </li>
            <li>
              <strong>Right to object (Art. 21):</strong> objection to
              processing based on legitimate interests.
            </li>
          </ul>
          <p className="text-gray-700 mt-3">
            To exercise any of these rights, contact us at{' '}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-blue-600 hover:text-blue-500"
            >
              {CONTACT_EMAIL}
            </a>
            . Complaints may be directed to the relevant supervisory authority
            (in Germany: BfDI).
          </p>
        </section>

        {/* 12 */}
        <section id="section-12" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            12. Additional Rights — United States (CCPA / CPRA)
          </h2>
          <p className="text-gray-700">
            If you are a California resident or resident of another US state
            with applicable privacy legislation, you have the right to know,
            delete, correct, and opt out of the sale of personal information.
            We do not sell or share personal information. Contact:{' '}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-blue-600 hover:text-blue-500"
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        {/* 13 */}
        <section id="section-13" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            13. Additional Rights — Canada (PIPEDA / Law 25)
          </h2>
          <p className="text-gray-700">
            If you are in Canada, you have the right to access, correct, and
            withdraw consent under PIPEDA and provincial privacy laws. Contact:{' '}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-blue-600 hover:text-blue-500"
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        {/* 14 */}
        <section id="section-14" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            14. Additional Rights — Other Jurisdictions
          </h2>
          <p className="text-gray-700">
            Users in Brazil (LGPD), Japan (APPI), Australia (Privacy Act 1988),
            South Korea (PIPA), Singapore (PDPA), and other markets may exercise
            equivalent data-protection rights under applicable national law.
            Contact:{' '}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-blue-600 hover:text-blue-500"
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        {/* 15 */}
        <section id="section-15" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            15. Changes to This Policy
          </h2>
          <p className="text-gray-700">
            We may update this policy from time to time. The &ldquo;Last
            updated&rdquo; date at the top of this page indicates when it was
            last revised. For material changes we will notify users via an
            in-app notice or email.
          </p>
        </section>

        {/* 16 */}
        <section id="section-16" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            16. Contact Us
          </h2>
          <p className="text-gray-700">
            For questions or concerns about this policy or your data, please
            contact:{' '}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-blue-600 hover:text-blue-500"
            >
              {CONTACT_EMAIL}
            </a>
          </p>
          <p className="text-gray-700 mt-2">
            Christian Louis IT Beratung<br />
            Alter Steinweg 3, 20459 Hamburg, Germany
          </p>
        </section>

        <div className="border-t border-gray-200 pt-4 flex flex-wrap gap-4 text-sm text-gray-500">
          <Link href="/terms" className="hover:text-blue-600">
            Terms of Service
          </Link>
          <Link href="/datenschutz" className="hover:text-blue-600">
            Datenschutz (DE)
          </Link>
          <Link href="/impressum" className="hover:text-blue-600">
            Impressum
          </Link>
          <Link href="/login" className="hover:text-blue-600">
            Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
