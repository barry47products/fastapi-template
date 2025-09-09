# Deployment Setup Guide

This guide explains how to configure GitHub environments and secrets for automated deployments.

## GitHub Environment Setup

### 1. Create Environments

In your GitHub repository, go to **Settings → Environments** and create:

#### Staging Environment

- **Name**: `staging`
- **URL**: `https://staging.yourapp.com` (optional)
- **Protection Rules**:
  - Deployment branches: `main` and `develop`
  - Required reviewers: None (optional)

#### Production Environment

- **Name**: `production`
- **URL**: `https://api.yourapp.com` (optional)
- **Protection Rules**:
  - Deployment branches: `main` only
  - Required reviewers: At least 1
  - Wait timer: 5 minutes
  - Prevent self-review: Enabled

### 2. Environment Secrets

Configure these secrets for each environment in **Settings → Environments → [Environment] → Environment Secrets**:

#### Required Secrets

| Secret Name         | Description                   | Example Value                         |
| ------------------- | ----------------------------- | ------------------------------------- |
| `DATABASE_URL`      | PostgreSQL connection string  | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL`         | Redis connection string       | `redis://:pass@host:6379`             |
| `INTERNAL_API_KEYS` | Comma-separated API keys      | `key1,key2,key3`                      |
| `WEBHOOK_SECRET`    | Webhook authentication secret | `your-secure-webhook-secret`          |
| `POSTGRES_PASSWORD` | Database password             | `secure-db-password`                  |
| `REDIS_PASSWORD`    | Redis password                | `secure-redis-password`               |
| `GRAFANA_PASSWORD`  | Grafana admin password        | `secure-grafana-password`             |

#### Optional Secrets

| Secret Name                      | Description          | Default                              |
| -------------------------------- | -------------------- | ------------------------------------ |
| `CORS_ORIGINS`                   | Allowed CORS origins | Environment-specific URLs            |
| `LOG_LEVEL`                      | Logging level        | `INFO` for prod, `DEBUG` for staging |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | API rate limit       | `60` for prod, `300` for staging     |

### 3. Repository Secrets

Configure these at the repository level in **Settings → Secrets and Variables → Actions**:

| Secret Name   | Description                    | Required                 |
| ------------- | ------------------------------ | ------------------------ |
| `SONAR_TOKEN` | SonarQube authentication token | Yes (if using SonarQube) |

## Deployment Infrastructure Requirements

### Server Requirements

Your deployment servers should have:

- **Docker**: Version 20.10+
- **Docker Compose**: V2 (included with Docker Desktop)
- **SSL Certificates**: For HTTPS termination
- **Load Balancer**: For production (optional)
- **Monitoring**: Prometheus/Grafana endpoints

### Network Configuration

Ensure these ports are accessible:

| Port | Service                  | Access            |
| ---- | ------------------------ | ----------------- |
| 80   | HTTP (redirect to HTTPS) | Public            |
| 443  | HTTPS                    | Public            |
| 5432 | PostgreSQL               | Internal only     |
| 6379 | Redis                    | Internal only     |
| 9090 | Prometheus               | Internal/VPN only |
| 3000 | Grafana                  | Internal/VPN only |

## Deployment Workflows

### Automatic Deployments

**Staging**: Triggered on push to `main` or `develop` branches

```bash
git push origin main  # Auto-deploys to staging
```

**Production**: Requires manual approval after staging success

- Navigate to **Actions** tab in GitHub
- Find the deployment workflow
- Click **Review deployments** and approve

### Manual Deployments

Use workflow dispatch for manual deployments:

```bash
# Deploy to staging
gh workflow run deploy.yml -f environment=staging

# Deploy to production
gh workflow run deploy.yml -f environment=production

# Force deploy (skip tests)
gh workflow run deploy.yml -f environment=staging -f force_deploy=true
```

## Monitoring and Alerts

### Health Checks

Automated health checks run every 15 minutes:

- Application status endpoints
- Database connectivity
- Cache connectivity
- SSL certificate validity

### Performance Monitoring

Available through:

- **Prometheus**: Metrics collection at `:9091`
- **Grafana**: Dashboards at `:3000`
- **Application Metrics**: `/metrics` endpoint (restricted)

### Alerting

Failed health checks automatically:

- Create GitHub issues with `alert` label
- Include troubleshooting links
- Provide escalation procedures

## Troubleshooting

### Common Deployment Issues

**Environment not found**: Create GitHub environments first

```bash
# Run the environment setup workflow
gh workflow run environment-setup.yml -f environment=staging
```

**Secrets not accessible**: Check environment secret configuration

```bash
# Verify secrets are set in Settings → Environments → [env] → Environment Secrets
```

**Docker build failures**: Check image registry permissions

```bash
# Ensure GITHUB_TOKEN has packages:write permission
```

### Manual Deployment Commands

If automated deployment fails, deploy manually:

```bash
# SSH to deployment server
ssh user@server

# Navigate to application directory
cd /path/to/app

# Create environment file
cp .env.example .env.prod
# Edit .env.prod with production values

# Deploy using script
./scripts/deployment/deploy-prod.sh

# Or manual docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Rollback Procedures

**Automatic Rollback**: Triggered on deployment failure

```bash
# Check rollback job in GitHub Actions
```

**Manual Rollback**: Use previous image tag

```bash
# SSH to server
ssh user@server

# Pull previous image
docker pull ghcr.io/your-org/fastapi-template:previous-tag

# Update docker-compose with previous tag
# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

## Security Considerations

### Secret Management

- **Never commit secrets** to repository
- **Use strong passwords** (min 16 characters)
- **Rotate secrets regularly** (quarterly)
- **Limit secret access** to required environments only

### Access Control

- **Production approvals**: Require multiple reviewers
- **Branch protection**: Limit production deploys to `main`
- **Audit logging**: Monitor deployment activities
- **Principle of least privilege**: Minimal required permissions

### SSL/TLS

- **Use valid certificates** (not self-signed)
- **Enable HSTS** for security headers
- **Regular certificate renewal** (automated via cert-bot)
- **Strong cipher suites** only

## Maintenance

### Regular Tasks

**Daily**:

- Monitor application health
- Check error rates and performance
- Review security alerts

**Weekly**:

- Update dependencies
- Review and rotate logs
- Test backup/restore procedures

**Monthly**:

- Security scans and updates
- Performance optimization
- Disaster recovery testing

### Backup and Recovery

**Database Backups**:

```bash
# Automated daily backups
./scripts/maintenance/backup.sh

# Manual backup
docker exec fastapi-prod-postgres pg_dump -U postgres fastapi_prod > backup.sql
```

**Application Backups**:

- Docker images stored in GitHub Container Registry
- Configuration files in Git repository
- Secrets managed in GitHub environments

This setup provides enterprise-grade deployment automation with proper security, monitoring, and maintenance procedures.
