# RAG Medical Assistant - Google Cloud Platform Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the RAG Medical Assistant to Google Cloud Platform (GCP) using a production-ready, scalable architecture.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cloud CDN     │    │  Load Balancer   │    │   Cloud Armor   │
│   (Static)      │    │   (HTTPS/SSL)    │    │  (Security)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌──────────────────┐
                    │   Cloud Run      │
                    │ (Auto-scaling)   │
                    └──────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Cloud SQL     │ │ Cloud Storage   │ │ Cloud Memory-   │
│ (PostgreSQL)    │ │ (File uploads)  │ │ store (Redis)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Prerequisites

### Required Tools
- **Google Cloud SDK** (gcloud CLI)
- **Terraform** (v1.0+)
- **Docker** (for local testing)
- **Git** (for version control)

### GCP Account Setup
1. Create a Google Cloud Platform account
2. Create a new project or select existing one
3. Enable billing for the project
4. Install and authenticate Google Cloud SDK

## Quick Start Deployment

### 1. Clone and Setup
```bash
git clone <your-repository-url>
cd rag-medical-assistant
```

### 2. Automated Deployment
```bash
# Run the automated deployment script
./scripts/deploy-gcp.sh
```

The script will:
- Validate prerequisites
- Collect deployment configuration
- Set up GCP project and APIs
- Deploy infrastructure with Terraform
- Build and deploy the application
- Run health checks

## Manual Deployment Steps

### Step 1: Environment Setup

1. **Authenticate with Google Cloud:**
```bash
gcloud auth login
gcloud auth application-default login
```

2. **Set your project:**
```bash
gcloud config set project YOUR_PROJECT_ID
```

3. **Enable required APIs:**
```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  storage-component.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### Step 2: Infrastructure Deployment

1. **Configure Terraform variables:**
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

2. **Deploy infrastructure:**
```bash
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

### Step 3: Secrets Management

1. **Create required secrets:**
```bash
# Generate and store JWT secret
echo -n "$(openssl rand -base64 32)" | gcloud secrets create jwt-secret --data-file=-

# Generate and store Flask secret key
echo -n "$(openssl rand -base64 32)" | gcloud secrets create flask-secret-key --data-file=-

# Store OpenAI API key (replace with your actual key)
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
```

### Step 4: Application Deployment

1. **Build and push Docker image:**
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/rag-medical-assistant:latest .
```

2. **Deploy to Cloud Run:**
```bash
# Update project ID in cloud-run.yaml
sed -i 's/PROJECT_ID/YOUR_PROJECT_ID/g' gcp/cloud-run.yaml

# Deploy the service
gcloud run services replace gcp/cloud-run.yaml --region=us-central1
```

### Step 5: Database Setup

1. **Run database migrations:**
```bash
./scripts/migrate-database.sh --environment gcp --project YOUR_PROJECT_ID --instance YOUR_INSTANCE_NAME
```

## Configuration Options

### Terraform Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `project_id` | GCP Project ID | - | Yes |
| `region` | GCP Region | `us-central1` | No |
| `environment` | Environment name | `prod` | No |
| `domain_name` | Custom domain | `""` | No |
| `database_tier` | Cloud SQL tier | `db-f1-micro` | No |
| `redis_memory_size_gb` | Redis memory | `1` | No |
| `enable_monitoring` | Enable monitoring | `true` | No |
| `enable_security_policy` | Enable Cloud Armor | `true` | No |

### Environment Variables

The application uses the following environment variables (managed via Secret Manager):

| Variable | Description | Source |
|----------|-------------|--------|
| `DATABASE_URL` | PostgreSQL connection | Auto-generated |
| `REDIS_URL` | Redis connection | Auto-generated |
| `OPENAI_API_KEY` | OpenAI API key | Manual setup |
| `JWT_SECRET` | JWT signing key | Auto-generated |
| `FLASK_SECRET_KEY` | Flask session key | Auto-generated |

## Custom Domain Setup

### 1. Configure Domain in Terraform
```hcl
domain_name = "your-domain.com"
```

### 2. Update DNS Records
Point your domain to the load balancer IP:
```bash
# Get the load balancer IP
terraform output load_balancer_ip_address

# Create A record: your-domain.com -> LOAD_BALANCER_IP
```

### 3. SSL Certificate
The managed SSL certificate will be automatically provisioned and may take 10-60 minutes to become active.

## Monitoring and Logging

### Cloud Monitoring Dashboard
Access your custom dashboard:
```
https://console.cloud.google.com/monitoring/dashboards/custom/DASHBOARD_ID
```

### Key Metrics Monitored
- **Request Count** - Requests per second
- **Response Latency** - 95th percentile response time
- **Error Rate** - 4xx/5xx error rates
- **CPU/Memory Usage** - Resource utilization
- **Database Connections** - Connection pool usage

### Alerting
Alerts are configured for:
- Service downtime (uptime check failures)
- High error rates (>10 errors/5min)
- High resource usage (>80% CPU/Memory)
- Database connection issues

### Log Analysis
```bash
# View application logs
gcloud logs tail --follow --filter="resource.type=cloud_run_revision"

# View error logs only
gcloud logs tail --follow --filter="resource.type=cloud_run_revision AND severity>=ERROR"
```

## Cost Optimization

### Estimated Monthly Costs

| Service | Configuration | Estimated Cost |
|---------|---------------|----------------|
| Cloud Run | 2 CPU, 4GB RAM, moderate traffic | $10-50 |
| Cloud SQL | db-f1-micro with backups | $7-15 |
| Cloud Memorystore | 1GB Redis | $30-50 |
| Cloud Storage | File uploads, logs | $1-5 |
| Load Balancer | HTTPS, CDN | $5-20 |
| Monitoring | Metrics, logs | $0-10 |
| **Total** | | **$53-150/month** |

### Cost Optimization Tips

1. **Right-size Resources:**
   - Start with smaller instance types
   - Monitor usage and scale as needed
   - Use Cloud Run's pay-per-request model

2. **Optimize Storage:**
   - Set lifecycle policies for logs
   - Use appropriate storage classes
   - Clean up unused files regularly

3. **Monitor Usage:**
   - Set up billing alerts
   - Review cost reports monthly
   - Use committed use discounts for predictable workloads

4. **Development Environment:**
   - Use smaller tiers for dev/staging
   - Shut down non-production resources when not needed
   - Share development instances across team

## Scaling Strategies

### Horizontal Scaling
Cloud Run automatically scales based on:
- **Request volume** - Scales up with increased traffic
- **CPU utilization** - Adds instances when CPU is high
- **Memory usage** - Scales when memory pressure increases

### Configuration:
```yaml
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "100"
        run.googleapis.com/cpu-throttling: "false"
```

### Database Scaling
- **Vertical scaling:** Increase CPU/memory of Cloud SQL instance
- **Read replicas:** Add read replicas for read-heavy workloads
- **Connection pooling:** Use PgBouncer for connection management

### Redis Scaling
- **Memory scaling:** Increase Redis instance memory
- **High availability:** Enable Redis HA for production
- **Clustering:** Use Redis cluster for large datasets

## Security Best Practices

### 1. Network Security
- **VPC:** All services run in private VPC
- **Private IP:** Database uses private IP only
- **Cloud Armor:** DDoS protection and rate limiting
- **HTTPS Only:** All traffic encrypted in transit

### 2. Identity and Access Management
- **Service Accounts:** Minimal required permissions
- **Secret Manager:** All sensitive data encrypted
- **Audit Logging:** All access logged and monitored

### 3. Application Security
- **Input Validation:** All user inputs validated
- **SQL Injection Protection:** Parameterized queries
- **XSS Protection:** Content Security Policy headers
- **Rate Limiting:** API rate limiting implemented

## Troubleshooting

### Common Issues

#### 1. Deployment Failures
```bash
# Check Cloud Build logs
gcloud builds list --limit=5
gcloud builds log BUILD_ID

# Check Cloud Run deployment
gcloud run services describe rag-medical-assistant --region=us-central1
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
gcloud sql connect INSTANCE_NAME --user=postgres

# Check VPC connector
gcloud compute networks vpc-access connectors describe CONNECTOR_NAME --region=us-central1
```

#### 3. SSL Certificate Issues
```bash
# Check certificate status
gcloud compute ssl-certificates describe CERT_NAME --global

# Common causes:
# - DNS not pointing to load balancer IP
# - Certificate provisioning takes time (10-60 minutes)
# - Domain verification required
```

#### 4. High Latency/Performance Issues
```bash
# Check Cloud Run metrics
gcloud run services describe rag-medical-assistant --region=us-central1 --format="yaml"

# Optimize:
# - Increase CPU allocation
# - Add more memory
# - Check database query performance
# - Enable Cloud CDN for static content
```

### Debug Commands

```bash
# View service logs
gcloud logs tail --follow --filter="resource.type=cloud_run_revision AND resource.labels.service_name=rag-medical-assistant"

# Check service health
curl -f https://your-service-url/health

# Test database connection
gcloud sql connect INSTANCE_NAME --user=postgres --database=rag_medical

# View Terraform state
terraform show
terraform state list

# Check resource quotas
gcloud compute project-info describe --project=PROJECT_ID
```

### Performance Tuning

#### Cloud Run Optimization
```yaml
# Increase resources for better performance
resources:
  limits:
    cpu: "4"
    memory: "8Gi"

# Reduce cold starts
annotations:
  autoscaling.knative.dev/minScale: "2"
  run.googleapis.com/execution-environment: gen2
```

#### Database Optimization
```sql
-- Monitor slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_chat_messages_session_created ON chat_messages(session_id, created_at);
```

## Backup and Disaster Recovery

### Automated Backups
- **Cloud SQL:** Daily automated backups with 7-day retention
- **Point-in-time recovery:** Available for last 7 days
- **Cross-region backups:** Optional for disaster recovery

### Manual Backup
```bash
# Create manual backup
gcloud sql backups create --instance=INSTANCE_NAME --description="Manual backup before deployment"

# Export database
gcloud sql export sql INSTANCE_NAME gs://BUCKET_NAME/backup-$(date +%Y%m%d).sql --database=rag_medical
```

### Disaster Recovery Plan
1. **RTO (Recovery Time Objective):** < 4 hours
2. **RPO (Recovery Point Objective):** < 1 hour
3. **Multi-region deployment:** For critical production workloads
4. **Automated failover:** Using Cloud SQL HA configuration

## Maintenance and Updates

### Regular Maintenance Tasks
1. **Weekly:**
   - Review monitoring dashboards
   - Check error logs
   - Verify backup completion

2. **Monthly:**
   - Update dependencies
   - Review cost reports
   - Security patch updates

3. **Quarterly:**
   - Performance review
   - Capacity planning
   - Security audit

### Update Deployment
```bash
# Update application code
git pull origin main

# Build new image
gcloud builds submit --tag gcr.io/PROJECT_ID/rag-medical-assistant:latest .

# Deploy update
gcloud run services replace gcp/cloud-run.yaml --region=us-central1

# Run database migrations if needed
./scripts/migrate-database.sh --environment gcp --project PROJECT_ID --instance INSTANCE_NAME
```

## Support and Resources

### Documentation Links
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

### Monitoring URLs
- **Cloud Console:** `https://console.cloud.google.com/`
- **Monitoring Dashboard:** `https://console.cloud.google.com/monitoring`
- **Cloud Run Services:** `https://console.cloud.google.com/run`
- **Cloud SQL:** `https://console.cloud.google.com/sql`

### Emergency Contacts
- **GCP Support:** Available through Cloud Console
- **Application Logs:** Cloud Logging in GCP Console
- **Status Page:** `https://status.cloud.google.com/`

---

## Conclusion

This deployment guide provides a comprehensive, production-ready setup for the RAG Medical Assistant on Google Cloud Platform. The architecture is designed for:

- **Scalability:** Auto-scaling based on demand
- **Reliability:** High availability with automated backups
- **Security:** Enterprise-grade security controls
- **Cost-effectiveness:** Pay-per-use pricing model
- **Maintainability:** Infrastructure as Code with Terraform

For additional support or questions, refer to the troubleshooting section or consult the GCP documentation links provided above.