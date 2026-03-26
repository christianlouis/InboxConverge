import Link from 'next/link';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Impressum – POP3 Forwarder',
};

export default function ImpressumPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Impressum</h1>

        <section className="mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">
            Angaben gemäß § 5 TMG
          </h2>
          <p className="text-gray-700">
            Christian Louis IT Beratung<br />
            Alter Steinweg 3<br />
            20459 Hamburg<br />
            Deutschland
          </p>
        </section>

        <section className="mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">
            Vertreten durch
          </h2>
          <p className="text-gray-700">Christian Krakau-Louis</p>
        </section>

        <section className="mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Kontakt</h2>
          <p className="text-gray-700">
            Fax: +49 40 97074609<br />
            E-Mail:{' '}
            <a
              href="mailto:christianlouis@gmail.com"
              className="text-blue-600 hover:text-blue-500"
            >
              christianlouis@gmail.com
            </a>
          </p>
        </section>

        <section className="mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">
            Umsatzsteuer-Identifikationsnummer
          </h2>
          <p className="text-gray-700">
            Umsatzsteuer-Identifikationsnummer gemäß § 27a Umsatzsteuergesetz:
            <br />
            DE202899017
          </p>
        </section>

        <section className="mb-8">
          <p className="text-gray-700">
            Dieses Projekt ist Teil einer Open-Source-Initiative. Alle Rechte
            vorbehalten.
          </p>
        </section>

        <div className="border-t border-gray-200 pt-4 flex gap-4 text-sm text-gray-500">
          <Link href="/datenschutz" className="hover:text-blue-600">
            Datenschutz
          </Link>
          <Link href="/login" className="hover:text-blue-600">
            Zurück zur Anmeldung
          </Link>
        </div>
      </div>
    </div>
  );
}
