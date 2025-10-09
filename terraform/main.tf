# Terraform configuration for RAG Medical Assistant on Google Cloud Platform
# This creates all necessary infrastructure for production deployment

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.0"
    }
  }
}

# Variables
variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "domain_name" {
  description = "Custom domain name for the application"
  type        = string
  default     = ""
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "sql-component.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "storage-component.googleapis.com",
    "vpcaccess.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudresourcemanager.googleapis.com"
  ])

  service = each.value
  project = var.project_id

  disable_dependent_services = true
}

# VPC Network
resource "google_compute_network" "rag_vpc" {
  name                    = "rag-medical-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Subnet
resource "google_compute_subnetwork" "rag_subnet" {
  name          = "rag-medical-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.rag_vpc.id
  project       = var.project_id

  private_ip_google_access = true
}

# Private Service Connection for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "rag-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.rag_vpc.id
  project       = var.project_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.rag_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "rag_connector" {
  name          = "rag-connector"
  region        = var.region
  network       = google_compute_network.rag_vpc.name
  ip_cidr_range = "10.8.0.0/28"
  project       = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Cloud SQL Database
resource "google_sql_database_instance" "rag_postgres" {
  name             = "rag-medical-db-${var.environment}"
  database_version = "POSTGRES_14"
  region           = var.region
  project          = var.project_id

  settings {
    tier                        = "db-f1-micro"
    availability_type           = "ZONAL"
    disk_type                   = "PD_SSD"
    disk_size                   = 20
    disk_autoresize             = true
    disk_autoresize_limit       = 100
    deletion_protection_enabled = false

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.rag_vpc.id
      enable_private_path_for_google_cloud_services = true
    }

    database_flags {
      name  = "log_statement"
      value = "all"
    }
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "rag_database" {
  name     = "rag_medical"
  instance = google_sql_database_instance.rag_postgres.name
  project  = var.project_id
}

resource "google_sql_user" "rag_user" {
  name     = "rag_user"
  instance = google_sql_database_instance.rag_postgres.name
  password = random_password.db_password.result
  project  = var.project_id
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Cloud Memorystore (Redis)
resource "google_redis_instance" "rag_redis" {
  name           = "rag-medical-redis-${var.environment}"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
  project        = var.project_id

  authorized_network = google_compute_network.rag_vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }

  depends_on = [google_project_service.required_apis]
}

# Cloud Storage Bucket
resource "google_storage_bucket" "rag_storage" {
  name          = "${var.project_id}-rag-storage"
  location      = var.region
  project       = var.project_id
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

# Service Account for Cloud Run
resource "google_service_account" "rag_service_account" {
  account_id   = "rag-medical-sa"
  display_name = "RAG Medical Assistant Service Account"
  project      = var.project_id
}

# IAM roles for service account
resource "google_project_iam_member" "rag_sa_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.rag_service_account.email}"
}

# Secret Manager secrets
resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"
  project   = var.project_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql://${google_sql_user.rag_user.name}:${random_password.db_password.result}@${google_sql_database_instance.rag_postgres.private_ip_address}:5432/${google_sql_database.rag_database.name}"
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "redis-url"
  project   = var.project_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = "redis://${google_redis_instance.rag_redis.host}:${google_redis_instance.rag_redis.port}/0"
}

# Placeholder secrets (to be updated manually)
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"
  project   = var.project_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "jwt-secret"
  project   = var.project_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "google_secret_manager_secret" "flask_secret_key" {
  secret_id = "flask-secret-key"
  project   = var.project_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "flask_secret_key" {
  secret      = google_secret_manager_secret.flask_secret_key.id
  secret_data = random_password.flask_secret.result
}

resource "random_password" "flask_secret" {
  length  = 64
  special = true
}

# Cloud Armor Security Policy
resource "google_compute_security_policy" "rag_security_policy" {
  name    = "rag-medical-security-policy"
  project = var.project_id

  rule {
    action   = "allow"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Allow all traffic"
  }

  rule {
    action   = "deny(403)"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default deny rule"
  }

  # Rate limiting rule
  rule {
    action   = "rate_based_ban"
    priority = "100"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      ban_duration_sec = 300
    }
    description = "Rate limiting rule"
  }
}

# Outputs
output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "vpc_network" {
  description = "The VPC network name"
  value       = google_compute_network.rag_vpc.name
}

output "database_connection_name" {
  description = "The Cloud SQL connection name"
  value       = google_sql_database_instance.rag_postgres.connection_name
}

output "database_private_ip" {
  description = "The Cloud SQL private IP"
  value       = google_sql_database_instance.rag_postgres.private_ip_address
}

output "redis_host" {
  description = "The Redis host"
  value       = google_redis_instance.rag_redis.host
}

output "storage_bucket" {
  description = "The Cloud Storage bucket name"
  value       = google_storage_bucket.rag_storage.name
}

output "service_account_email" {
  description = "The service account email"
  value       = google_service_account.rag_service_account.email
}

output "vpc_connector" {
  description = "The VPC Access Connector name"
  value       = google_vpc_access_connector.rag_connector.name
}