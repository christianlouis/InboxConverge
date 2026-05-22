'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authApi } from '@/lib/api';
import { BrandMark } from '@/components/BrandMark';

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);

    try {
      await authApi.register({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
      });
      
      // Auto-login after registration
      const loginResponse = await authApi.login({
        username: formData.email,
        password: formData.password,
      });
      localStorage.setItem('access_token', loginResponse.access_token);
      
      router.push('/dashboard');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f7faff] px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Link href="/">
            <BrandMark />
          </Link>
        </div>
        <div className="ic-panel p-8">
        <div>
          <h2 className="text-center text-3xl font-extrabold text-slate-950">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-slate-500">
            Start consolidating external mailboxes into Gmail.
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label htmlFor="full_name" className="block text-sm font-bold text-slate-700">
                Full Name
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="ic-focus mt-1 relative block w-full rounded-md border border-[#b8c8df] px-3 py-2.5 text-slate-950 placeholder-slate-400 focus:border-[#0b63f6] sm:text-sm"
                placeholder="John Doe"
              />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-bold text-slate-700">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="ic-focus mt-1 relative block w-full rounded-md border border-[#b8c8df] px-3 py-2.5 text-slate-950 placeholder-slate-400 focus:border-[#0b63f6] sm:text-sm"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-bold text-slate-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="ic-focus mt-1 relative block w-full rounded-md border border-[#b8c8df] px-3 py-2.5 text-slate-950 placeholder-slate-400 focus:border-[#0b63f6] sm:text-sm"
                placeholder="••••••••"
              />
            </div>
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-bold text-slate-700">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                className="ic-focus mt-1 relative block w-full rounded-md border border-[#b8c8df] px-3 py-2.5 text-slate-950 placeholder-slate-400 focus:border-[#0b63f6] sm:text-sm"
                placeholder="••••••••"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="ic-button-primary w-full disabled:opacity-50"
            >
              {loading ? 'Creating account...' : 'Sign up'}
            </button>
          </div>

          <div className="text-center">
            <p className="text-sm text-slate-600">
              Already have an account?{' '}
              <Link href="/login" className="font-bold text-[#0b63f6] hover:text-[#0649bf]">
                Sign in
              </Link>
            </p>
          </div>

          <p className="text-xs text-center text-slate-400">
            By creating an account you agree to our{' '}
            <Link href="/terms" className="underline hover:text-slate-600">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link href="/privacy" className="underline hover:text-slate-600">
              Privacy Policy
            </Link>
            .
          </p>
        </form>
        </div>

        <div className="mt-4 flex justify-center gap-4 text-xs text-slate-400">
          <Link href="/privacy" className="hover:text-slate-600 transition-colors">
            Privacy Policy
          </Link>
          <Link href="/terms" className="hover:text-slate-600 transition-colors">
            Terms
          </Link>
          <Link href="/impressum" className="hover:text-slate-600 transition-colors">
            Impressum
          </Link>
          <Link href="/datenschutz" className="hover:text-slate-600 transition-colors">
            Datenschutz
          </Link>
        </div>
      </div>
    </div>
  );
}
