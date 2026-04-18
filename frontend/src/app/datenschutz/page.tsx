import Link from 'next/link';
import type { Metadata } from 'next';

const APP_NAME = process.env.APP_NAME ?? 'InboxConverge';

export const metadata: Metadata = {
  title: `Datenschutz – ${APP_NAME}`,
};

const LAST_UPDATED = 'March 26, 2026';
const CONTACT_EMAIL = process.env.CONTACT_EMAIL ?? 'christian@inboxconverge.com';

export default function DatenschutzPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Datenschutzhinweis
        </h1>
        <p className="text-sm text-gray-500 mb-8">
          Letzte Aktualisierung: {LAST_UPDATED}
        </p>

        {/* TOC */}
        <nav className="mb-8 p-4 bg-gray-50 rounded-md text-sm text-blue-700 space-y-1">
          <p className="font-semibold text-gray-700 mb-2">Inhalt</p>
          {[
            'Verantwortlicher',
            'Geltungsbereich dieser Datenschutzerklärung',
            'Datenerhebung & Zwecke',
            'Datenminimierung & Zweckbindung',
            'Verwendung von Cookies & ähnlichen Technologien',
            'Drittanbieter-Dienste',
            'Internationale Datenübertragungen',
            'Datenaufbewahrung',
            'Datensicherheit',
            'Ihre Rechte (EU / EWR / UK / Schweiz)',
            'Zusätzliche Rechte – Vereinigte Staaten (CCPA/CPRA)',
            'Zusätzliche Rechte – Kanada (PIPEDA / Gesetz 25)',
            'Zusätzliche Rechte – Lateinamerika (LGPD & andere)',
            'Zusätzliche Rechte – Asien-Pazifik & Japan',
            'Zusätzliche Rechte – Ukraine',
            'Aktualisierungen zu dieser Datenschutzerklärung',
          ].map((title, i) => (
            <div key={i}>
              <a href={`#section-${i + 1}`} className="hover:underline">
                {i + 1}. {title}
              </a>
            </div>
          ))}
        </nav>

        {/* Sections */}
        <section id="section-1" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            1. Verantwortlicher
          </h2>
          <p className="text-gray-700 mb-3">
            Der für die Verarbeitung Ihrer personenbezogenen Daten gemäß der
            EU-Datenschutz-Grundverordnung (DSGVO) und gleichwertiger
            Datenschutzgesetze weltweit verantwortliche Verantwortliche ist:
          </p>
          <p className="text-gray-700 mb-3">
            Christian Louis IT Beratung<br />
            Alter Steinweg 3, 20459 Hamburg, Deutschland
          </p>
          <p className="text-gray-700">
            Kontakt-E-Mail:{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-blue-600 hover:text-blue-500">
              {CONTACT_EMAIL}
            </a>
          </p>
          <p className="text-gray-700 mt-2">
            Bei allen datenschutzbezogenen Anfragen (Zugriff, Löschung,
            Berichtigung, Widerspruch oder Beschwerden) kontaktieren Sie uns
            bitte unter der obenstehenden E-Mail-Adresse. Wir werden innerhalb
            von 30 Tagen (oder dem durch geltendes Recht vorgeschriebenen
            Zeitraum) antworten.
          </p>
        </section>

        <section id="section-2" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            2. Geltungsbereich dieser Datenschutzerklärung
          </h2>
          <p className="text-gray-700 mb-3">
            Dieser Hinweis gilt für die {APP_NAME}-Webanwendung. Er gilt
            für alle Nutzer weltweit, einschließlich derjenigen in der
            Europäischen Union (EU), dem Europäischen Wirtschaftsraum (EWR),
            Deutschland, dem Vereinigten Königreich (UK), der Schweiz, der
            Ukraine, den Vereinigten Staaten (US), Kanada, Lateinamerika,
            dem asiatisch-pazifischen Raum und Japan.
          </p>
          <p className="text-gray-700">
            Eine englischsprachige Fassung dieser Datenschutzerklärung ist
            verfügbar unter:{' '}
            <Link href="/privacy" className="text-blue-600 hover:text-blue-500">
              /privacy
            </Link>
            .
          </p>
        </section>

        <section id="section-3" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            3. Datenerhebung &amp; Zwecke
          </h2>
          <p className="text-gray-700 mb-2">
            <strong>Benutzerauthentifizierung:</strong> Wir verwenden OAuth 2.0
            (Google) und optionale lokale Authentifizierung. Über OAuth können
            wir Ihren Namen, Ihre E-Mail-Adresse und Ihr Profilbild erhalten.
          </p>
          <p className="text-gray-700 mb-2">
            <strong>E-Mail-Verarbeitung:</strong> E-Mails, die von Ihren
            konfigurierten POP3-Konten abgerufen werden, werden ausschließlich
            für den Zweck der Weiterleitung an Gmail verarbeitet. Der
            E-Mail-Inhalt wird nicht länger gespeichert, als es betrieblich
            notwendig ist.
          </p>
          <p className="text-gray-700 mb-2">
            <strong>Audit-Protokolle:</strong> Wir führen begrenzte Protokolle
            (Aktionsart, Zeitstempel, Benutzeridentifikator), um die Integrität
            und Sicherheit des Dienstes zu gewährleisten.
          </p>
          <p className="text-gray-700">
            <strong>Rechtsgrundlage (DSGVO Art. 6):</strong> (1)(b)
            Vertragsdurchführung, (1)(c) Rechtliche Verpflichtung, (1)(f)
            Berechtigte Interessen.
          </p>
        </section>

        <section id="section-4" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            4. Datenminimierung &amp; Zweckbindung
          </h2>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>
              Wir erheben nur die minimalen personenbezogenen Daten, die zur
              Durchführung des Dienstes erforderlich sind.
            </li>
            <li>
              E-Mail-Inhalte werden ausschließlich für den von Ihnen
              initiierten Weiterleitungszweck verarbeitet.
            </li>
            <li>
              Es wird keine Werbung, Verhaltensverfolgung oder Profilierung
              durchgeführt.
            </li>
            <li>
              Es werden keine Tracking-Cookies oder Analysescripts geladen.
            </li>
          </ul>
        </section>

        <section id="section-5" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            5. Verwendung von Cookies &amp; ähnlichen Technologien
          </h2>
          <p className="text-gray-700">
            Der Dienst verwendet nur unbedingt erforderliche Sitzungscookies,
            um Ihre authentifizierte Sitzung aufrechtzuerhalten. Diese Cookies
            sind für die Funktion des Dienstes unerlässlich und sind von den
            Anforderungen an vorherige Zustimmung gemäß der EU-E-Privacy-
            Richtlinie (Art. 5(3)) ausgenommen. Wir verwenden keine
            Analyse-Cookies, Werbe-Cookies oder Tracking-Pixel.
          </p>
        </section>

        <section id="section-6" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            6. Drittanbieter-Dienste
          </h2>
          <p className="text-gray-700 mb-2">
            <strong>OAuth-Anbieter (Google):</strong> Wenn Sie sich über OAuth
            authentifizieren, verarbeitet der jeweilige Anbieter Ihre
            Anmeldeinformationen gemäß seiner eigenen Datenschutzrichtlinie.
          </p>
          <p className="text-gray-700 mb-2">
            <strong>Gmail API:</strong> E-Mails werden über die Gmail API in
            Ihr Gmail-Konto eingespielt. Ihre OAuth-Zugangsdaten werden
            verschlüsselt gespeichert.
          </p>
          <p className="text-gray-700">
            <strong>Kein Verkauf oder Teilen für Werbung:</strong> Wir
            verkaufen, vermieten oder teilen Ihre personenbezogenen Daten
            nicht mit Dritten zu Werbungs- oder Marketingzwecken.
          </p>
        </section>

        <section id="section-7" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            7. Internationale Datenübertragungen
          </h2>
          <p className="text-gray-700">
            Wenn personenbezogene Daten außerhalb des EWR übertragen werden,
            verlassen wir uns auf geeignete Schutzmaßnahmen, einschließlich
            Standardvertragsklauseln (SCCs) gemäß EU-Beschluss 2021/914/EU
            sowie Angemessenheitsentscheidungen der Europäischen Kommission.
          </p>
        </section>

        <section id="section-8" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            8. Datenaufbewahrung
          </h2>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>
              <strong>Sitzungsdaten:</strong> Wird gelöscht, wenn Sie sich
              abmelden oder nach Ablauf der Sitzung.
            </li>
            <li>
              <strong>Kontokonfiguration & Metadaten:</strong> Für die Dauer
              Ihrer Nutzung des Dienstes aufbewahrt.
            </li>
            <li>
              <strong>Audit-Protokolle:</strong> Für bis zu 90 Tage
              aufbewahrt.
            </li>
            <li>
              <strong>OAuth-Token:</strong> In verschlüsselter Form gespeichert
              und jederzeit über Ihren OAuth-Anbieter widerrufbar.
            </li>
          </ul>
        </section>

        <section id="section-9" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            9. Datensicherheit
          </h2>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>Verschlüsselung von Anmeldeinformationen im Ruhezustand.</li>
            <li>
              Transport Layer Security (TLS/HTTPS) für alle Kommunikationen.
            </li>
            <li>
              Rollenbasierte Zugriffskontrollen zum Schutz personenbezogener
              Daten.
            </li>
            <li>CSRF-Schutz für alle zustandsändernden Anfragen.</li>
          </ul>
        </section>

        <section id="section-10" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            10. Ihre Rechte (EU / EWR / UK / Schweiz)
          </h2>
          <ul className="list-disc list-inside text-gray-700 space-y-1">
            <li>
              <strong>Recht auf Zugang (Art. 15):</strong> Kopie der über Sie
              gespeicherten Daten.
            </li>
            <li>
              <strong>Recht auf Berichtigung (Art. 16):</strong> Korrektur
              ungenauer Daten.
            </li>
            <li>
              <strong>Recht auf Löschung (Art. 17):</strong> Löschung Ihrer
              persönlichen Daten.
            </li>
            <li>
              <strong>Recht auf Einschränkung (Art. 18):</strong> Vorübergehende
              Aussetzung der Verarbeitung.
            </li>
            <li>
              <strong>Recht auf Datenübertragbarkeit (Art. 20):</strong> Daten
              in maschinenlesbarem Format.
            </li>
            <li>
              <strong>Widerspruchsrecht (Art. 21):</strong> Widerspruch gegen
              Verarbeitung auf Basis berechtigter Interessen.
            </li>
          </ul>
          <p className="text-gray-700 mt-3">
            Um eines dieser Rechte auszuüben, kontaktieren Sie uns unter{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-blue-600 hover:text-blue-500">
              {CONTACT_EMAIL}
            </a>
            . Beschwerden können an die zuständige Datenschutzbehörde (in
            Deutschland: BfDI) gerichtet werden.
          </p>
        </section>

        <section id="section-11" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            11. Zusätzliche Rechte – Vereinigte Staaten (CCPA / CPRA)
          </h2>
          <p className="text-gray-700">
            Wenn Sie ein Bewohner Kaliforniens oder eines anderen US-
            Bundesstaates mit anwendbarer Datenschutzgesetzgebung sind, haben
            Sie das Recht auf Auskunft, Löschung, Berichtigung und Widerspruch
            gegen den Verkauf persönlicher Daten. Wir verkaufen oder teilen
            keine personenbezogenen Informationen. Kontakt:{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-blue-600 hover:text-blue-500">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        <section id="section-12" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            12. Zusätzliche Rechte – Kanada (PIPEDA / Gesetz 25)
          </h2>
          <p className="text-gray-700">
            Wenn Sie sich in Kanada befinden, haben Sie das Recht auf Zugang,
            Korrektur und Widerruf der Zustimmung gemäß PIPEDA und den
            provinziellen Datenschutzgesetzen. Kontakt:{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-blue-600 hover:text-blue-500">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        <section id="section-13" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            13. Zusätzliche Rechte – Lateinamerika (LGPD &amp; andere)
          </h2>
          <p className="text-gray-700">
            Brasilianische Nutzer haben gemäß LGPD (Lei 13.709/2018) das Recht
            auf Bestätigung der Verarbeitung, Zugang, Berichtigung, Löschung
            und Datenübertragbarkeit. Nutzer in anderen lateinamerikanischen
            Ländern können entsprechende Rechte gemäß nationalem Recht ausüben.
            Kontakt:{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-blue-600 hover:text-blue-500">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        <section id="section-14" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            14. Zusätzliche Rechte – Asien-Pazifik &amp; Japan
          </h2>
          <p className="text-gray-700">
            Nutzer in Japan (APPI), Australien (Privacy Act 1988), Südkorea
            (PIPA) sowie anderen APJ-Märkten (Singapur PDPA, Neuseeland, Indien
            DPDP) können entsprechende Datenschutzrechte ausüben. Kontakt:{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-blue-600 hover:text-blue-500">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        <section id="section-15" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            15. Zusätzliche Rechte – Ukraine
          </h2>
          <p className="text-gray-700">
            Nutzer in der Ukraine sind nach dem ukrainischen Gesetz &bdquo;Über den
            Schutz persönlicher Daten&ldquo; (Nr. 2297-VI) geschützt. Ihre Rechte
            umfassen Zugang, Berichtigung, Sperrung, Löschung und das Recht
            auf Widerspruch gegen die Verarbeitung. Kontakt:{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-blue-600 hover:text-blue-500">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        <section id="section-16" className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">
            16. Aktualisierungen zu dieser Datenschutzerklärung
          </h2>
          <p className="text-gray-700">
            Wir können diese Mitteilung von Zeit zu Zeit aktualisieren. Das
            Datum &bdquo;Letzte Aktualisierung&ldquo; am Anfang dieser Seite gibt an, wann
            die Mitteilung zuletzt überarbeitet wurde. Bei wesentlichen
            Änderungen werden wir die Nutzer durch eine Benachrichtigung in der
            Anwendung oder per E-Mail informieren.
          </p>
          <p className="text-gray-700 mt-3">
            Bei Fragen oder Bedenken kontaktieren Sie uns unter{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-blue-600 hover:text-blue-500">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>

        <div className="border-t border-gray-200 pt-4 flex flex-wrap gap-4 text-sm text-gray-500">
          <Link href="/privacy" className="hover:text-blue-600">
            Privacy Policy (EN)
          </Link>
          <Link href="/terms" className="hover:text-blue-600">
            Terms of Service
          </Link>
          <Link href="/impressum" className="hover:text-blue-600">
            Impressum
          </Link>
          <Link href="/login" className="hover:text-blue-600">
            Zurück zur Anmeldung
          </Link>
        </div>
      </div>
    </div>
  );
}
