# Web Interface Quick Start Guide

The InboxConverge now includes a modern web interface built with Next.js, making it easy to manage your email forwarding without API calls.

## 🌐 Accessing the Web Interface

After starting the services with `docker-compose -f docker-compose.new.yml up -d`, the web interface is available at:

**http://localhost:3000**

## 📱 Features

### Landing Page
- Overview of the service
- Sign In / Sign Up buttons
- Feature highlights

### Authentication
- **Email/Password Registration** - Create a new account
- **Email/Password Login** - Sign in to existing account
- **Google OAuth** - One-click sign-in with Google

### Dashboard
- **Overview Cards** showing:
  - Total mail accounts
  - Emails forwarded today
  - Active accounts
  - Recent errors
- **Recent Activity** - Table of recent processing runs
- **Quick Actions** - Add new account, view all accounts

### Mail Accounts Management
- **List View** - All your configured mail accounts
  - Status indicators (active/inactive, errors)
  - Last checked timestamp
  - Quick enable/disable toggle
- **Add Account** 
  - Auto-detect button for popular providers (Gmail, Outlook, Yahoo, etc.)
  - Test connection before saving
  - Configure check intervals and limits
- **Edit Account** - Update existing account settings
- **Delete Account** - Remove accounts you no longer need

### Settings
- **Profile Management** - Update your name and email
- **Subscription Info** - View your current plan and limits
- **Notification Settings** - Configure error notifications

## 🚀 Getting Started with the Web Interface

1. **Start the services** (if not already running):
   ```bash
   docker-compose -f docker-compose.new.yml up -d
   ```

2. **Open your browser** to http://localhost:3000

3. **Create an account**:
   - Click "Sign Up" 
   - Enter your details
   - Or use "Sign in with Google"

4. **Add your first mail account**:
   - Click "Add Mail Account" button
   - Enter your email address
   - Click "Auto-Detect" to automatically fill in server settings
   - Enter your email password (or app password)
   - Click "Test Connection" to verify
   - Click "Save"

5. **Monitor your forwarding**:
   - Dashboard shows real-time statistics
   - Check the recent activity table for processing history
   - View detailed logs for each account

## 🎨 Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Icons**: Lucide React
- **API Client**: Axios

## 🔧 Development

To run the frontend in development mode locally:

```bash
cd frontend
npm install
npm run dev
```

The development server will start at http://localhost:3000 with hot reload enabled.

## 🐳 Docker Configuration

The frontend is configured in `docker-compose.new.yml`:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: inboxconverge-frontend
  ports:
    - "3000:3000"
  environment:
    - NEXT_PUBLIC_API_URL=http://backend:8000
  depends_on:
    - backend
  restart: unless-stopped
```

## 🌍 Environment Variables

Create a `.env.local` file in the `frontend` directory:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

For production, update this to your actual backend URL.

## 📸 Screenshots

_(Screenshots will be added after deployment)_

### Dashboard
- Overview with statistics cards
- Recent processing runs

### Mail Accounts
- List of all configured accounts
- Add/Edit account modals

### Authentication
- Login page
- Registration page
- OAuth flow

## 🔐 Security

- All API requests require authentication via JWT tokens
- Passwords are never stored in the frontend
- OAuth tokens are managed securely
- CSRF protection enabled
- Secure HTTP-only cookies for sensitive data

## 📱 Responsive Design

The interface is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile phones

## 🆘 Troubleshooting

### Cannot connect to backend
- Ensure backend is running: `docker-compose -f docker-compose.new.yml ps`
- Check backend logs: `docker-compose -f docker-compose.new.yml logs backend`
- Verify API URL in `.env.local`

### Authentication not working
- Clear browser local storage
- Check backend logs for auth errors
- Verify Google OAuth credentials (if using OAuth)

### Frontend not loading
- Check frontend logs: `docker-compose -f docker-compose.new.yml logs frontend`
- Rebuild frontend: `docker-compose -f docker-compose.new.yml build frontend`
- Clear browser cache

## 🔄 Updates

To update the frontend:

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.new.yml build frontend
docker-compose -f docker-compose.new.yml restart frontend
```

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check the documentation in the `docs` folder
- Review API documentation at http://localhost:8000/api/docs
