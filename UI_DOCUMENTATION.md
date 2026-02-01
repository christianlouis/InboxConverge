# Web Interface Screenshots and Features

This document describes the web interface screens and their features.

## 🏠 Landing Page (/)

**URL**: `http://localhost:3000`

### Features:
- Clean, modern hero section with service description
- "Sign In" and "Sign Up" call-to-action buttons
- Three key feature cards:
  - 🔍 **Auto-Detection**: Automatically detect mail server settings
  - ⏰ **Scheduled Checks**: Periodic email checking and forwarding
  - 🔒 **Secure & Private**: Encrypted credentials and user isolation
- "How It Works" section with 3-step process:
  1. Connect your email accounts
  2. Configure forwarding settings
  3. Relax while emails are forwarded automatically

### Design:
- Responsive layout
- Blue gradient header
- Professional typography
- Mobile-friendly navigation

---

## 🔐 Login Page (/login)

**URL**: `http://localhost:3000/login`

### Features:
- Email/password login form
- "Sign in with Google" OAuth button with Google icon
- Link to registration page
- Error message display
- Loading states during authentication

### Form Fields:
- Email address (required)
- Password (required)

### Actions:
- **Sign in** button - Submit credentials
- **Sign in with Google** - OAuth2 flow
- **Sign up** link - Navigate to registration

---

## 📝 Registration Page (/register)

**URL**: `http://localhost:3000/register`

### Features:
- User registration form
- Password confirmation
- Auto-login after successful registration
- Error message display for validation failures
- Link back to login page

### Form Fields:
- Full Name (required)
- Email address (required)
- Password (required, min 8 characters)
- Confirm Password (required, must match)

### Validation:
- Email format validation
- Password minimum length (8 characters)
- Password match verification
- Duplicate email detection

---

## 📊 Dashboard (/dashboard)

**URL**: `http://localhost:3000/dashboard` (Protected route)

### Layout:
- Sidebar navigation (collapsible on mobile)
- Top bar with user info and logout
- Main content area with cards and tables

### Overview Cards (4 cards in a grid):
1. **Total Accounts**
   - Count of all configured mail accounts
   - Icon: Mail icon

2. **Emails Forwarded Today**
   - Total emails processed in last 24 hours
   - Icon: Send icon

3. **Active Accounts**
   - Number of enabled accounts
   - Icon: CheckCircle icon

4. **Errors**
   - Count of errors in recent processing
   - Icon: AlertCircle icon
   - Red color for warnings

### Recent Processing Runs Table:
- **Columns**:
  - Account name
  - Status (badge: success/failed/running)
  - Emails fetched
  - Emails forwarded
  - Started at (timestamp)
  - Duration
- **Features**:
  - Sortable columns
  - Color-coded status badges
  - Empty state when no runs yet
  - Auto-refresh with React Query

### Quick Actions:
- "Add Mail Account" button (prominent, primary color)
- "View All Accounts" link

---

## 📧 Mail Accounts Page (/accounts)

**URL**: `http://localhost:3000/accounts` (Protected route)

### Features:
- List of all user's mail accounts
- Card-based layout for each account
- Add new account button
- Search/filter capabilities (planned)

### Account Card Display:
Each account shows:
- **Account Name** (e.g., "Work Gmail")
- **Email Address** (e.g., "work@gmail.com")
- **Protocol** badge (e.g., "POP3+SSL")
- **Status Indicator**:
  - Green dot: Active and working
  - Red dot: Has errors
  - Gray dot: Disabled
- **Last Checked**: Timestamp of last processing
- **Check Interval**: How often emails are checked (e.g., "Every 5 minutes")
- **Error Message**: Displayed if last check failed (red text)
- **Statistics**:
  - Total emails forwarded
  - Last successful run
- **Action Buttons**:
  - Toggle (Enable/Disable)
  - Edit button
  - Delete button (with confirmation)

### Add/Edit Mail Account Modal:

#### Form Fields:
1. **Account Name**
   - Friendly name for the account
   - Example: "My Old Gmail"

2. **Email Address**
   - The email to fetch from
   - Used for auto-detection

3. **Auto-Detect Button**
   - Automatically fills in protocol, host, port for common providers
   - Supports: Gmail, Outlook, Yahoo, GMX, WEB.de, T-Online

4. **Protocol** (dropdown)
   - POP3 (port 110)
   - POP3+SSL (port 995)
   - IMAP (port 143)
   - IMAP+SSL (port 993)

5. **Mail Server Host**
   - Example: pop.gmail.com

6. **Port**
   - Number input
   - Auto-filled by protocol selection

7. **Username**
   - Usually the email address
   - For POP3/IMAP authentication

8. **Password**
   - Masked input
   - Stored encrypted in database
   - Gmail users: Use App Password

9. **Use SSL/TLS**
   - Toggle switch
   - Enabled by default for SSL protocols

10. **Check Interval**
    - Dropdown: 1, 5, 10, 15, 30, 60 minutes
    - How often to check for new emails

11. **Max Emails Per Check**
    - Optional number input
    - Limit emails processed in single run
    - Defaults to system setting

#### Action Buttons:
- **Test Connection** - Verifies credentials without saving
  - Shows success/error message
  - Displays connection details
- **Save** - Creates or updates the account
- **Cancel** - Closes modal without saving

---

## ⚙️ Settings Page (/settings)

**URL**: `http://localhost:3000/settings` (Protected route)

### Sections:

#### 1. User Profile
- Display name
- Email address
- Account created date
- Edit profile button (future enhancement)

#### 2. Subscription Information
- **Current Tier**: Free/Basic/Pro/Enterprise
- **Tier Badge**: Color-coded by level
- **Account Limits**:
  - Max mail accounts allowed
  - Current accounts used
  - Progress bar showing usage
- **Upgrade Button**: Navigate to subscription plans (planned)

#### 3. Notification Settings (Planned)
- Email notifications for errors
- Frequency preferences
- Notification channels (Apprise integration)

#### 4. Security (Planned)
- Change password
- Two-factor authentication
- Active sessions
- API tokens

---

## 🎨 UI Components

### Sidebar Navigation:
- **Dashboard** - Home icon
- **Mail Accounts** - Mail icon
- **Settings** - Settings icon
- **Logout** - LogOut icon

### Top Bar:
- User name display
- Subscription tier badge
- Hamburger menu (mobile)

### Status Badges:
- **Success**: Green background, white text
- **Error**: Red background, white text
- **Running**: Blue background, white text
- **Disabled**: Gray background, white text

### Loading States:
- Spinner animation for page loads
- Skeleton loaders for tables
- Button loading states

### Empty States:
- "No mail accounts yet" - Dashboard
- "No processing runs" - History table
- Helpful call-to-action buttons

### Error Display:
- Red banner at top of forms
- Inline field validation errors
- Toast notifications (planned)

### Responsive Design:
- **Desktop** (≥1024px): Full sidebar, 4-column card grid
- **Tablet** (768-1023px): Collapsible sidebar, 2-column grid
- **Mobile** (<768px): Hamburger menu, single column, stacked cards

---

## 🔐 Authentication Flow

### Login Flow:
1. User enters credentials
2. API validates and returns JWT token
3. Token stored in localStorage
4. User redirected to dashboard
5. AuthGuard checks token on protected routes

### Google OAuth Flow:
1. User clicks "Sign in with Google"
2. Redirected to Google authorization page
3. User grants permission
4. Redirected back to `/auth/callback?code=...`
5. Frontend exchanges code for token via API
6. Token stored, user redirected to dashboard

### Session Management:
- JWT tokens expire after 30 minutes
- Refresh tokens valid for 7 days
- Automatic logout on 401 responses
- Token refresh before expiry (planned)

---

## 🎯 User Experience Highlights

### Intuitive Design:
- Clear navigation structure
- Consistent color scheme (blue primary)
- Familiar UI patterns
- Helpful empty states

### Accessibility:
- Semantic HTML elements
- Proper form labels
- Keyboard navigation support
- Screen reader friendly (planned enhancement)

### Performance:
- React Query caching
- Optimistic updates
- Lazy loading
- Code splitting

### Feedback:
- Loading indicators
- Error messages
- Success confirmations
- Real-time status updates

---

## 📱 Mobile Experience

All pages are fully responsive:
- Touch-friendly buttons (minimum 44x44px)
- Swipe gestures for navigation (planned)
- Optimized layouts for small screens
- Fast load times with optimized assets
- Progressive Web App capabilities (planned)

---

## 🚀 Planned Enhancements

### Phase 1 (Next Release):
- [ ] Toast notification system
- [ ] Email filtering rules interface
- [ ] Processing logs detailed view
- [ ] Export data functionality

### Phase 2 (Future):
- [ ] Advanced analytics dashboard
- [ ] Email preview before forwarding
- [ ] Batch operations on accounts
- [ ] Dark mode theme
- [ ] Keyboard shortcuts
- [ ] Real-time WebSocket updates

### Phase 3 (Long-term):
- [ ] Mobile native app
- [ ] Browser extension
- [ ] Email templates
- [ ] AI-powered filtering
- [ ] Team collaboration features

---

## 📸 Screenshot Placeholders

_Actual screenshots to be added after deployment_

### Key Screens to Capture:
1. Landing page hero section
2. Login page with Google button
3. Dashboard with populated data
4. Mail accounts list with multiple accounts
5. Add mail account modal
6. Settings page
7. Mobile view of dashboard
8. Error state examples
9. Loading state examples
10. Empty state examples

---

## 🎨 Design System

### Colors:
- **Primary**: Blue (#2563eb)
- **Success**: Green (#10b981)
- **Warning**: Yellow (#f59e0b)
- **Error**: Red (#ef4444)
- **Background**: Gray (#f9fafb)
- **Text**: Dark Gray (#111827)

### Typography:
- **Font Family**: System fonts (sans-serif)
- **Headings**: Bold, larger sizes
- **Body**: Regular weight, 14-16px
- **Labels**: Medium weight, 12-14px

### Spacing:
- Consistent 8px grid system
- Padding: 1rem (16px) standard
- Margins: 1.5rem (24px) between sections
- Card spacing: 1rem gap

### Components:
- **Buttons**: Rounded corners (6px), hover states
- **Cards**: White background, subtle shadow
- **Inputs**: Border focus states, validation colors
- **Badges**: Rounded pills, color-coded
- **Icons**: Lucide React, consistent size (20-24px)

---

This comprehensive UI documentation provides a complete picture of the web interface implementation.
