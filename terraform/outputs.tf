# Terraform outputs for RAG Medical Assistant GCP deployment

output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "environment" {
  description = "The deployment environment"
  value       = var.environment
}

# VPC and Networking
output "vpc_network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.vpc_network.name
}

output "vpc_network_id" {
  description = "ID of the VPC network"
  value       = google_compute_network.vpc_network.id
}

output "vpc_subnet_name" {
  description = "Name of the VPC subnet"
  value       = google_compute_subnetwork.vpc_subnet.name
}

output "vpc_connector_name" {
  description = "Name of the VPC Access Connector"
  value       = google_vpc_access_connector.connector.name
}

# Cloud SQL Database
output "database_instance_name" {
  description = "Name of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.name
}

output "database_connection_name" {
  description = "Connection name for the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_private_ip" {
  description = "Private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
  sensitive   = true
}

output "database_public_ip" {
  description = "Public IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.public_ip_address
  sensitive   = true
}

# Redis (Cloud Memorystore)
output "redis_instance_id" {
  description = "ID of the Redis instance"
  value       = google_redis_instance.cache.id
}

output "redis_host" {
  description = "Host IP of the Redis instance"
  value       = google_redis_instance.cache.host
  sensitive   = true
}

output "redis_port" {
  description = "Port of the Redis instance"
  value       = google_redis_instance.cache.port
}

output "redis_memory_size" {
  description = "Memory size of the Redis instance in GB"
  value       = google_redis_instance.cache.memory_size_gb
}

# Cloud Storage
output "storage_bucket_name" {
  description = "Name of the Cloud Storage bucket"
  value       = google_storage_bucket.app_storage.name
}

output "storage_bucket_url" {
  description = "URL of the Cloud Storage bucket"
  value       = google_storage_bucket.app_storage.url
}

# Service Account
output "service_account_email" {
  description = "Email of the service account"
  value       = google_service_account.app_service_account.email
}

output "service_account_id" {
  description = "ID of the service account"
  value       = google_service_account.app_service_account.id
}

# Secret Manager
output "secret_database_url_id" {
  description = "ID of the database URL secret"
  value       = google_secret_manager_secret.database_url.secret_id
}

output "secret_redis_url_id" {
  description = "ID of the Redis URL secret"
  value       = google_secret_manager_secret.redis_url.secret_id
}

output "secret_openai_api_key_id" {
  description = "ID of the OpenAI API key secret"
  value       = google_secret_manager_secret.openai_api_key.secret_id
}

output "secret_jwt_secret_id" {
  description = "ID of the JWT secret"
  value       = google_secret_manager_secret.jwt_secret.secret_id
}

output "secret_flask_secret_key_id" {
  description = "ID of the Flask secret key"
  value       = google_secret_manager_secret.flask_secret_key.secret_id
}

# Cloud Armor Security Policy
output "security_policy_name" {
  description = "Name of the Cloud Armor security policy"
  value       = var.enable_security_policy ? google_compute_security_policy.security_policy[0].name : null
}

output "security_policy_id" {
  description = "ID of the Cloud Armor security policy"
  value       = var.enable_security_policy ? google_compute_security_policy.security_policy[0].id : null
}

# Load Balancer (if domain is configured)
output "load_balancer_ip" {
  description = "IP address of the load balancer"
  value       = var.domain_name != "" ? google_compute_global_address.lb_ip[0].address : null
}

output "ssl_certificate_name" {
  description = "Name of the SSL certificate"
  value       = var.domain_name != "" ? google_compute_managed_ssl_certificate.ssl_cert[0].name : null
}

# Cloud Run Service URL (will be set after deployment)
output "cloud_run_service_url" {
  description = "URL of the Cloud Run service (set after deployment)"
  value       = "https://rag-medical-assistant-${var.environment}-${random_id.suffix.hex}-${substr(var.project_id, -8, -1)}.a.run.app"
}

# Monitoring and Logging
output "log_sink_name" {
  description = "Name of the Cloud Logging sink"
  value       = var.enable_monitoring ? google_logging_project_sink.app_logs[0].name : null
}

# Deployment Information
output "deployment_commands" {
  description = "Commands to deploy the application"
  value = {
    build_image = "gcloud builds submit --tag gcr.io/${var.project_id}/rag-medical-assistant:latest ."
    deploy_service = "gcloud run services replace gcp/cloud-run.yaml --region=${var.region}"
    get_service_url = "gcloud run services describe rag-medical-assistant --region=${var.region} --format='value(status.url)'"
  }
}

# Resource URLs for management
output "resource_urls" {
  description = "URLs to manage GCP resources"
  value = {
    cloud_sql = "https://console.cloud.google.com/sql/instances/${google_sql_database_instance.postgres.name}/overview?project=${var.project_id}"
    redis = "https://console.cloud.google.com/memorystore/redis/locations/${var.region}/instances/${google_redis_instance.cache.name}/details/overview?project=${var.project_id}"
    storage = "https://console.cloud.google.com/storage/browser/${google_storage_bucket.app_storage.name}?project=${var.project_id}"
    secret_manager = "https://console.cloud.google.com/security/secret-manager?project=${var.project_id}"
    cloud_run = "https://console.cloud.google.com/run?project=${var.project_id}"
    monitoring = "https://console.cloud.google.com/monitoring?project=${var.project_id}"
    logging = "https://console.cloud.google.com/logs?project=${var.project_id}"
  }
}

# Cost Estimation
output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown (USD)"
  value = {
    cloud_run = "~$10-50 (depending on traffic)"
    cloud_sql = var.database_tier == "db-f1-micro" ? "~$7-15" : "~$25-100"
    redis = "~$30-50 (1GB instance)"
    storage = "~$1-5 (depending on usage)"
    networking = "~$5-20"
    monitoring = "~$0-10"
    total_estimate = "~$53-240 per month"
    note = "Costs vary based on actual usage, traffic, and storage requirements"
  }
}

# Security and Compliance
output "security_features" {
  description = "Enabled security features"
  value = {
    private_ip_database = true
    vpc_connector = true
    secret_manager = true
    cloud_armor = var.enable_security_policy
    https_only = var.domain_name != ""
    iam_service_account = true
    backup_enabled = var.enable_backup
  }
}

# Random suffix for unique resource naming
resource "random_id" "suffix" {
  byte_length = 4
}

output "resource_suffix" {
  description = "Random suffix used for resource naming"
  value       = random_id.suffix.hex
}