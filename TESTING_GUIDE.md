# Testing Guide for Web Interface

This guide will help you test the complete multi-tenant web interface with the backend services.

## Prerequisites

- Docker and Docker Compose installed
- Git repository cloned
- Terminal/Command line access

## Step 1: Environment Setup

### Backend Configuration

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file and update the following critical values:
   ```bash
   # Database - should point to Docker service
   DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/pop3_forwarder
   
   # Redis - should point to Docker service
   REDIS_URL=redis://redis:6379/0
   CELERY_BROKER_URL=redis://redis:6379/0
   CELERY_RESULT_BACKEND=redis://redis:6379/0
   
   # Security - CHANGE THESE IN PRODUCTION!
   SECRET_KEY=your-generated-secret-key-min-32-characters
   ENCRYPTION_KEY=your-generated-encryption-key-min-32-characters
   
   # CORS for frontend
   CORS_ORIGINS=http://localhost:3000,http://localhost:8000
   
   # Google OAuth (optional for testing)
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback
   ```

### Frontend Configuration

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```

2. Create `.env.local` file:
   ```bash
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   ```

## Step 2: Start Services

From the project root directory:

```bash
# Start all services
docker-compose -f docker-compose.new.yml up -d

# Check that all services are running
docker-compose -f docker-compose.new.yml ps
```

Expected output should show all services as "Up":
- postgres
- redis
- backend
- celery-worker
- celery-beat
- frontend

## Step 3: Initialize Database

Run database migrations:

```bash
docker-compose -f docker-compose.new.yml exec backend alembic upgrade head
```

## Step 4: Access the Application

### Web Interface
Open your browser to: **http://localhost:3000**

You should see the landing page with:
- Hero section explaining the service
- Features list
- "Sign In" and "Sign Up" buttons

### API Documentation
Open your browser to: **http://localhost:8000/api/docs**

This shows the interactive Swagger/OpenAPI documentation.

## Step 5: Test User Registration

### Method 1: Via Web Interface

1. Go to http://localhost:3000
2. Click "Sign Up"
3. Fill in the form:
   - Full Name: "Test User"
   - Email: "test@example.com"
   - Password: "testpassword123"
   - Confirm Password: "testpassword123"
4. Click "Sign up"
5. You should be redirected to the dashboard

### Method 2: Via API

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "full_name": "Test User"
  }'
```

## Step 6: Test Login

### Via Web Interface

1. Go to http://localhost:3000/login
2. Enter credentials:
   - Email: "test@example.com"
   - Password: "testpassword123"
3. Click "Sign in"
4. You should be redirected to the dashboard

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpassword123"
```

Save the returned `access_token` for subsequent API requests.

## Step 7: Test Dashboard

After logging in, you should see the dashboard with:

- **Overview Cards** showing:
  - Total Accounts: 0
  - Emails Forwarded: 0
  - Active Accounts: 0
  - Errors: 0

- **Recent Processing Runs** table (empty initially)

- **Quick Actions** buttons:
  - Add Mail Account
  - View All Accounts

## Step 8: Test Adding Mail Account

### Via Web Interface

1. Click "Add Mail Account" button
2. Fill in the form:
   - Account Name: "Test Gmail"
   - Email: "test@gmail.com"
   - Click "Auto-Detect" to automatically fill settings
   - Or manually enter:
     - Protocol: POP3+SSL
     - Host: pop.gmail.com
     - Port: 995
     - Username: test@gmail.com
     - Password: (your Gmail app password)
     - Use SSL: checked
     - Check Interval: 5 minutes
3. Click "Test Connection" (optional)
4. Click "Save"

### Via API

```bash
TOKEN="your-access-token-from-login"

curl -X POST http://localhost:8000/api/v1/mail-accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Gmail",
    "protocol": "pop3_ssl",
    "host": "pop.gmail.com",
    "port": 995,
    "username": "test@gmail.com",
    "password": "your-app-password",
    "use_ssl": true,
    "check_interval_minutes": 5
  }'
```

## Step 9: Test Auto-Detection Feature

The auto-detection feature automatically configures mail server settings:

### Via Web Interface

1. Go to Add Mail Account
2. Enter email: "test@outlook.com"
3. Click "Auto-Detect"
4. Settings should be automatically filled:
   - Protocol: IMAP+SSL
   - Host: outlook.office365.com
   - Port: 993

Supported providers:
- Gmail (pop.gmail.com / imap.gmail.com)
- Outlook/Hotmail (outlook.office365.com)
- Yahoo (pop.mail.yahoo.com / imap.mail.yahoo.com)
- GMX (pop.gmx.com / imap.gmx.com)
- WEB.de (pop3.web.de / imap.web.de)
- T-Online (pop.t-online.de / imap.t-online.de)

## Step 10: Test Mail Account Management

### List Accounts

Navigate to "Mail Accounts" page to see all configured accounts with:
- Account name and email
- Status indicator (active/inactive)
- Last checked timestamp
- Error messages (if any)
- Enable/Disable toggle
- Edit and Delete buttons

### Edit Account

1. Click "Edit" button on an account
2. Modify settings (e.g., change check interval to 10 minutes)
3. Click "Save"
4. Account should be updated

### Delete Account

1. Click "Delete" button on an account
2. Confirm deletion
3. Account should be removed from the list

## Step 11: Test Settings Page

1. Navigate to "Settings" from the sidebar
2. View current user profile
3. View subscription information (tier, limits)

## Step 12: Test Google OAuth (Optional)

If you configured Google OAuth credentials:

1. Go to http://localhost:3000/login
2. Click "Sign in with Google"
3. You should be redirected to Google's authorization page
4. After authorizing, you should be redirected back and logged in

## Step 13: Test Multitenancy Isolation

Create a second user and verify data isolation:

1. Logout from first account
2. Register a new user: "test2@example.com"
3. Add mail accounts for this user
4. Verify that mail accounts from first user are not visible
5. Login back as first user
6. Verify that only first user's accounts are visible

## Verification Checklist

- [ ] Frontend loads successfully at http://localhost:3000
- [ ] Backend API docs accessible at http://localhost:8000/api/docs
- [ ] User registration works
- [ ] Email/password login works
- [ ] Dashboard displays correctly
- [ ] Can add mail account
- [ ] Auto-detect feature works
- [ ] Can edit mail account
- [ ] Can delete mail account
- [ ] Mail accounts list shows all accounts
- [ ] Settings page displays user info
- [ ] Logout works correctly
- [ ] Multitenancy isolation verified (each user sees only their data)
- [ ] Mobile responsive design works (test on mobile device or browser dev tools)

## Troubleshooting

### Backend not accessible

```bash
# Check backend logs
docker-compose -f docker-compose.new.yml logs backend

# Restart backend
docker-compose -f docker-compose.new.yml restart backend
```

### Frontend not loading

```bash
# Check frontend logs
docker-compose -f docker-compose.new.yml logs frontend

# Rebuild frontend
docker-compose -f docker-compose.new.yml build frontend
docker-compose -f docker-compose.new.yml restart frontend
```

### Database connection errors

```bash
# Check if postgres is running
docker-compose -f docker-compose.new.yml ps postgres

# Check postgres logs
docker-compose -f docker-compose.new.yml logs postgres

# Restart postgres
docker-compose -f docker-compose.new.yml restart postgres
```

### CORS errors in browser console

Verify `CORS_ORIGINS` in `backend/.env` includes `http://localhost:3000`

### Authentication fails

1. Clear browser local storage
2. Check backend logs for auth errors
3. Verify SECRET_KEY is set in backend/.env

## Performance Testing

### Load Testing

Use Apache Bench (ab) or similar tool:

```bash
# Test registration endpoint
ab -n 100 -c 10 -p registration.json -T application/json \
  http://localhost:8000/api/v1/auth/register
```

### Email Processing Testing

1. Add multiple mail accounts (5-10)
2. Monitor Celery worker logs:
   ```bash
   docker-compose -f docker-compose.new.yml logs -f celery-worker
   ```
3. Verify emails are being processed
4. Check processing runs in the dashboard

## Cleanup

To stop all services and remove containers:

```bash
docker-compose -f docker-compose.new.yml down
```

To also remove volumes (database data):

```bash
docker-compose -f docker-compose.new.yml down -v
```

## Next Steps

After successful testing:

1. Set up proper Google OAuth credentials for production
2. Configure Stripe for payment processing
3. Set up email notifications with Apprise
4. Deploy to production server
5. Set up SSL/TLS certificates
6. Configure proper backup strategy
7. Set up monitoring and alerting

## Support

For issues or questions:
- Check logs: `docker-compose -f docker-compose.new.yml logs [service-name]`
- Review API documentation: http://localhost:8000/api/docs
- Open an issue on GitHub
