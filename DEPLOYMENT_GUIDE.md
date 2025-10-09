# 🚀 Production Deployment Guide

## 📋 Overview

This guide covers deploying your custom ML RAG Medical Assistant to production with Docker, monitoring, and CI/CD.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │────│  React Frontend  │    │  Node.js API    │
│   Load Balancer │    │  (Static Files)  │    │  (Business Logic)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  │
         ┌─────────────────────────┼─────────────────────────┐
         │                        │                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Flask ML API   │    │   PostgreSQL     │    │     Redis       │
│  (Custom Models)│    │   (Database)     │    │    (Cache)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│     MLflow      │    │   Prometheus     │    │    Grafana      │
│  (Experiments)  │    │  (Monitoring)    │    │  (Dashboard)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Deployment

### 1. Environment Setup

```bash
# Clone your repository
git clone <your-repo-url>
cd RAG

# Create environment file
cp .env.example .env
```

Edit `.env`:
```bash
# API Keys
OPENAI_API_KEY=your_openai_key_here

# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/rag_medical
REDIS_URL=redis://redis:6379/0

# ML Configuration
ML_MODEL_PATH=/app/models
CUDA_VISIBLE_DEVICES=0

# Security
JWT_SECRET=your_jwt_secret_here
FLASK_SECRET_KEY=your_flask_secret_here
```

### 2. Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f rag-medical-app
```

### 3. Access Your Application

- **Frontend**: http://localhost
- **API Documentation**: http://localhost/api/docs
- **ML API**: http://localhost/ml/docs
- **MLflow**: http://localhost:5001
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 🔧 Production Configuration

### SSL/HTTPS Setup

1. **Get SSL Certificate** (Let's Encrypt):
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com
```

2. **Update Nginx Config**:
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Your existing configuration...
}
```

### Environment Variables

Create production `.env`:
```bash
# Production settings
NODE_ENV=production
FLASK_ENV=production

# Database (use managed service in production)
DATABASE_URL=postgresql://user:pass@your-db-host:5432/rag_medical

# Redis (use managed service)
REDIS_URL=redis://your-redis-host:6379/0

# Security
JWT_SECRET=your_super_secure_jwt_secret
FLASK_SECRET_KEY=your_super_secure_flask_key

# ML Configuration
ML_MODEL_PATH=/app/models
CUDA_VISIBLE_DEVICES=0

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=your_secure_password
```

## 🏥 Health Checks

### Application Health

```bash
# Check application health
curl http://localhost/health

# Check ML API health
curl http://localhost/ml/health

# Check database connection
curl http://localhost/api/health/db
```

### Service Monitoring

```bash
# View service status
docker-compose ps

# Check resource usage
docker stats

# View application logs
docker-compose logs -f --tail=100 rag-medical-app
```

## 📊 Monitoring Setup

### Prometheus Metrics

The application exposes metrics at:
- `/metrics` - Application metrics
- `/ml/metrics` - ML model metrics

### Grafana Dashboards

Import pre-configured dashboards:
1. Application Performance
2. ML Model Performance
3. Infrastructure Metrics
4. Business Metrics

### Alerts Configuration

Set up alerts for:
- High response times
- Model inference failures
- Database connection issues
- High memory usage

## 🔄 CI/CD Pipeline

### GitHub Actions

The pipeline includes:
1. **Testing** - Unit tests, integration tests
2. **Security** - Vulnerability scanning
3. **Building** - Docker image creation
4. **Deployment** - Automated deployment

### Manual Deployment

```bash
# Build production image
docker build -t rag-medical:latest .

# Tag for registry
docker tag rag-medical:latest your-registry/rag-medical:latest

# Push to registry
docker push your-registry/rag-medical:latest

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d
```

## 🔒 Security Considerations

### 1. API Security
- Rate limiting configured in Nginx
- JWT authentication for protected endpoints
- Input validation and sanitization

### 2. Database Security
- Connection encryption
- Regular backups
- Access control

### 3. ML Model Security
- Model versioning and validation
- Secure model storage
- Input sanitization for ML endpoints

## 📈 Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  rag-medical-app:
    deploy:
      replicas: 3
    # ... rest of configuration
```

### Load Balancing

```nginx
upstream app_servers {
    server app1:80;
    server app2:80;
    server app3:80;
}
```

### Database Scaling
- Read replicas for PostgreSQL
- Redis clustering for cache
- Connection pooling

## 🚨 Troubleshooting

### Common Issues

**1. Out of Memory**
```bash
# Check memory usage
docker stats

# Increase memory limits
docker-compose up -d --scale rag-medical-app=1 --memory=4g
```

**2. ML Model Loading Issues**
```bash
# Check model files
docker exec -it rag_rag-medical-app_1 ls -la /app/models

# Check ML API logs
docker-compose logs flask-ml
```

**3. Database Connection**
```bash
# Test database connection
docker exec -it rag_postgres_1 psql -U postgres -d rag_medical

# Check database logs
docker-compose logs postgres
```

### Performance Optimization

**1. Model Optimization**
```python
# Use model quantization
model = torch.quantization.quantize_dynamic(
    model, {torch.nn.Linear}, dtype=torch.qint8
)

# Enable mixed precision
with torch.cuda.amp.autocast():
    outputs = model(inputs)
```

**2. Caching Strategy**
```python
# Cache embeddings
@cache.memoize(timeout=3600)
def get_embedding(text):
    return model.encode(text)
```

## 📋 Maintenance

### Regular Tasks

**Daily:**
- Check application health
- Monitor resource usage
- Review error logs

**Weekly:**
- Update dependencies
- Backup database
- Review performance metrics

**Monthly:**
- Security updates
- Model retraining evaluation
- Capacity planning

### Backup Strategy

```bash
# Database backup
docker exec rag_postgres_1 pg_dump -U postgres rag_medical > backup.sql

# Model backup
docker cp rag_rag-medical-app_1:/app/models ./models_backup

# Configuration backup
cp docker-compose.yml docker-compose.yml.backup
```

## 🎯 Production Checklist

- [ ] SSL certificate configured
- [ ] Environment variables set
- [ ] Database migrations applied
- [ ] Models fine-tuned and deployed
- [ ] Monitoring dashboards configured
- [ ] Backup strategy implemented
- [ ] Security scanning completed
- [ ] Performance testing done
- [ ] Documentation updated
- [ ] Team trained on deployment

## 🆘 Support

### Logs Location
- Application: `/app/logs/`
- Nginx: `/var/log/nginx/`
- Supervisor: `/var/log/supervisor/`

### Emergency Contacts
- DevOps Team: devops@yourcompany.com
- ML Team: ml@yourcompany.com
- Security Team: security@yourcompany.com

---

🎉 **Your RAG Medical Assistant is now production-ready!**

For additional support, check the troubleshooting section or contact the development team.