#!/bin/bash

# RAG Medical Assistant - Google Cloud Platform Deployment Script
# This script automates the complete deployment process to GCP

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=""
REGION="us-central1"
ENVIRONMENT="prod"
DOMAIN_NAME=""
NOTIFICATION_EMAIL=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate prerequisites
validate_prerequisites() {
    print_status "Validating prerequisites..."
    
    # Check if gcloud is installed
    if ! command_exists gcloud; then
        print_error "Google Cloud SDK is not installed. Please install it first."
        exit 1
    fi
    
    # Check if terraform is installed
    if ! command_exists terraform; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if docker is installed
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if user is authenticated with gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with Google Cloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    print_success "All prerequisites validated"
}

# Function to get user configuration
get_configuration() {
    print_status "Getting deployment configuration..."
    
    # Get project ID if not set
    if [ -z "$PROJECT_ID" ]; then
        echo -n "Enter your Google Cloud Project ID: "
        read PROJECT_ID
    fi
    
    # Get region
    echo -n "Enter deployment region (default: us-central1): "
    read input_region
    if [ ! -z "$input_region" ]; then
        REGION="$input_region"
    fi
    
    # Get environment
    echo -n "Enter environment (dev/staging/prod, default: prod): "
    read input_env
    if [ ! -z "$input_env" ]; then
        ENVIRONMENT="$input_env"
    fi
    
    # Get domain name (optional)
    echo -n "Enter custom domain name (optional, press Enter to skip): "
    read DOMAIN_NAME
    
    # Get notification email (optional)
    echo -n "Enter notification email for alerts (optional, press Enter to skip): "
    read NOTIFICATION_EMAIL
    
    print_success "Configuration collected"
}

# Function to set up GCP project
setup_gcp_project() {
    print_status "Setting up GCP project..."
    
    # Set the project
    gcloud config set project "$PROJECT_ID"
    
    # Enable required APIs
    print_status "Enabling required APIs..."
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
        cloudresourcemanager.googleapis.com \
        container.googleapis.com \
        containerregistry.googleapis.com
    
    print_success "GCP project setup completed"
}

# Function to create terraform.tfvars file
create_terraform_vars() {
    print_status "Creating Terraform variables file..."
    
    cat > terraform/terraform.tfvars << EOF
project_id = "$PROJECT_ID"
region = "$REGION"
environment = "$ENVIRONMENT"
domain_name = "$DOMAIN_NAME"
notification_email = "$NOTIFICATION_EMAIL"

# Resource configuration
database_tier = "db-f1-micro"
redis_memory_size_gb = 1
enable_backup = true
backup_retention_days = 7
enable_monitoring = true
enable_security_policy = true
rate_limit_requests_per_minute = 100
storage_bucket_location = "US"
vpc_cidr_range = "10.0.0.0/24"
connector_cidr_range = "10.8.0.0/28"
deletion_protection = true
ssl_policy = "MODERN"
cloud_run_cpu = "2"
cloud_run_memory = "4Gi"
cloud_run_max_instances = 100
cloud_run_min_instances = 1
enable_cdn = true

labels = {
  project     = "rag-medical-assistant"
  environment = "$ENVIRONMENT"
  managed-by  = "terraform"
}
EOF
    
    print_success "Terraform variables file created"
}

# Function to deploy infrastructure with Terraform
deploy_infrastructure() {
    print_status "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init
    
    # Plan the deployment
    print_status "Planning Terraform deployment..."
    terraform plan -var-file=terraform.tfvars
    
    # Ask for confirmation
    echo -n "Do you want to proceed with the infrastructure deployment? (y/N): "
    read confirm
    if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
        print_warning "Infrastructure deployment cancelled"
        cd ..
        return 1
    fi
    
    # Apply the configuration
    print_status "Applying Terraform configuration..."
    terraform apply -var-file=terraform.tfvars -auto-approve
    
    # Get outputs
    print_status "Getting Terraform outputs..."
    terraform output > ../terraform-outputs.txt
    
    cd ..
    print_success "Infrastructure deployment completed"
}

# Function to set up secrets
setup_secrets() {
    print_status "Setting up secrets in Secret Manager..."
    
    # Generate random secrets if they don't exist
    JWT_SECRET=$(openssl rand -base64 32)
    FLASK_SECRET_KEY=$(openssl rand -base64 32)
    
    # Create secrets (will fail if they already exist, which is fine)
    gcloud secrets create jwt-secret --data-file=<(echo -n "$JWT_SECRET") --project="$PROJECT_ID" 2>/dev/null || true
    gcloud secrets create flask-secret-key --data-file=<(echo -n "$FLASK_SECRET_KEY") --project="$PROJECT_ID" 2>/dev/null || true
    
    # Placeholder for OpenAI API key (user needs to set this manually)
    echo -n "your-openai-api-key-here" | gcloud secrets create openai-api-key --data-file=- --project="$PROJECT_ID" 2>/dev/null || true
    
    print_warning "Please update the OpenAI API key secret manually:"
    print_warning "gcloud secrets versions add openai-api-key --data-file=<(echo -n 'your-actual-api-key')"
    
    print_success "Secrets setup completed"
}

# Function to build and push Docker image
build_and_push_image() {
    print_status "Building and pushing Docker image..."
    
    # Build the image using Cloud Build
    gcloud builds submit \
        --tag "gcr.io/$PROJECT_ID/rag-medical-assistant:latest" \
        --project="$PROJECT_ID" \
        .
    
    print_success "Docker image built and pushed"
}

# Function to deploy Cloud Run service
deploy_cloud_run() {
    print_status "Deploying Cloud Run service..."
    
    # Update the Cloud Run configuration with actual project ID
    sed -i.bak "s/PROJECT_ID/$PROJECT_ID/g" gcp/cloud-run.yaml
    
    # Deploy the service
    gcloud run services replace gcp/cloud-run.yaml \
        --region="$REGION" \
        --project="$PROJECT_ID"
    
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe rag-medical-assistant \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.url)")
    
    print_success "Cloud Run service deployed at: $SERVICE_URL"
    echo "$SERVICE_URL" > service-url.txt
}

# Function to run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    # Get database connection details from Terraform outputs
    DB_CONNECTION_NAME=$(terraform -chdir=terraform output -raw database_connection_name)
    
    # Run migrations using Cloud Run Jobs (if migration scripts exist)
    if [ -d "migrations" ]; then
        print_status "Database migration scripts found, running migrations..."
        # This would typically involve running a Cloud Run job or connecting via Cloud SQL Proxy
        print_warning "Manual database migration may be required. Check the migrations/ directory."
    else
        print_warning "No migration scripts found. Database will be initialized on first run."
    fi
    
    print_success "Database migration check completed"
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    if [ -f "service-url.txt" ]; then
        SERVICE_URL=$(cat service-url.txt)
        
        # Wait for service to be ready
        print_status "Waiting for service to be ready..."
        sleep 30
        
        # Check health endpoint
        if curl -f -s "$SERVICE_URL/health" > /dev/null; then
            print_success "Health check passed"
        else
            print_warning "Health check failed. Service may still be starting up."
        fi
        
        # Check API endpoint
        if curl -f -s "$SERVICE_URL/api/health" > /dev/null; then
            print_success "API health check passed"
        else
            print_warning "API health check failed. Check logs for issues."
        fi
    else
        print_warning "Service URL not found. Skipping health checks."
    fi
}

# Function to display deployment summary
display_summary() {
    print_success "Deployment completed successfully!"
    echo
    echo "=== Deployment Summary ==="
    echo "Project ID: $PROJECT_ID"
    echo "Region: $REGION"
    echo "Environment: $ENVIRONMENT"
    
    if [ -f "service-url.txt" ]; then
        SERVICE_URL=$(cat service-url.txt)
        echo "Service URL: $SERVICE_URL"
    fi
    
    if [ ! -z "$DOMAIN_NAME" ]; then
        echo "Custom Domain: $DOMAIN_NAME"
        echo "Note: Make sure to point your domain to the load balancer IP"
    fi
    
    echo
    echo "=== Next Steps ==="
    echo "1. Update the OpenAI API key in Secret Manager"
    echo "2. Configure your domain DNS (if using custom domain)"
    echo "3. Monitor the application using Cloud Monitoring"
    echo "4. Check logs in Cloud Logging"
    echo
    echo "=== Useful Commands ==="
    echo "View logs: gcloud logs tail --follow --project=$PROJECT_ID"
    echo "Update service: gcloud run services replace gcp/cloud-run.yaml --region=$REGION"
    echo "View monitoring: https://console.cloud.google.com/monitoring?project=$PROJECT_ID"
    echo
}

# Function to handle cleanup on error
cleanup_on_error() {
    print_error "Deployment failed. Check the logs above for details."
    echo
    echo "To clean up resources, you can run:"
    echo "cd terraform && terraform destroy -var-file=terraform.tfvars"
    exit 1
}

# Main deployment function
main() {
    echo "=== RAG Medical Assistant - GCP Deployment ==="
    echo
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Run deployment steps
    validate_prerequisites
    get_configuration
    setup_gcp_project
    create_terraform_vars
    deploy_infrastructure
    setup_secrets
    build_and_push_image
    deploy_cloud_run
    run_migrations
    run_health_checks
    display_summary
}

# Run the main function
main "$@"