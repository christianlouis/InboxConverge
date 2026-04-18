import Link from 'next/link';
import type { Metadata } from 'next';

const APP_NAME = process.env.APP_NAME ?? 'InboxConverge';

export const metadata: Metadata = {
  title: `Terms of Service – ${APP_NAME}`,
};

const LAST_UPDATED = 'April 18, 2026';
const CONTACT_EMAIL = process.env.CONTACT_EMAIL ?? 'christian@inboxconverge.com';

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Terms of Service</h1>
        <p className="text-sm text-gray-500 mb-8">Last updated: {LAST_UPDATED}</p>

        {/* TOC */}
        <nav className="mb-8 p-4 bg-gray-50 rounded-md text-sm text-blue-700 space-y-1">
          <p className="font-semibold text-gray-700 mb-2">Contents</p>
          {[
            'Acceptance of Terms',
            'Service Description',
            'Account Registration',
            'Acceptable Use',
            'Google API Services',
            'Intellectual Property',
            'Data and Privacy',
            'Availability and Modifications',
            'Disclaimers',
            'Limitation of Liability',
            'Indemnification',
            'Termination',
            'Governing Law and Dispute Resolution',
            'Changes to These Terms',
            'Contact',
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
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            1. Acceptance of Terms
          </h2>
          <p className="text-gray-700 mb-3">
            By accessing or using {APP_NAME} (&ldquo;the Service&rdquo;), you agree
            to be bound by these Terms of Service (&ldquo;Terms&rdquo;). If you do
            not agree, do not use the Service.
          </p>
          <p className="text-gray-700">
            The Service is provided by Christian Louis IT Beratung, Alter
            Steinweg 3, 20459 Hamburg, Germany (&ldquo;we&rdquo;, &ldquo;us&rdquo;,
            &ldquo;our&rdquo;).
          </p>
        </section>

        {/* 2 */}
        <section id="section-2" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            2. Service Description
          </h2>
          <p className="text-gray-700 mb-3">
            {APP_NAME} is an email consolidation service that polls legacy
            POP3 and IMAP mailboxes on your behalf and delivers the retrieved
            messages directly into your Gmail inbox via the Gmail API. The
            Service is designed for personal and small-business use.
          </p>
          <p className="text-gray-700">
            The Service is not affiliated with, endorsed by, or sponsored by
            Google LLC. Gmail and Google are trademarks of Google LLC.
          </p>
        </section>

        {/* 3 */}
        <section id="section-3" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            3. Account Registration
          </h2>
          <ul className="list-disc list-inside text-gray-700 space-y-2">
            <li>
              You must be at least 16 years old (or the minimum age of digital
              consent in your jurisdiction) to create an account.
            </li>
            <li>
              You are responsible for maintaining the security of your account
              credentials and for all activity that occurs under your account.
            </li>
            <li>
              You must provide accurate, current, and complete information
              during registration and keep it up to date.
            </li>
            <li>
              You may not share your account with others or create accounts for
              the purpose of circumventing usage limits.
            </li>
          </ul>
        </section>

        {/* 4 */}
        <section id="section-4" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            4. Acceptable Use
          </h2>
          <p className="text-gray-700 mb-3">You agree not to use the Service to:</p>
          <ul className="list-disc list-inside text-gray-700 space-y-2">
            <li>
              Violate any applicable law, regulation, or third-party rights.
            </li>
            <li>
              Transmit unsolicited commercial messages (spam) or malicious
              content.
            </li>
            <li>
              Attempt to gain unauthorised access to any systems or networks.
            </li>
            <li>
              Interfere with or disrupt the integrity or performance of the
              Service.
            </li>
            <li>
              Circumvent or reverse-engineer any technical protection measures.
            </li>
            <li>
              Use the Service in a way that could impose an unreasonable load on
              our infrastructure.
            </li>
          </ul>
          <p className="text-gray-700 mt-3">
            We reserve the right to suspend or terminate accounts that violate
            this policy.
          </p>
        </section>

        {/* 5 */}
        <section id="section-5" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            5. Google API Services
          </h2>
          <p className="text-gray-700 mb-3">
            The Service uses the Google Gmail API to insert messages into your
            Gmail account. By connecting your Google account you also agree to
            Google&rsquo;s{' '}
            <a
              href="https://policies.google.com/terms"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-500"
            >
              Terms of Service
            </a>{' '}
            and{' '}
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
          <p className="text-gray-700 mb-3">
            Our use of data obtained via Google APIs complies with the{' '}
            <a
              href="https://developers.google.com/terms/api-services-user-data-policy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-500"
            >
              Google API Services User Data Policy
            </a>
            , including the Limited Use requirements. In particular, we use
            Google user data only to provide the email-import service described
            in these Terms and never for advertising or unrelated purposes.
          </p>
          <p className="text-gray-700">
            You can revoke {APP_NAME}&rsquo;s access to your Google account at
            any time from your{' '}
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
        </section>

        {/* 6 */}
        <section id="section-6" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            6. Intellectual Property
          </h2>
          <p className="text-gray-700 mb-3">
            The {APP_NAME} software is open-source and licensed under the
            terms of the project&rsquo;s{' '}
            <a
              href="https://github.com/christianlouis/InboxConverge/blob/main/LICENSE"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-500"
            >
              LICENSE
            </a>{' '}
            file. Nothing in these Terms grants you a licence to use the
            {' '}{APP_NAME} name or logo for purposes outside of the permitted
            open-source licence.
          </p>
          <p className="text-gray-700">
            You retain all rights to your own email content. We claim no
            ownership over any messages processed by the Service.
          </p>
        </section>

        {/* 7 */}
        <section id="section-7" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            7. Data and Privacy
          </h2>
          <p className="text-gray-700">
            Our collection and use of personal data is described in our{' '}
            <Link href="/privacy" className="text-blue-600 hover:text-blue-500">
              Privacy Policy
            </Link>
            , which forms part of these Terms. By using the Service you
            acknowledge and agree to the Privacy Policy.
          </p>
        </section>

        {/* 8 */}
        <section id="section-8" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            8. Availability and Modifications
          </h2>
          <p className="text-gray-700 mb-3">
            We aim to provide a reliable service but do not guarantee
            uninterrupted availability. We may modify, suspend, or discontinue
            the Service (or any part of it) at any time with reasonable notice
            where practicable.
          </p>
          <p className="text-gray-700">
            We may update these Terms from time to time. Material changes will
            be communicated via in-app notice or email. Continued use of the
            Service after changes take effect constitutes acceptance of the
            revised Terms.
          </p>
        </section>

        {/* 9 */}
        <section id="section-9" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            9. Disclaimers
          </h2>
          <p className="text-gray-700 mb-3">
            The Service is provided &ldquo;as is&rdquo; and &ldquo;as
            available&rdquo; without warranties of any kind, express or implied,
            including but not limited to warranties of merchantability, fitness
            for a particular purpose, or non-infringement.
          </p>
          <p className="text-gray-700">
            We do not warrant that the Service will be error-free, that defects
            will be corrected, or that the Service or its infrastructure are
            free of viruses or other harmful components.
          </p>
        </section>

        {/* 10 */}
        <section id="section-10" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            10. Limitation of Liability
          </h2>
          <p className="text-gray-700 mb-3">
            To the maximum extent permitted by applicable law, Christian Louis
            IT Beratung and its representatives shall not be liable for any
            indirect, incidental, special, consequential, or punitive damages,
            or any loss of profits, data, goodwill, or business opportunities
            arising out of or in connection with your use of the Service.
          </p>
          <p className="text-gray-700">
            Our aggregate liability for any claim relating to the Service is
            limited to the greater of (a) the amount you paid us in the 12
            months preceding the claim, or (b) €50.
          </p>
        </section>

        {/* 11 */}
        <section id="section-11" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            11. Indemnification
          </h2>
          <p className="text-gray-700">
            You agree to indemnify and hold harmless Christian Louis IT Beratung
            and its representatives from and against any claims, damages,
            losses, and expenses (including reasonable legal fees) arising out
            of your use of the Service, your violation of these Terms, or your
            violation of any third-party rights.
          </p>
        </section>

        {/* 12 */}
        <section id="section-12" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            12. Termination
          </h2>
          <p className="text-gray-700 mb-3">
            You may close your account at any time by contacting us at{' '}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-blue-600 hover:text-blue-500"
            >
              {CONTACT_EMAIL}
            </a>
            . Upon closure, all your data will be permanently deleted within
            30 days.
          </p>
          <p className="text-gray-700">
            We may suspend or terminate your account immediately if you breach
            these Terms or if we are required to do so by law.
          </p>
        </section>

        {/* 13 */}
        <section id="section-13" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            13. Governing Law and Dispute Resolution
          </h2>
          <p className="text-gray-700 mb-3">
            These Terms are governed by the laws of the Federal Republic of
            Germany, excluding its conflict-of-law provisions. The courts of
            Hamburg, Germany shall have exclusive jurisdiction over any dispute
            arising out of or in connection with these Terms, except where
            mandatory consumer-protection laws in your jurisdiction provide
            otherwise.
          </p>
          <p className="text-gray-700">
            EU consumers may also use the European Commission&rsquo;s Online
            Dispute Resolution platform:{' '}
            <a
              href="https://ec.europa.eu/consumers/odr"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-500"
            >
              https://ec.europa.eu/consumers/odr
            </a>
            . We are not obliged to participate in alternative dispute
            resolution procedures but will consider reasonable requests.
          </p>
        </section>

        {/* 14 */}
        <section id="section-14" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            14. Changes to These Terms
          </h2>
          <p className="text-gray-700">
            We reserve the right to modify these Terms at any time. We will
            provide at least 14 days&rsquo; notice of material changes via
            in-app notification or email. Your continued use of the Service
            after the effective date of revised Terms constitutes your
            acceptance of those Terms.
          </p>
        </section>

        {/* 15 */}
        <section id="section-15" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            15. Contact
          </h2>
          <p className="text-gray-700">
            For questions about these Terms, please contact:
          </p>
          <p className="text-gray-700 mt-2">
            Christian Louis IT Beratung<br />
            Alter Steinweg 3, 20459 Hamburg, Germany<br />
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-blue-600 hover:text-blue-500"
            >
              {CONTACT_EMAIL}
            </a>
          </p>
        </section>

        <div className="border-t border-gray-200 pt-4 flex flex-wrap gap-4 text-sm text-gray-500">
          <Link href="/privacy" className="hover:text-blue-600">
            Privacy Policy
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
