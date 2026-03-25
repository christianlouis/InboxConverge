# ADR 008: Use Next.js for Frontend

**Status:** Accepted  
**Date:** 2026-02-10  
**Deciders:** Development Team

## Context

The SaaS platform requires a web frontend that provides:

1. User authentication (email/password + Google OAuth)
2. Mail account management dashboard (CRUD operations)
3. Processing run history and statistics
4. Settings and subscription management
5. Responsive design for mobile and desktop

Technical requirements:
- Type-safe API integration with the FastAPI backend
- Server-side rendering (SSR) for SEO and initial load performance
- Static export capability for CDN hosting
- Easy Docker containerization
- Modern development tooling (TypeScript, ESLint, hot-reload)

## Decision

We will use **Next.js 14+** (App Router) with **TypeScript** and **Tailwind CSS** for the frontend.

## Alternatives Considered

### 1. React (Create React App / Vite SPA)
- **Pros**: Simpler build setup, no SSR complexity, large ecosystem
- **Cons**: Client-side rendering only (SEO limitations), no built-in routing, additional setup for SSR

### 2. Vue.js / Nuxt.js
- **Pros**: Excellent developer experience, reactive by default, SSR via Nuxt
- **Cons**: Smaller ecosystem than React, team less familiar, different component model

### 3. Svelte / SvelteKit
- **Pros**: Very small bundle size, simple reactive model, SSR via SvelteKit
- **Cons**: Smaller community, fewer UI component libraries, less mature ecosystem

### 4. Angular
- **Pros**: Full framework (routing, forms, HTTP), TypeScript-first
- **Cons**: Heavy boilerplate, steep learning curve, over-engineered for a dashboard application

### 5. Server-Side Templates (Jinja2 / FastAPI with Jinja)
- **Pros**: Simplest deployment (single backend), no separate frontend build
- **Cons**: No reactive UI, poor UX for dynamic dashboards, hard to test independently

## Rationale

Next.js was chosen because:

1. **App Router**: File-system based routing with layout nesting simplifies page organization
2. **TypeScript First**: Strong typing catches API integration errors at compile time
3. **API Route Proxy**: Next.js Route Handlers allow proxying backend requests at runtime — eliminating CORS issues and enabling `BACKEND_URL` to be set at container runtime (not build time)
4. **SSR + Static**: Supports both server-rendered pages (authenticated dashboard) and static pages (marketing landing page)
5. **Tailwind CSS**: Utility-first CSS eliminates the need for a separate CSS framework and enables rapid UI development
6. **Large Ecosystem**: Extensive component libraries, excellent documentation, widely used
7. **Docker Friendly**: `next start` serves the production build, easily containerized

## Implementation Architecture

### Frontend Proxy Pattern

The frontend proxies all API calls through a Next.js Route Handler to avoid CORS and build-time URL issues:

```
Browser → Next.js Server (/api/v1/*) → FastAPI Backend (BACKEND_URL/api/v1/*)
```

```typescript
// src/app/api/v1/[...path]/route.ts
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join("/");
  const url = `${BACKEND_URL}/api/v1/${path}${req.nextUrl.search}`;
  return fetch(url, { headers: req.headers });
}
```

This means `BACKEND_URL` is a **runtime** environment variable (set in Docker Compose / Kubernetes), not a build-time variable. The Axios client uses a relative base URL:

```typescript
// src/lib/api.ts
const api = axios.create({ baseURL: "/api/v1" });
```

### Project Structure

```
frontend/src/
├── app/                    # Next.js App Router pages
│   ├── page.tsx            # Landing page
│   ├── login/              # Authentication pages
│   ├── dashboard/          # Main dashboard
│   ├── accounts/           # Mail account management
│   ├── settings/           # User settings
│   └── api/v1/[...path]/   # Backend proxy Route Handler
├── components/             # Reusable UI components
│   ├── AddMailAccountModal.tsx
│   ├── DashboardLayout.tsx
│   └── AuthGuard.tsx
├── lib/
│   └── api.ts              # Typed Axios API client
├── store/
│   └── authStore.ts        # Zustand authentication state
└── instrumentation.ts      # Server startup hook (logs BACKEND_URL)
```

### Authentication State

Authentication state is managed via **Zustand** store, with JWT tokens persisted in `localStorage`. The `AuthGuard` component protects all dashboard routes.

## Consequences

### Positive
- TypeScript catches API contract mismatches at compile time
- Proxy pattern eliminates CORS configuration and build-time URL embedding
- App Router layouts reduce boilerplate for authenticated vs public pages
- Tailwind CSS enables rapid UI iteration without writing custom CSS
- Server instrumentation hook logs `BACKEND_URL` at startup for easy debugging

### Negative
- Next.js adds complexity vs a plain React SPA (SSR concepts, server/client component boundary)
- Node.js 20+ required at runtime (not just build time)
- Separate Docker container needed (backend and frontend are distinct services)
- `localStorage` token storage is vulnerable to XSS (future: migrate to `httpOnly` cookies)

### Neutral
- ESLint with `eslint-config-next` enforces Next.js-specific rules
- `npm ci` used in CI to ensure deterministic installs from `package-lock.json`

## Related Decisions

- See ADR-007 for JWT tokens consumed by the frontend
- See ADR-003 for the FastAPI backend the frontend proxies to

## References

- [Next.js Documentation](https://nextjs.org/docs)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Tailwind CSS](https://tailwindcss.com/)
- [Zustand State Management](https://github.com/pmndrs/zustand)
