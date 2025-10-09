# Terraform variables for RAG Medical Assistant GCP deployment

variable "project_id" {
  description = "The GCP project ID where resources will be created"
  type        = string
  validation {
    condition     = length(var.project_id) > 0
    error_message = "Project ID must not be empty."
  }
}

variable "region" {
  description = "The GCP region for regional resources"
  type        = string
  default     = "us-central1"
  validation {
    condition = contains([
      "us-central1", "us-east1", "us-west1", "us-west2",
      "europe-west1", "europe-west2", "europe-west3",
      "asia-east1", "asia-northeast1", "asia-southeast1"
    ], var.region)
    error_message = "Region must be a valid GCP region."
  }
}

variable "zone" {
  description = "The GCP zone for zonal resources"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "domain_name" {
  description = "Custom domain name for the application (optional)"
  type        = string
  default     = ""
}

variable "database_tier" {
  description = "Cloud SQL database tier"
  type        = string
  default     = "db-f1-micro"
  validation {
    condition = contains([
      "db-f1-micro", "db-g1-small", "db-n1-standard-1",
      "db-n1-standard-2", "db-n1-standard-4"
    ], var.database_tier)
    error_message = "Database tier must be a valid Cloud SQL tier."
  }
}

variable "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 1
  validation {
    condition     = var.redis_memory_size_gb >= 1 && var.redis_memory_size_gb <= 300
    error_message = "Redis memory size must be between 1 and 300 GB."
  }
}

variable "enable_backup" {
  description = "Enable automated backups for Cloud SQL"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention must be between 1 and 365 days."
  }
}

variable "enable_monitoring" {
  description = "Enable Cloud Monitoring and Logging"
  type        = bool
  default     = true
}

variable "enable_security_policy" {
  description = "Enable Cloud Armor security policy"
  type        = bool
  default     = true
}

variable "rate_limit_requests_per_minute" {
  description = "Rate limit for requests per minute per IP"
  type        = number
  default     = 100
  validation {
    condition     = var.rate_limit_requests_per_minute >= 10 && var.rate_limit_requests_per_minute <= 1000
    error_message = "Rate limit must be between 10 and 1000 requests per minute."
  }
}

variable "storage_bucket_location" {
  description = "Cloud Storage bucket location"
  type        = string
  default     = "US"
  validation {
    condition = contains([
      "US", "EU", "ASIA", "us-central1", "us-east1",
      "europe-west1", "asia-east1"
    ], var.storage_bucket_location)
    error_message = "Storage location must be a valid Cloud Storage location."
  }
}

variable "vpc_cidr_range" {
  description = "CIDR range for the VPC subnet"
  type        = string
  default     = "10.0.0.0/24"
  validation {
    condition     = can(cidrhost(var.vpc_cidr_range, 0))
    error_message = "VPC CIDR range must be a valid CIDR block."
  }
}

variable "connector_cidr_range" {
  description = "CIDR range for the VPC Access Connector"
  type        = string
  default     = "10.8.0.0/28"
  validation {
    condition     = can(cidrhost(var.connector_cidr_range, 0))
    error_message = "Connector CIDR range must be a valid CIDR block."
  }
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    project     = "rag-medical-assistant"
    environment = "production"
    managed-by  = "terraform"
  }
}

variable "deletion_protection" {
  description = "Enable deletion protection for critical resources"
  type        = bool
  default     = true
}

variable "ssl_policy" {
  description = "SSL policy for HTTPS load balancer"
  type        = string
  default     = "MODERN"
  validation {
    condition     = contains(["COMPATIBLE", "MODERN", "RESTRICTED"], var.ssl_policy)
    error_message = "SSL policy must be one of: COMPATIBLE, MODERN, RESTRICTED."
  }
}

variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run service"
  type        = string
  default     = "2"
  validation {
    condition = contains([
      "1", "2", "4", "6", "8"
    ], var.cloud_run_cpu)
    error_message = "Cloud Run CPU must be one of: 1, 2, 4, 6, 8."
  }
}

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run service"
  type        = string
  default     = "4Gi"
  validation {
    condition = contains([
      "512Mi", "1Gi", "2Gi", "4Gi", "8Gi", "16Gi", "32Gi"
    ], var.cloud_run_memory)
    error_message = "Cloud Run memory must be a valid memory size."
  }
}

variable "cloud_run_max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 100
  validation {
    condition     = var.cloud_run_max_instances >= 1 && var.cloud_run_max_instances <= 1000
    error_message = "Max instances must be between 1 and 1000."
  }
}

variable "cloud_run_min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 1
  validation {
    condition     = var.cloud_run_min_instances >= 0 && var.cloud_run_min_instances <= 100
    error_message = "Min instances must be between 0 and 100."
  }
}

variable "enable_cdn" {
  description = "Enable Cloud CDN for static content"
  type        = bool
  default     = true
}

variable "notification_email" {
  description = "Email address for monitoring notifications"
  type        = string
  default     = ""
  validation {
    condition     = var.notification_email == "" || can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.notification_email))
    error_message = "Notification email must be a valid email address or empty."
  }
}