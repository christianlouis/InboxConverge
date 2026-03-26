'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { userApi, SubscriptionPlan } from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Mail, ArrowRight, Shield, Zap, Clock, Check } from 'lucide-react';

async function fetchPublicPlans(): Promise<SubscriptionPlan[]> {
  const res = await api.get<SubscriptionPlan[]>('/subscriptions/plans');
  return res.data;
}

function PricingCard({ plan }: { plan: SubscriptionPlan }) {
  const yearlyMonthly = plan.price_yearly
    ? (plan.price_yearly / 12).toFixed(2)
    : null;

  return (
    <div className="bg-white rounded-xl shadow-md p-8 flex flex-col border border-gray-100 hover:shadow-lg transition-shadow">
      <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
      <p className="mt-2 text-sm text-gray-500 flex-1">{plan.description}</p>
      <div className="mt-6">
        <span className="text-4xl font-extrabold text-gray-900">
          €{plan.price_monthly.toFixed(2)}
        </span>
        <span className="text-gray-500">/month</span>
        {yearlyMonthly && (
          <p className="text-xs text-green-600 mt-1">
            or €{yearlyMonthly}/mo billed yearly (€{plan.price_yearly?.toFixed(2)})
          </p>
        )}
      </div>
      <ul className="mt-6 space-y-2 text-sm text-gray-600">
        <li className="flex items-center gap-2">
          <Check className="h-4 w-4 text-green-500 shrink-0" />
          {plan.max_mail_accounts === 1
            ? '1 mailbox'
            : `Up to ${plan.max_mail_accounts} mailboxes`}
        </li>
        <li className="flex items-center gap-2">
          <Check className="h-4 w-4 text-green-500 shrink-0" />
          Checked every {plan.check_interval_minutes} minute{plan.check_interval_minutes > 1 ? 's' : ''}
        </li>
        <li className="flex items-center gap-2">
          <Check className="h-4 w-4 text-green-500 shrink-0" />
          Up to {plan.max_emails_per_day.toLocaleString()} emails/day
        </li>
      </ul>
      <Link
        href="/register"
        className="mt-8 block text-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
      >
        Get started
      </Link>
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const { isLoading, setUser, setLoading } = useAuthStore();

  useEffect(() => {
    const token =
      typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (!token) return;

    userApi
      .getCurrentUser()
      .then((userData) => {
        setUser(userData);
        router.push('/dashboard');
      })
      .catch((err) => {
        console.error('Auth check failed on home page:', err);
        localStorage.removeItem('access_token');
        setLoading(false);
      });
  }, [router, setUser, setLoading]);

  const { data: plans } = useQuery({
    queryKey: ['public-plans'],
    queryFn: fetchPublicPlans,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const hasPaidPlans = plans && plans.length > 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <Mail className="h-8 w-8 text-blue-600 mr-2" />
              <h1 className="text-2xl font-bold text-gray-900">InboxConverge</h1>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/login"
                className="text-gray-700 hover:text-gray-900 font-medium"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Sign Up Free
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">

        {/* Hero */}
        <div className="text-center">
          <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-6">
            Your old inboxes,{' '}
            <span className="text-blue-600">delivered to Gmail.</span>
          </h2>
          <p className="text-xl text-gray-600 mb-4 max-w-2xl mx-auto">
            You know the ones — that GMX account from 2009, the old ISP address your
            bank still sends to, the Hotmail you gave out in school. InboxConverge
            quietly polls them all and drops everything into your Gmail. Set it once,
            forget it exists.
          </p>
          <p className="text-base text-gray-500 mb-8 max-w-xl mx-auto">
            No forwarding rules to configure. No email clients to keep open.
            Just your mail, where you actually read it.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link
              href="/register"
              className="flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-lg font-medium"
            >
              Get Started — it&apos;s free
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
            <Link
              href="/login"
              className="px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-lg font-medium"
            >
              Sign In
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="mt-20 grid md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex items-center justify-center h-12 w-12 rounded-md bg-blue-500 text-white mb-4">
              <Zap className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Auto-detects everything
            </h3>
            <p className="text-gray-600">
              Type your old email address and InboxConverge figures out the server
              settings. No Googling port numbers required.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex items-center justify-center h-12 w-12 rounded-md bg-green-500 text-white mb-4">
              <Clock className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Runs in the background
            </h3>
            <p className="text-gray-600">
              Checks your old inboxes on a schedule you choose — from every minute
              to once a day. New mail appears in Gmail as if it was always there.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex items-center justify-center h-12 w-12 rounded-md bg-purple-500 text-white mb-4">
              <Shield className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Your passwords stay yours
            </h3>
            <p className="text-gray-600">
              Credentials are encrypted at rest and never shared. All connections
              use SSL/TLS and Gmail delivery uses OAuth2 — no app passwords needed.
            </p>
          </div>
        </div>

        {/* How It Works */}
        <div className="mt-20">
          <h3 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Three steps and you&apos;re done
          </h3>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="flex items-center justify-center h-16 w-16 rounded-full bg-blue-100 text-blue-600 text-2xl font-bold mx-auto mb-4">
                1
              </div>
              <h4 className="text-xl font-semibold text-gray-900 mb-2">Add your old inbox</h4>
              <p className="text-gray-600">
                Paste the email address — InboxConverge auto-detects the POP3/IMAP
                settings in seconds.
              </p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center h-16 w-16 rounded-full bg-blue-100 text-blue-600 text-2xl font-bold mx-auto mb-4">
                2
              </div>
              <h4 className="text-xl font-semibold text-gray-900 mb-2">Connect Gmail</h4>
              <p className="text-gray-600">
                Sign in with Google once. InboxConverge delivers mail directly into
                your inbox using the Gmail API — no SMTP relay needed.
              </p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center h-16 w-16 rounded-full bg-blue-100 text-blue-600 text-2xl font-bold mx-auto mb-4">
                3
              </div>
              <h4 className="text-xl font-semibold text-gray-900 mb-2">Close the tab</h4>
              <p className="text-gray-600">
                Seriously, that&apos;s it. Your mail arrives automatically from now on.
                Check the dashboard whenever you like, but you won&apos;t need to.
              </p>
            </div>
          </div>
        </div>

        {/* Pricing — only rendered when paid plans exist (hidden in enterprise/all-free mode) */}
        {hasPaidPlans && (
          <div className="mt-24">
            <h3 className="text-3xl font-bold text-center text-gray-900 mb-4">
              Pricing
            </h3>
            <p className="text-center text-gray-500 mb-12 max-w-xl mx-auto">
              Start free. Upgrade if you need more inboxes or faster checks.
              Cancel any time — no questions, no fuss.
            </p>
            <div className={`grid gap-8 ${plans.length === 1 ? 'max-w-sm mx-auto' : plans.length === 2 ? 'md:grid-cols-2 max-w-2xl mx-auto' : 'md:grid-cols-3'}`}>
              {plans.map((plan) => (
                <PricingCard key={plan.id} plan={plan} />
              ))}
            </div>
            <p className="mt-8 text-center text-sm text-gray-500">
              All paid plans include a{' '}
              <span className="font-medium">free tier</span> when you first sign up
              — no credit card required.
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-20 border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-gray-600 text-sm">
            © {new Date().getFullYear()} InboxConverge — made for people, not enterprises.
          </p>
        </div>
      </footer>
    </div>
  );
}
