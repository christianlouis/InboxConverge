# Deployment Checklist and Next Steps

This document provides a checklist for deploying the multi-tenant InboxConverge with web interface.

## 🚀 Pre-Deployment Checklist

### 1. Environment Setup

#### Backend Environment Variables (`backend/.env`)
- [ ] Generate secure `SECRET_KEY` (min 32 characters)
  ```bash
  openssl rand -hex 32
  ```
- [ ] Generate secure `ENCRYPTION_KEY` (min 32 characters)
  ```bash
  openssl rand -hex 32
  ```
- [ ] Set `DATABASE_URL` to production PostgreSQL instance
- [ ] Configure `REDIS_URL` for production Redis
- [ ] Set `CORS_ORIGINS` to include production frontend URL
- [ ] Set `DEBUG=false` for production
- [ ] Configure `LOG_LEVEL=INFO` or `WARNING`

#### Google OAuth (Optional but Recommended)
- [ ] Create Google Cloud Project
- [ ] Enable Google+ API
- [ ] Create OAuth 2.0 credentials
- [ ] Set authorized redirect URIs:
  - Development: `http://localhost:3000/auth/callback`
  - Production: `https://yourdomain.com/auth/callback`
- [ ] Add `GOOGLE_CLIENT_ID` to backend/.env
- [ ] Add `GOOGLE_CLIENT_SECRET` to backend/.env
- [ ] Add `GOOGLE_REDIRECT_URI` to backend/.env

#### Frontend Environment Variables (`frontend/.env.local`)
- [ ] Set `NEXT_PUBLIC_API_URL` to backend URL
  - Development: `http://localhost:8000`
  - Production: `https://api.yourdomain.com`

### 2. Infrastructure Setup

#### Docker Host
- [ ] Server with Docker installed (20.10+)
- [ ] Docker Compose installed (v2.0+)
- [ ] Minimum 2 vCPU, 4GB RAM
- [ ] 40GB+ available disk space
- [ ] Ports 80, 443, 8000, 3000 available

#### Database
- [ ] PostgreSQL 15+ instance running
- [ ] Database created: `inbox_converge`
- [ ] Connection details configured in backend/.env
- [ ] Backups configured

#### Redis
- [ ] Redis 7+ instance running
- [ ] Connection details configured in backend/.env
- [ ] Persistence enabled (AOF or RDB)

### 3. SSL/TLS Configuration

#### Option A: Let's Encrypt with Certbot
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com
```

#### Option B: Reverse Proxy (Recommended)
- [ ] nginx or Traefik configured
- [ ] SSL certificates obtained
- [ ] Frontend proxied from port 3000
- [ ] Backend API proxied from port 8000
- [ ] CORS headers properly configured

### 4. Security Hardening

- [ ] Firewall configured (UFW or iptables)
- [ ] Only necessary ports open (80, 443, 22)
- [ ] SSH key-based authentication
- [ ] Fail2ban installed for brute force protection
- [ ] Docker containers running as non-root users
- [ ] Secrets not committed to version control
- [ ] Regular security updates enabled

## 📦 Deployment Steps

### Step 1: Clone Repository

```bash
# On production server
cd /opt
sudo git clone https://github.com/christianlouis/inboxconverge.git
cd inboxconverge
```

### Step 2: Configure Environment

```bash
# Backend
cd backend
cp .env.example .env
nano .env  # Edit with production values

# Frontend
cd ../frontend
echo "NEXT_PUBLIC_API_URL=https://api.yourdomain.com" > .env.local
```

### Step 3: Build and Start Services

```bash
cd ..
docker-compose -f docker-compose.new.yml build
docker-compose -f docker-compose.new.yml up -d
```

### Step 4: Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.new.yml exec backend alembic upgrade head

# Verify
docker-compose -f docker-compose.new.yml exec backend alembic current
```

### Step 5: Verify Services

```bash
# Check all services are running
docker-compose -f docker-compose.new.yml ps

# Check logs
docker-compose -f docker-compose.new.yml logs -f
```

### Step 6: Test Application

```bash
# Test backend API
curl https://api.yourdomain.com/health

# Test frontend
curl https://yourdomain.com

# Register test user
curl -X POST https://api.yourdomain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","full_name":"Test User"}'
```

### Step 7: Configure Monitoring

#### Health Checks
```bash
# Add to crontab for monitoring
*/5 * * * * curl -f https://yourdomain.com/health || mail -s "Site Down" admin@yourdomain.com
```

#### Log Rotation
```bash
# Configure Docker log rotation in /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## 🔄 Maintenance

### Regular Tasks

#### Daily
- [ ] Monitor error logs
- [ ] Check Celery worker status
- [ ] Verify email processing is working

#### Weekly
- [ ] Review database size and performance
- [ ] Check for security updates
- [ ] Rotate logs if necessary

#### Monthly
- [ ] Database backup verification
- [ ] Review user feedback and errors
- [ ] Update dependencies if needed

### Backup Strategy

#### Database Backups
```bash
# Automated daily backup script
cat > /usr/local/bin/backup-pop3-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/var/backups/inbox_converge
DATE=$(date +%Y%m%d_%H%M%S)
docker exec inboxconverge-postgres pg_dump -U postgres inbox_converge | gzip > $BACKUP_DIR/backup_$DATE.sql.gz
find $BACKUP_DIR -type f -mtime +30 -delete
EOF

chmod +x /usr/local/bin/backup-pop3-db.sh

# Add to crontab
0 2 * * * /usr/local/bin/backup-pop3-db.sh
```

## 🐛 Troubleshooting

### Common Issues

#### Frontend Cannot Connect to Backend
**Symptoms**: CORS errors, network errors
**Solutions**:
1. Verify `CORS_ORIGINS` includes frontend URL
2. Check backend is accessible from frontend container
3. Verify API URL in frontend .env.local

#### Database Connection Errors
**Symptoms**: "Connection refused" or timeout errors
**Solutions**:
1. Check PostgreSQL is running
2. Verify DATABASE_URL is correct
3. Check network connectivity
4. Review PostgreSQL logs

#### Celery Workers Not Processing
**Symptoms**: Emails not being forwarded
**Solutions**:
1. Check Redis is running
2. Review celery-worker logs
3. Verify CELERY_BROKER_URL is correct
4. Restart celery-worker container

#### OAuth Not Working
**Symptoms**: "Invalid redirect URI" or OAuth errors
**Solutions**:
1. Verify GOOGLE_REDIRECT_URI matches exactly
2. Check OAuth credentials in Google Console
3. Ensure HTTPS is used in production

### Log Locations

```bash
# Backend logs
docker-compose -f docker-compose.new.yml logs backend

# Frontend logs
docker-compose -f docker-compose.new.yml logs frontend

# Celery worker logs
docker-compose -f docker-compose.new.yml logs celery-worker

# Database logs
docker-compose -f docker-compose.new.yml logs postgres
```

## 📊 Monitoring & Observability

### Recommended Tools

#### Application Monitoring
- **Uptime Monitoring**: UptimeRobot, Pingdom
- **Error Tracking**: Sentry (can be added to backend)
- **Performance**: New Relic, DataDog

#### Infrastructure Monitoring
- **Container Health**: Docker healthchecks
- **Resource Usage**: cAdvisor + Prometheus + Grafana
- **Log Aggregation**: ELK Stack or Loki

### Metrics to Monitor

- [ ] API response times
- [ ] Error rates
- [ ] Email processing throughput
- [ ] Database connection pool usage
- [ ] Redis memory usage
- [ ] Disk space utilization
- [ ] Container CPU/Memory usage

## 🔐 Security Considerations

### Ongoing Security Tasks

- [ ] Regular dependency updates
  ```bash
  # Backend
  cd backend
  pip list --outdated
  
  # Frontend
  cd frontend
  npm outdated
  ```

- [ ] Monitor for security advisories
  - GitHub Dependabot alerts
  - CVE databases
  - Security mailing lists

- [ ] Regular security audits
  - Code review
  - Penetration testing
  - Vulnerability scanning

- [ ] Access control review
  - User permissions
  - API access logs
  - Failed login attempts

## 🚀 Next Steps and Enhancements

### Immediate (Week 1)
1. [ ] Set up monitoring and alerting
2. [ ] Configure automated backups
3. [ ] Create user documentation
4. [ ] Test all critical user flows

### Short-term (Month 1)
1. [ ] Implement Stripe payment integration
2. [ ] Add Apprise notification system
3. [ ] Create admin dashboard
4. [ ] Set up CI/CD pipeline

### Medium-term (Quarter 1)
1. [ ] Add email filtering rules
2. [ ] Implement advanced analytics
3. [ ] Create mobile app or PWA
4. [ ] Add team collaboration features

### Long-term (Year 1)
1. [ ] Kubernetes deployment
2. [ ] Multi-region support
3. [ ] Advanced ML-based filtering
4. [ ] Enterprise SSO/SAML

## 📞 Support Resources

### Documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Setup guide
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing procedures
- [UI_DOCUMENTATION.md](UI_DOCUMENTATION.md) - UI details
- [WEB_INTERFACE_GUIDE.md](WEB_INTERFACE_GUIDE.md) - User guide

### Getting Help
- GitHub Issues: Report bugs and request features
- GitHub Discussions: Ask questions and share ideas
- API Documentation: http://your-domain.com/api/docs

## ✅ Post-Deployment Verification

Use this checklist after deployment:

### Functional Tests
- [ ] User can register via web interface
- [ ] User can login with email/password
- [ ] User can login with Google OAuth
- [ ] Dashboard loads with correct data
- [ ] User can add mail account
- [ ] Auto-detect feature works
- [ ] Test connection feature works
- [ ] User can edit mail account
- [ ] User can delete mail account
- [ ] Emails are being processed (check Celery logs)
- [ ] User can logout
- [ ] Protected routes redirect to login when not authenticated

### Performance Tests
- [ ] Page load times < 2 seconds
- [ ] API response times < 500ms
- [ ] Email processing completes within interval
- [ ] No memory leaks in long-running processes

### Security Tests
- [ ] HTTPS enforced on all pages
- [ ] Passwords not visible in logs
- [ ] API requires authentication
- [ ] CORS properly configured
- [ ] SQL injection protection verified
- [ ] XSS protection enabled

---

**Deployment Date**: __________  
**Deployed By**: __________  
**Production URL**: __________  
**Version**: 2.0.0

---

## 🎉 Congratulations!

If all checkboxes above are complete, your multi-tenant InboxConverge with web interface is successfully deployed and ready to serve users!
