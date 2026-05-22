'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import { versionApi } from '@/lib/api';
import { BrandMark } from '@/components/BrandMark';
import { 
  LayoutDashboard, 
  Mail, 
  Settings, 
  LogOut, 
  Menu, 
  X,
  User,
  Shield,
  Users,
  CreditCard,
  Bell,
  Inbox,
  Activity
} from 'lucide-react';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const { data: versionInfo } = useQuery({
    queryKey: ['version'],
    queryFn: () => versionApi.get(),
    staleTime: Infinity,
  });

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Mail Accounts', href: '/accounts', icon: Mail },
    { name: 'Notifications', href: '/notifications', icon: Bell },
    { name: 'Mailbox Activity', href: '/logs', icon: Inbox },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  const adminNavigation = user?.is_superuser
    ? [
        { name: 'Admin Overview', href: '/admin', icon: Shield },
        { name: 'Manage Users', href: '/admin/users', icon: Users },
        { name: 'Manage Plans', href: '/admin/plans', icon: CreditCard },
        { name: 'Activity Logs', href: '/admin/logs', icon: Activity },
      ]
    : [];

  const allNavItems = [...navigation, ...adminNavigation];

  return (
    <div className="min-h-screen bg-[#f7faff] text-slate-900">
      {/* Sidebar for desktop */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-grow border-r border-[#d9e3f2] bg-white/95 shadow-[14px_0_42px_rgba(16,33,63,0.04)]">
          <div className="flex h-18 flex-shrink-0 items-center px-5 border-b border-[#d9e3f2]">
            <BrandMark />
          </div>
          <nav className="flex-1 px-3 py-5 space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center px-3.5 py-2.5 text-sm font-semibold rounded-lg transition-colors ${
                    isActive
                      ? 'bg-[#e7f0ff] text-[#0649bf]'
                      : 'text-slate-600 hover:bg-[#f7faff] hover:text-slate-950'
                  }`}
                >
                  <item.icon className={`mr-3 h-5 w-5 ${isActive ? 'text-[#0b63f6]' : 'text-slate-400'}`} />
                  {item.name}
                </Link>
              );
            })}
            {adminNavigation.length > 0 && (
              <>
                <div className="pt-5 pb-1 px-3.5">
                  <p className="text-xs font-bold uppercase text-slate-400">Admin</p>
                </div>
                {adminNavigation.map((item) => {
                  const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`flex items-center px-3.5 py-2.5 text-sm font-semibold rounded-lg transition-colors ${
                        isActive
                          ? 'bg-[#e8f7ef] text-[#11834d]'
                          : 'text-slate-600 hover:bg-[#f7faff] hover:text-slate-950'
                      }`}
                    >
                      <item.icon className={`mr-3 h-5 w-5 ${isActive ? 'text-[#11834d]' : 'text-slate-400'}`} />
                      {item.name}
                    </Link>
                  );
                })}
              </>
            )}
          </nav>
          <div className="flex-shrink-0 border-t border-[#d9e3f2] p-4">
            <button
              onClick={handleLogout}
              className="flex items-center w-full px-3.5 py-2.5 text-sm font-semibold text-slate-600 rounded-lg hover:bg-[#f7faff] hover:text-slate-950 transition-colors"
            >
              <LogOut className="mr-3 h-5 w-5 text-slate-400" />
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Mobile sidebar */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="fixed inset-0 bg-slate-900/50" onClick={() => setSidebarOpen(false)} />
          <div className="fixed inset-y-0 left-0 flex w-72 flex-col bg-white">
            <div className="flex items-center justify-between h-18 px-5 border-b border-[#d9e3f2]">
              <BrandMark />
              <button onClick={() => setSidebarOpen(false)} className="text-slate-500 hover:text-slate-700">
                <X className="h-6 w-6" />
              </button>
            </div>
            <nav className="flex-1 px-3 py-5 space-y-1">
              {navigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`flex items-center px-3.5 py-2.5 text-sm font-semibold rounded-lg transition-colors ${
                      isActive
                        ? 'bg-[#e7f0ff] text-[#0649bf]'
                        : 'text-slate-600 hover:bg-[#f7faff] hover:text-slate-950'
                    }`}
                  >
                    <item.icon className={`mr-3 h-5 w-5 ${isActive ? 'text-[#0b63f6]' : 'text-slate-400'}`} />
                    {item.name}
                  </Link>
                );
              })}
              {adminNavigation.length > 0 && (
                <>
                  <div className="pt-5 pb-1 px-3.5">
                    <p className="text-xs font-bold uppercase text-slate-400">Admin</p>
                  </div>
                  {adminNavigation.map((item) => {
                    const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                    return (
                      <Link
                        key={item.name}
                        href={item.href}
                        onClick={() => setSidebarOpen(false)}
                        className={`flex items-center px-3.5 py-2.5 text-sm font-semibold rounded-lg transition-colors ${
                          isActive
                            ? 'bg-[#e8f7ef] text-[#11834d]'
                            : 'text-slate-600 hover:bg-[#f7faff] hover:text-slate-950'
                        }`}
                      >
                        <item.icon className={`mr-3 h-5 w-5 ${isActive ? 'text-[#11834d]' : 'text-slate-400'}`} />
                        {item.name}
                      </Link>
                    );
                  })}
                </>
              )}
            </nav>
            <div className="flex-shrink-0 border-t border-[#d9e3f2] p-4">
              <button
                onClick={handleLogout}
                className="flex items-center w-full px-3.5 py-2.5 text-sm font-semibold text-slate-600 rounded-lg hover:bg-[#f7faff] hover:text-slate-950 transition-colors"
              >
                <LogOut className="mr-3 h-5 w-5 text-slate-400" />
                Logout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="lg:pl-64 flex flex-col flex-1">
        {/* Top bar */}
        <div className="sticky top-0 z-10 flex h-16 flex-shrink-0 border-b border-[#d9e3f2] bg-white/90 backdrop-blur-xl">
          <button
            type="button"
            className="border-r border-[#d9e3f2] px-4 text-slate-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex flex-1 justify-between px-4 sm:px-6 lg:px-8">
            <div className="flex flex-1 items-center">
              <h2 className="text-lg font-bold text-slate-950">
                {allNavItems.find((item) => item.href === pathname)?.name || 'Dashboard'}
              </h2>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className={`flex h-8 w-8 items-center justify-center rounded-md text-white ${user?.is_superuser ? 'bg-[#11834d]' : 'bg-[#0b63f6]'}`}>
                  {user?.is_superuser ? <Shield className="h-4 w-4" /> : <User className="h-4 w-4" />}
                </div>
                <div className="hidden sm:block">
                  <p className="text-sm font-semibold text-slate-950">{user?.full_name}</p>
                  <p className="text-xs text-slate-500">
                    {user?.email}
                    {user?.is_superuser && (
                      <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                        Admin
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1">
          <div className="py-7">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              {children}
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-[#d9e3f2] bg-white/80 py-4 px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
            <div className="flex flex-wrap gap-4">
              <Link href="/impressum" className="hover:text-slate-600 transition-colors">
                Impressum
              </Link>
              <Link href="/datenschutz" className="hover:text-slate-600 transition-colors">
                Datenschutz
              </Link>
            </div>
            {versionInfo && (
              <div className="flex flex-wrap gap-3">
                <span>v{versionInfo.version}</span>
                {versionInfo.build_date && (
                  <span>
                    Built{' '}
                    {new Date(versionInfo.build_date).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                )}
              </div>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
}
