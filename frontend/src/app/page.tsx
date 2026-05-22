'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { userApi, SubscriptionPlan } from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { ArrowRight, Shield, Zap, Clock, Check } from 'lucide-react';
import { BrandMark } from '@/components/BrandMark';

async function fetchPublicPlans(): Promise<SubscriptionPlan[]> {
  const res = await api.get<SubscriptionPlan[]>('/subscriptions/plans');
  return res.data;
}

function PricingCard({ plan }: { plan: SubscriptionPlan }) {
  const yearlyMonthly = plan.price_yearly
    ? (plan.price_yearly / 12).toFixed(2)
    : null;

  return (
    <div className="ic-card flex flex-col p-8 transition-transform hover:-translate-y-0.5">
      <h3 className="text-xl font-bold text-slate-950">{plan.name}</h3>
      <p className="mt-2 text-sm text-slate-500 flex-1">{plan.description}</p>
      <div className="mt-6">
        <span className="text-4xl font-extrabold text-slate-950">
          €{plan.price_monthly.toFixed(2)}
        </span>
        <span className="text-slate-500">/month</span>
        {yearlyMonthly && (
          <p className="text-xs text-[#11834d] mt-1">
            or €{yearlyMonthly}/mo billed yearly (€{plan.price_yearly?.toFixed(2)})
          </p>
        )}
      </div>
      <ul className="mt-6 space-y-2 text-sm text-slate-600">
        <li className="flex items-center gap-2">
          <Check className="h-4 w-4 text-[#11834d] shrink-0" />
          {plan.max_mail_accounts === 1
            ? '1 mailbox'
            : `Up to ${plan.max_mail_accounts} mailboxes`}
        </li>
        <li className="flex items-center gap-2">
          <Check className="h-4 w-4 text-[#11834d] shrink-0" />
          Checked every {plan.check_interval_minutes} minute{plan.check_interval_minutes > 1 ? 's' : ''}
        </li>
        <li className="flex items-center gap-2">
          <Check className="h-4 w-4 text-[#11834d] shrink-0" />
          Up to {plan.max_emails_per_day.toLocaleString()} emails/day
        </li>
      </ul>
      <Link
        href="/register"
        className="ic-button-primary mt-8 w-full"
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
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-[#d9e3f2] bg-white/90 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <BrandMark />
            <div className="flex items-center gap-4">
              <Link
                href="/login"
                className="font-semibold text-slate-700 hover:text-slate-950"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="ic-button-primary"
              >
                Sign Up Free
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">

        {/* Hero */}
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="mb-6 text-4xl font-extrabold leading-tight text-slate-950 sm:text-6xl">
            Your old inboxes, delivered to Gmail.
          </h2>
          <p className="mx-auto mb-4 max-w-2xl text-xl leading-8 text-slate-600">
            You know the ones — that GMX account from 2009, the old ISP address your
            bank still sends to, the Hotmail you gave out in school. InboxConverge
            quietly polls them all and drops everything into your Gmail. Set it once,
            forget it exists.
          </p>
          <p className="text-base text-slate-500 mb-8 max-w-xl mx-auto">
            No forwarding rules to configure. No email clients to keep open.
            Just your mail, where you actually read it.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link
              href="/register"
              className="ic-button-primary min-h-12 px-6 text-base"
            >
              Get Started — it&apos;s free
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
            <Link
              href="/login"
              className="ic-button-secondary min-h-12 px-6 text-base"
            >
              Sign In
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="mt-20 grid md:grid-cols-3 gap-8">
          <div className="ic-card p-6">
            <div className="flex items-center justify-center h-12 w-12 rounded-md bg-[#0b63f6] text-white mb-4">
              <Zap className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-950 mb-2">
              Auto-detects everything
            </h3>
            <p className="text-slate-600">
              Type your old email address and InboxConverge figures out the server
              settings. No Googling port numbers required.
            </p>
          </div>

          <div className="ic-card p-6">
            <div className="flex items-center justify-center h-12 w-12 rounded-md bg-[#11834d] text-white mb-4">
              <Clock className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-950 mb-2">
              Runs in the background
            </h3>
            <p className="text-slate-600">
              Checks your old inboxes on a schedule you choose — from every minute
              to once a day. New mail appears in Gmail as if it was always there.
            </p>
          </div>

          <div className="ic-card p-6">
            <div className="flex items-center justify-center h-12 w-12 rounded-md bg-[#10213f] text-white mb-4">
              <Shield className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-950 mb-2">
              Your passwords stay yours
            </h3>
            <p className="text-slate-600">
              Credentials are encrypted at rest and never shared. All connections
              use SSL/TLS and Gmail delivery uses OAuth2 — no app passwords needed.
            </p>
          </div>
        </div>

        {/* How It Works */}
        <div className="mt-20">
          <h3 className="text-3xl font-extrabold text-center text-slate-950 mb-12">
            Three steps and you&apos;re done
          </h3>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="flex items-center justify-center h-16 w-16 rounded-full bg-[#e7f0ff] text-[#0b63f6] text-2xl font-bold mx-auto mb-4">
                1
              </div>
              <h4 className="text-xl font-bold text-slate-950 mb-2">Add your old inbox</h4>
              <p className="text-slate-600">
                Paste the email address — InboxConverge auto-detects the POP3/IMAP
                settings in seconds.
              </p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center h-16 w-16 rounded-full bg-[#e7f0ff] text-[#0b63f6] text-2xl font-bold mx-auto mb-4">
                2
              </div>
              <h4 className="text-xl font-bold text-slate-950 mb-2">Connect Gmail</h4>
              <p className="text-slate-600">
                Sign in with Google once. InboxConverge delivers mail directly into
                your inbox using the Gmail API — no SMTP relay needed.
              </p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center h-16 w-16 rounded-full bg-[#e7f0ff] text-[#0b63f6] text-2xl font-bold mx-auto mb-4">
                3
              </div>
              <h4 className="text-xl font-bold text-slate-950 mb-2">Close the tab</h4>
              <p className="text-slate-600">
                Seriously, that&apos;s it. Your mail arrives automatically from now on.
                Check the dashboard whenever you like, but you won&apos;t need to.
              </p>
            </div>
          </div>
        </div>

        {/* Pricing — only rendered when paid plans exist (hidden in enterprise/all-free mode) */}
        {hasPaidPlans && (
          <div className="mt-24">
            <h3 className="text-3xl font-extrabold text-center text-slate-950 mb-4">
              Pricing
            </h3>
            <p className="text-center text-slate-500 mb-12 max-w-xl mx-auto">
              Start free. Upgrade if you need more inboxes or faster checks.
              Cancel any time — no questions, no fuss.
            </p>
            <div className={`grid gap-8 ${plans.length === 1 ? 'max-w-sm mx-auto' : plans.length === 2 ? 'md:grid-cols-2 max-w-2xl mx-auto' : 'md:grid-cols-3'}`}>
              {plans.map((plan) => (
                <PricingCard key={plan.id} plan={plan} />
              ))}
            </div>
            <p className="mt-8 text-center text-sm text-slate-500">
              All paid plans include a{' '}
              <span className="font-medium">free tier</span> when you first sign up
              — no credit card required.
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-20 border-t border-[#d9e3f2] bg-[#fbfdff]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-slate-600 text-sm mb-3">
            © {new Date().getFullYear()} InboxConverge — made for people, not enterprises.
          </p>
          <div className="flex justify-center gap-4 text-xs text-slate-400">
            <Link href="/privacy" className="hover:text-slate-600 transition-colors">
              Privacy Policy
            </Link>
            <Link href="/terms" className="hover:text-slate-600 transition-colors">
              Terms of Service
            </Link>
            <Link href="/impressum" className="hover:text-slate-600 transition-colors">
              Impressum
            </Link>
            <Link href="/datenschutz" className="hover:text-slate-600 transition-colors">
              Datenschutz
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
