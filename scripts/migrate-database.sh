#!/bin/bash

# RAG Medical Assistant - Database Migration Script
# This script handles database migrations for both local and GCP environments

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="local"
PROJECT_ID=""
REGION="us-central1"
INSTANCE_NAME=""
DATABASE_NAME="rag_medical"

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

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -e, --environment ENV    Environment (local|gcp) [default: local]"
    echo "  -p, --project PROJECT    GCP Project ID (required for GCP)"
    echo "  -r, --region REGION      GCP Region [default: us-central1]"
    echo "  -i, --instance INSTANCE  Cloud SQL instance name"
    echo "  -d, --database DATABASE  Database name [default: rag_medical]"
    echo "  -h, --help              Show this help message"
    echo
    echo "Examples:"
    echo "  $0 --environment local"
    echo "  $0 --environment gcp --project my-project --instance my-instance"
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -p|--project)
                PROJECT_ID="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -i|--instance)
                INSTANCE_NAME="$2"
                shift 2
                ;;
            -d|--database)
                DATABASE_NAME="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Function to validate arguments
validate_args() {
    if [[ "$ENVIRONMENT" != "local" && "$ENVIRONMENT" != "gcp" ]]; then
        print_error "Environment must be 'local' or 'gcp'"
        exit 1
    fi
    
    if [[ "$ENVIRONMENT" == "gcp" ]]; then
        if [[ -z "$PROJECT_ID" ]]; then
            print_error "Project ID is required for GCP environment"
            exit 1
        fi
        if [[ -z "$INSTANCE_NAME" ]]; then
            print_error "Instance name is required for GCP environment"
            exit 1
        fi
    fi
}

# Function to create migrations directory
create_migrations_dir() {
    if [[ ! -d "migrations" ]]; then
        print_status "Creating migrations directory..."
        mkdir -p migrations
        print_success "Migrations directory created"
    fi
}

# Function to create initial migration files
create_initial_migrations() {
    print_status "Creating initial migration files..."
    
    # Create users table migration
    cat > migrations/001_create_users_table.sql << 'EOF'
-- Create users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    phone VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EOF

    # Create medical profiles table migration
    cat > migrations/002_create_medical_profiles_table.sql << 'EOF'
-- Create medical profiles table
CREATE TABLE IF NOT EXISTS medical_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    height_cm INTEGER,
    weight_kg DECIMAL(5,2),
    blood_type VARCHAR(5),
    allergies TEXT[],
    chronic_conditions TEXT[],
    current_medications TEXT[],
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on user_id
CREATE INDEX IF NOT EXISTS idx_medical_profiles_user_id ON medical_profiles(user_id);

-- Create updated_at trigger
CREATE TRIGGER update_medical_profiles_updated_at BEFORE UPDATE ON medical_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EOF

    # Create chat sessions table migration
    cat > migrations/003_create_chat_sessions_table.sql << 'EOF'
-- Create chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on user_id
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);

-- Create updated_at trigger
CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EOF

    # Create chat messages table migration
    cat > migrations/004_create_chat_messages_table.sql << 'EOF'
-- Create chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
EOF

    # Create medicine cabinet table migration
    cat > migrations/005_create_medicine_cabinet_table.sql << 'EOF'
-- Create medicine cabinet table
CREATE TABLE IF NOT EXISTS medicine_cabinet (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    medicine_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    start_date DATE,
    end_date DATE,
    notes TEXT,
    image_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on user_id
CREATE INDEX IF NOT EXISTS idx_medicine_cabinet_user_id ON medicine_cabinet(user_id);

-- Create updated_at trigger
CREATE TRIGGER update_medicine_cabinet_updated_at BEFORE UPDATE ON medicine_cabinet
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EOF

    # Create file uploads table migration
    cat > migrations/006_create_file_uploads_table.sql << 'EOF'
-- Create file uploads table
CREATE TABLE IF NOT EXISTS file_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    upload_type VARCHAR(50) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_file_uploads_user_id ON file_uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_file_uploads_upload_type ON file_uploads(upload_type);
EOF

    print_success "Initial migration files created"
}

# Function to run migrations locally
run_local_migrations() {
    print_status "Running migrations on local database..."
    
    # Check if PostgreSQL is running
    if ! docker ps | grep -q rag-medical-postgres; then
        print_error "Local PostgreSQL container is not running"
        print_status "Starting PostgreSQL container..."
        docker start rag-medical-postgres || {
            print_error "Failed to start PostgreSQL container"
            exit 1
        }
        sleep 5
    fi
    
    # Run each migration file
    for migration_file in migrations/*.sql; do
        if [[ -f "$migration_file" ]]; then
            print_status "Running migration: $(basename "$migration_file")"
            docker exec -i rag-medical-postgres psql -U postgres -d "$DATABASE_NAME" < "$migration_file"
            print_success "Migration completed: $(basename "$migration_file")"
        fi
    done
    
    print_success "All local migrations completed"
}

# Function to run migrations on GCP
run_gcp_migrations() {
    print_status "Running migrations on GCP Cloud SQL..."
    
    # Check if gcloud is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with Google Cloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    # Set the project
    gcloud config set project "$PROJECT_ID"
    
    # Get Cloud SQL instance connection name
    CONNECTION_NAME=$(gcloud sql instances describe "$INSTANCE_NAME" --format="value(connectionName)")
    
    print_status "Connecting to Cloud SQL instance: $CONNECTION_NAME"
    
    # Run each migration file using Cloud SQL Proxy
    for migration_file in migrations/*.sql; do
        if [[ -f "$migration_file" ]]; then
            print_status "Running migration: $(basename "$migration_file")"
            
            # Use gcloud sql connect to run the migration
            gcloud sql connect "$INSTANCE_NAME" --user=postgres --database="$DATABASE_NAME" < "$migration_file"
            
            print_success "Migration completed: $(basename "$migration_file")"
        fi
    done
    
    print_success "All GCP migrations completed"
}

# Function to create migration tracking table
create_migration_tracking() {
    print_status "Creating migration tracking table..."
    
    cat > migrations/000_create_migrations_table.sql << 'EOF'
-- Create migrations tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
EOF
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        docker exec -i rag-medical-postgres psql -U postgres -d "$DATABASE_NAME" < migrations/000_create_migrations_table.sql
    else
        gcloud sql connect "$INSTANCE_NAME" --user=postgres --database="$DATABASE_NAME" < migrations/000_create_migrations_table.sql
    fi
    
    print_success "Migration tracking table created"
}

# Function to seed initial data
seed_initial_data() {
    print_status "Seeding initial data..."
    
    cat > migrations/999_seed_initial_data.sql << 'EOF'
-- Seed initial data for development/testing

-- Insert sample medical conditions (for autocomplete/suggestions)
CREATE TABLE IF NOT EXISTS medical_conditions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT
);

INSERT INTO medical_conditions (name, category, description) VALUES
('Hypertension', 'Cardiovascular', 'High blood pressure'),
('Diabetes Type 2', 'Endocrine', 'Type 2 diabetes mellitus'),
('Asthma', 'Respiratory', 'Chronic respiratory condition'),
('Arthritis', 'Musculoskeletal', 'Joint inflammation'),
('Depression', 'Mental Health', 'Major depressive disorder'),
('Anxiety', 'Mental Health', 'Generalized anxiety disorder')
ON CONFLICT DO NOTHING;

-- Insert sample medications (for autocomplete/suggestions)
CREATE TABLE IF NOT EXISTS medications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    category VARCHAR(100),
    common_dosages TEXT[]
);

INSERT INTO medications (name, generic_name, category, common_dosages) VALUES
('Lisinopril', 'Lisinopril', 'ACE Inhibitor', ARRAY['5mg', '10mg', '20mg']),
('Metformin', 'Metformin', 'Antidiabetic', ARRAY['500mg', '850mg', '1000mg']),
('Albuterol', 'Albuterol', 'Bronchodilator', ARRAY['90mcg', '180mcg']),
('Ibuprofen', 'Ibuprofen', 'NSAID', ARRAY['200mg', '400mg', '600mg']),
('Sertraline', 'Sertraline', 'SSRI', ARRAY['25mg', '50mg', '100mg'])
ON CONFLICT DO NOTHING;
EOF
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        docker exec -i rag-medical-postgres psql -U postgres -d "$DATABASE_NAME" < migrations/999_seed_initial_data.sql
    else
        gcloud sql connect "$INSTANCE_NAME" --user=postgres --database="$DATABASE_NAME" < migrations/999_seed_initial_data.sql
    fi
    
    print_success "Initial data seeded"
}

# Function to display migration status
show_migration_status() {
    print_status "Migration status:"
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        docker exec -i rag-medical-postgres psql -U postgres -d "$DATABASE_NAME" -c "
            SELECT 
                schemaname,
                tablename,
                tableowner
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        "
    else
        gcloud sql connect "$INSTANCE_NAME" --user=postgres --database="$DATABASE_NAME" --command="
            SELECT 
                schemaname,
                tablename,
                tableowner
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        "
    fi
}

# Main function
main() {
    echo "=== RAG Medical Assistant - Database Migration ==="
    echo
    
    parse_args "$@"
    validate_args
    
    print_status "Environment: $ENVIRONMENT"
    if [[ "$ENVIRONMENT" == "gcp" ]]; then
        print_status "Project: $PROJECT_ID"
        print_status "Instance: $INSTANCE_NAME"
    fi
    print_status "Database: $DATABASE_NAME"
    echo
    
    create_migrations_dir
    create_initial_migrations
    create_migration_tracking
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        run_local_migrations
    else
        run_gcp_migrations
    fi
    
    seed_initial_data
    show_migration_status
    
    print_success "Database migration completed successfully!"
}

# Run the main function
main "$@"