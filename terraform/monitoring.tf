# Monitoring and Logging configuration for RAG Medical Assistant

# Enable required APIs for monitoring
resource "google_project_service" "monitoring_apis" {
  for_each = toset([
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "clouderrorreporting.googleapis.com",
    "cloudtrace.googleapis.com",
    "cloudprofiler.googleapis.com"
  ])
  
  project = var.project_id
  service = each.value
  
  disable_dependent_services = false
  disable_on_destroy        = false
}

# Cloud Logging sink for application logs
resource "google_logging_project_sink" "app_logs" {
  count       = var.enable_monitoring ? 1 : 0
  name        = "rag-medical-app-logs-${var.environment}"
  project     = var.project_id
  destination = "storage.googleapis.com/${google_storage_bucket.logs_bucket[0].name}"
  
  filter = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="rag-medical-assistant"
    OR
    resource.type="gce_instance"
    labels.app="rag-medical-assistant"
  EOT

  unique_writer_identity = true
}

# Storage bucket for logs
resource "google_storage_bucket" "logs_bucket" {
  count         = var.enable_monitoring ? 1 : 0
  name          = "${var.project_id}-rag-medical-logs-${var.environment}-${random_id.suffix.hex}"
  project       = var.project_id
  location      = var.storage_bucket_location
  force_destroy = !var.deletion_protection

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  versioning {
    enabled = false
  }

  labels = merge(var.labels, {
    purpose = "logging"
  })
}

# IAM binding for logging sink
resource "google_storage_bucket_iam_member" "logs_bucket_writer" {
  count  = var.enable_monitoring ? 1 : 0
  bucket = google_storage_bucket.logs_bucket[0].name
  role   = "roles/storage.objectCreator"
  member = google_logging_project_sink.app_logs[0].writer_identity
}

# Notification channel for alerts (email)
resource "google_monitoring_notification_channel" "email" {
  count        = var.enable_monitoring && var.notification_email != "" ? 1 : 0
  project      = var.project_id
  display_name = "RAG Medical Assistant Email Notifications"
  type         = "email"
  
  labels = {
    email_address = var.notification_email
  }
}

# Uptime check for the application
resource "google_monitoring_uptime_check_config" "app_uptime_check" {
  count        = var.enable_monitoring ? 1 : 0
  project      = var.project_id
  display_name = "RAG Medical Assistant Uptime Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = var.domain_name != "" ? var.domain_name : "rag-medical-assistant-${var.environment}.a.run.app"
    }
  }

  checker_type = "STATIC_IP_CHECKERS"
}

# Alert policy for uptime check failures
resource "google_monitoring_alert_policy" "uptime_alert" {
  count        = var.enable_monitoring ? 1 : 0
  project      = var.project_id
  display_name = "RAG Medical Assistant - Uptime Check Failed"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Uptime check failed"
    
    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\""
      duration        = "300s"
      comparison      = "COMPARISON_EQUAL"
      threshold_value = 0
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_NEXT_OLDER"
      }
    }
  }

  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email[0].name] : []

  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert policy for high error rate
resource "google_monitoring_alert_policy" "error_rate_alert" {
  count        = var.enable_monitoring ? 1 : 0
  project      = var.project_id
  display_name = "RAG Medical Assistant - High Error Rate"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "High 5xx error rate"
    
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND metric.labels.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 10
      
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields      = ["resource.labels.service_name"]
      }
    }
  }

  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email[0].name] : []

  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert policy for high memory usage
resource "google_monitoring_alert_policy" "memory_alert" {
  count        = var.enable_monitoring ? 1 : 0
  project      = var.project_id
  display_name = "RAG Medical Assistant - High Memory Usage"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "High memory utilization"
    
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/container/memory/utilizations\" AND resource.type=\"cloud_run_revision\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.8
      
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.labels.service_name"]
      }
    }
  }

  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email[0].name] : []

  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert policy for high CPU usage
resource "google_monitoring_alert_policy" "cpu_alert" {
  count        = var.enable_monitoring ? 1 : 0
  project      = var.project_id
  display_name = "RAG Medical Assistant - High CPU Usage"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "High CPU utilization"
    
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/container/cpu/utilizations\" AND resource.type=\"cloud_run_revision\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.8
      
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.labels.service_name"]
      }
    }
  }

  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email[0].name] : []

  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert policy for database connection issues
resource "google_monitoring_alert_policy" "database_alert" {
  count        = var.enable_monitoring ? 1 : 0
  project      = var.project_id
  display_name = "RAG Medical Assistant - Database Connection Issues"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "High database connection count"
    
    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\" AND resource.type=\"cloudsql_database\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 80
      
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.labels.database_id"]
      }
    }
  }

  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email[0].name] : []

  alert_strategy {
    auto_close = "1800s"
  }
}

# Custom dashboard for application monitoring
resource "google_monitoring_dashboard" "app_dashboard" {
  count        = var.enable_monitoring ? 1 : 0
  project      = var.project_id
  display_name = "RAG Medical Assistant - ${title(var.environment)} Dashboard"

  dashboard_json = jsonencode({
    displayName = "RAG Medical Assistant - ${title(var.environment)} Dashboard"
    mosaicLayout = {
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Request Count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["resource.labels.service_name"]
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Requests/sec"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          xPos   = 6
          widget = {
            title = "Response Latency"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"run.googleapis.com/request_latencies\" AND resource.type=\"cloud_run_revision\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_DELTA"
                      crossSeriesReducer = "REDUCE_PERCENTILE_95"
                      groupByFields      = ["resource.labels.service_name"]
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Latency (ms)"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          yPos   = 4
          widget = {
            title = "Memory Utilization"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"run.googleapis.com/container/memory/utilizations\" AND resource.type=\"cloud_run_revision\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_MEAN"
                      groupByFields      = ["resource.labels.service_name"]
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Utilization"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          xPos   = 6
          yPos   = 4
          widget = {
            title = "CPU Utilization"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"run.googleapis.com/container/cpu/utilizations\" AND resource.type=\"cloud_run_revision\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_MEAN"
                      groupByFields      = ["resource.labels.service_name"]
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Utilization"
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })
}

# Log-based metrics for custom monitoring
resource "google_logging_metric" "error_count" {
  count  = var.enable_monitoring ? 1 : 0
  name   = "rag_medical_error_count"
  filter = "resource.type=\"cloud_run_revision\" AND severity>=ERROR"
  
  metric_descriptor {
    metric_kind = "COUNTER"
    value_type  = "INT64"
    display_name = "RAG Medical Assistant Error Count"
  }
}

resource "google_logging_metric" "api_response_time" {
  count  = var.enable_monitoring ? 1 : 0
  name   = "rag_medical_api_response_time"
  filter = "resource.type=\"cloud_run_revision\" AND jsonPayload.response_time_ms>0"
  
  metric_descriptor {
    metric_kind = "GAUGE"
    value_type  = "DOUBLE"
    display_name = "RAG Medical Assistant API Response Time"
  }
  
  value_extractor = "EXTRACT(jsonPayload.response_time_ms)"
}

# Output monitoring information
output "monitoring_dashboard_url" {
  description = "URL to the monitoring dashboard"
  value       = var.enable_monitoring ? "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.app_dashboard[0].id}?project=${var.project_id}" : null
}

output "logs_bucket_name" {
  description = "Name of the logs storage bucket"
  value       = var.enable_monitoring ? google_storage_bucket.logs_bucket[0].name : null
}

output "uptime_check_id" {
  description = "ID of the uptime check"
  value       = var.enable_monitoring ? google_monitoring_uptime_check_config.app_uptime_check[0].uptime_check_id : null
}