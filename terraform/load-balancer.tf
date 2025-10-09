# Load Balancer configuration for RAG Medical Assistant
# This creates an HTTPS load balancer with SSL certificate and Cloud CDN

# Global IP address for the load balancer
resource "google_compute_global_address" "lb_ip" {
  count   = var.domain_name != "" ? 1 : 0
  name    = "rag-medical-lb-ip-${var.environment}"
  project = var.project_id
}

# Managed SSL certificate for HTTPS
resource "google_compute_managed_ssl_certificate" "ssl_cert" {
  count   = var.domain_name != "" ? 1 : 0
  name    = "rag-medical-ssl-cert-${var.environment}"
  project = var.project_id

  managed {
    domains = [var.domain_name]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# SSL policy for enhanced security
resource "google_compute_ssl_policy" "ssl_policy" {
  count           = var.domain_name != "" ? 1 : 0
  name            = "rag-medical-ssl-policy-${var.environment}"
  project         = var.project_id
  profile         = var.ssl_policy
  min_tls_version = "TLS_1_2"
}

# Backend service for Cloud Run
resource "google_compute_backend_service" "cloud_run_backend" {
  count                           = var.domain_name != "" ? 1 : 0
  name                           = "rag-medical-backend-${var.environment}"
  project                        = var.project_id
  protocol                       = "HTTP"
  port_name                      = "http"
  timeout_sec                    = 30
  connection_draining_timeout_sec = 10
  load_balancing_scheme          = "EXTERNAL"

  # Enable Cloud CDN for static content
  enable_cdn = var.enable_cdn

  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    default_ttl                 = 3600
    max_ttl                     = 86400
    client_ttl                  = 3600
    negative_caching            = true
    negative_caching_policy {
      code = 404
      ttl  = 120
    }
    negative_caching_policy {
      code = 410
      ttl  = 120
    }
    serve_while_stale = 86400
    
    cache_key_policy {
      include_host         = true
      include_protocol     = true
      include_query_string = false
      query_string_whitelist = ["utm_source", "utm_medium", "utm_campaign"]
    }
  }

  # Health check
  health_checks = [google_compute_health_check.cloud_run_health_check[0].id]

  # Security policy
  security_policy = var.enable_security_policy ? google_compute_security_policy.security_policy[0].id : null

  # Backend configuration will be added after Cloud Run deployment
  backend {
    group = "projects/${var.project_id}/global/networkEndpointGroups/rag-medical-neg-${var.environment}"
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }

  depends_on = [google_compute_health_check.cloud_run_health_check]
}

# Health check for Cloud Run service
resource "google_compute_health_check" "cloud_run_health_check" {
  count               = var.domain_name != "" ? 1 : 0
  name                = "rag-medical-health-check-${var.environment}"
  project             = var.project_id
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3

  http_health_check {
    port         = 8080
    request_path = "/health"
    host         = var.domain_name
  }

  log_config {
    enable = true
  }
}

# URL map for routing
resource "google_compute_url_map" "url_map" {
  count           = var.domain_name != "" ? 1 : 0
  name            = "rag-medical-url-map-${var.environment}"
  project         = var.project_id
  default_service = google_compute_backend_service.cloud_run_backend[0].id

  # Route for API endpoints
  path_matcher {
    name            = "api-matcher"
    default_service = google_compute_backend_service.cloud_run_backend[0].id

    path_rule {
      paths   = ["/api/*", "/health", "/metrics"]
      service = google_compute_backend_service.cloud_run_backend[0].id
    }
  }

  # Route for static assets with longer cache
  path_matcher {
    name            = "static-matcher"
    default_service = google_compute_backend_service.cloud_run_backend[0].id

    path_rule {
      paths   = ["/static/*", "/assets/*", "*.js", "*.css", "*.png", "*.jpg", "*.svg"]
      service = google_compute_backend_service.cloud_run_backend[0].id
    }
  }

  host_rule {
    hosts        = [var.domain_name]
    path_matcher = "api-matcher"
  }
}

# HTTPS proxy
resource "google_compute_target_https_proxy" "https_proxy" {
  count            = var.domain_name != "" ? 1 : 0
  name             = "rag-medical-https-proxy-${var.environment}"
  project          = var.project_id
  url_map          = google_compute_url_map.url_map[0].id
  ssl_certificates = [google_compute_managed_ssl_certificate.ssl_cert[0].id]
  ssl_policy       = google_compute_ssl_policy.ssl_policy[0].id
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "http_redirect" {
  count   = var.domain_name != "" ? 1 : 0
  name    = "rag-medical-http-redirect-${var.environment}"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http_proxy" {
  count   = var.domain_name != "" ? 1 : 0
  name    = "rag-medical-http-proxy-${var.environment}"
  project = var.project_id
  url_map = google_compute_url_map.http_redirect[0].id
}

# Global forwarding rules
resource "google_compute_global_forwarding_rule" "https_forwarding_rule" {
  count                 = var.domain_name != "" ? 1 : 0
  name                  = "rag-medical-https-forwarding-rule-${var.environment}"
  project               = var.project_id
  target                = google_compute_target_https_proxy.https_proxy[0].id
  port_range            = "443"
  ip_address            = google_compute_global_address.lb_ip[0].address
  load_balancing_scheme = "EXTERNAL"
}

resource "google_compute_global_forwarding_rule" "http_forwarding_rule" {
  count                 = var.domain_name != "" ? 1 : 0
  name                  = "rag-medical-http-forwarding-rule-${var.environment}"
  project               = var.project_id
  target                = google_compute_target_http_proxy.http_proxy[0].id
  port_range            = "80"
  ip_address            = google_compute_global_address.lb_ip[0].address
  load_balancing_scheme = "EXTERNAL"
}

# Network Endpoint Group for Cloud Run (to be created after deployment)
# This is a placeholder - the actual NEG will be created automatically by Cloud Run
# when the service is deployed with the correct annotations

# Firewall rules for load balancer
resource "google_compute_firewall" "allow_lb_health_check" {
  count   = var.domain_name != "" ? 1 : 0
  name    = "allow-lb-health-check-${var.environment}"
  project = var.project_id
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  # Google Cloud Load Balancer health check IP ranges
  source_ranges = [
    "130.211.0.0/22",
    "35.191.0.0/16"
  ]

  target_tags = ["rag-medical-app"]
}

# Firewall rule for HTTPS traffic
resource "google_compute_firewall" "allow_https" {
  count   = var.domain_name != "" ? 1 : 0
  name    = "allow-https-${var.environment}"
  project = var.project_id
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["443", "80"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["rag-medical-lb"]
}

# DNS record (if using Cloud DNS)
# Uncomment and configure if you're managing DNS with Google Cloud DNS
/*
resource "google_dns_record_set" "a_record" {
  count        = var.domain_name != "" ? 1 : 0
  name         = "${var.domain_name}."
  managed_zone = "your-dns-zone-name"  # Replace with your DNS zone name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.lb_ip[0].address]
}
*/

# Output load balancer information
output "load_balancer_ip_address" {
  description = "IP address of the load balancer"
  value       = var.domain_name != "" ? google_compute_global_address.lb_ip[0].address : null
}

output "ssl_certificate_status" {
  description = "Status of the SSL certificate"
  value       = var.domain_name != "" ? google_compute_managed_ssl_certificate.ssl_cert[0].managed[0].status : null
}

output "cdn_enabled" {
  description = "Whether Cloud CDN is enabled"
  value       = var.enable_cdn
}