#!/bin/bash

# RAG Medical Assistant - Local Development Setup Script
# This script sets up the local development environment for GCP deployment testing

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to install Google Cloud SDK
install_gcloud() {
    print_status "Installing Google Cloud SDK..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install --cask google-cloud-sdk
        else
            print_error "Homebrew not found. Please install Google Cloud SDK manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl https://sdk.cloud.google.com | bash
        exec -l $SHELL
    else
        print_error "Unsupported OS. Please install Google Cloud SDK manually."
        exit 1
    fi
    
    print_success "Google Cloud SDK installed"
}

# Function to install Terraform
install_terraform() {
    print_status "Installing Terraform..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew tap hashicorp/tap
            brew install hashicorp/tap/terraform
        else
            print_error "Homebrew not found. Please install Terraform manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
        sudo apt update && sudo apt install terraform
    else
        print_error "Unsupported OS. Please install Terraform manually."
        exit 1
    fi
    
    print_success "Terraform installed"
}

# Function to install Docker
install_docker() {
    print_status "Installing Docker..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install --cask docker
        else
            print_error "Homebrew not found. Please install Docker manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
    else
        print_error "Unsupported OS. Please install Docker manually."
        exit 1
    fi
    
    print_success "Docker installed"
}

# Function to setup development tools
setup_dev_tools() {
    print_status "Setting up development tools..."
    
    # Check and install Google Cloud SDK
    if ! command_exists gcloud; then
        install_gcloud
    else
        print_success "Google Cloud SDK already installed"
    fi
    
    # Check and install Terraform
    if ! command_exists terraform; then
        install_terraform
    else
        print_success "Terraform already installed"
    fi
    
    # Check and install Docker
    if ! command_exists docker; then
        install_docker
    else
        print_success "Docker already installed"
    fi
    
    print_success "Development tools setup completed"
}

# Function to authenticate with Google Cloud
authenticate_gcloud() {
    print_status "Authenticating with Google Cloud..."
    
    # Login to Google Cloud
    gcloud auth login
    
    # Set up application default credentials
    gcloud auth application-default login
    
    print_success "Google Cloud authentication completed"
}

# Function to create local environment file
create_local_env() {
    print_status "Creating local environment file..."
    
    cat > .env.local << 'EOF'
# Local Development Environment Variables
# Copy this file to .env and update with your actual values

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# Database Configuration (for local development)
DATABASE_URL=postgresql://postgres:password@localhost:5432/rag_medical_dev
REDIS_URL=redis://localhost:6379

# API Keys (get these from your providers)
OPENAI_API_KEY=your-openai-api-key-here

# Application Configuration
NODE_ENV=development
PORT=3000
API_PORT=3001

# Security
JWT_SECRET=your-jwt-secret-here
FLASK_SECRET_KEY=your-flask-secret-key-here

# File Upload
MAX_FILE_SIZE=10485760
UPLOAD_PATH=./uploads

# Logging
LOG_LEVEL=debug
EOF
    
    print_success "Local environment file created (.env.local)"
    print_warning "Please copy .env.local to .env and update with your actual values"
}

# Function to setup local database
setup_local_database() {
    print_status "Setting up local database..."
    
    if command_exists docker; then
        # Start PostgreSQL container
        docker run -d \
            --name rag-medical-postgres \
            -e POSTGRES_DB=rag_medical_dev \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD=password \
            -p 5432:5432 \
            postgres:13
        
        # Start Redis container
        docker run -d \
            --name rag-medical-redis \
            -p 6379:6379 \
            redis:6-alpine
        
        print_success "Local database containers started"
    else
        print_warning "Docker not available. Please set up PostgreSQL and Redis manually."
    fi
}

# Function to install project dependencies
install_dependencies() {
    print_status "Installing project dependencies..."
    
    # Install Node.js dependencies
    if [ -f "package.json" ]; then
        if command_exists pnpm; then
            pnpm install
        elif command_exists npm; then
            npm install
        else
            print_error "Neither pnpm nor npm found. Please install Node.js first."
            exit 1
        fi
        print_success "Node.js dependencies installed"
    fi
    
    # Install Python dependencies
    if [ -f "ml_backend/requirements.txt" ]; then
        if command_exists python3; then
            python3 -m pip install -r ml_backend/requirements.txt
        else
            print_error "Python 3 not found. Please install Python 3 first."
            exit 1
        fi
        print_success "Python dependencies installed"
    fi
}

# Function to run development servers
start_dev_servers() {
    print_status "Starting development servers..."
    
    # Create a simple start script
    cat > start-dev.sh << 'EOF'
#!/bin/bash

# Start all development servers
echo "Starting RAG Medical Assistant development servers..."

# Start the frontend
echo "Starting frontend server..."
npm run dev &
FRONTEND_PID=$!

# Start the API server
echo "Starting API server..."
npm run start:api &
API_PID=$!

# Start the ML backend
echo "Starting ML backend..."
cd ml_backend && python app.py &
ML_PID=$!
cd ..

echo "All servers started!"
echo "Frontend: http://localhost:3000"
echo "API: http://localhost:3001"
echo "ML Backend: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for interrupt
trap "kill $FRONTEND_PID $API_PID $ML_PID; exit" INT
wait
EOF
    
    chmod +x start-dev.sh
    print_success "Development start script created (start-dev.sh)"
}

# Function to create development documentation
create_dev_docs() {
    print_status "Creating development documentation..."
    
    cat > DEVELOPMENT.md << 'EOF'
# RAG Medical Assistant - Development Guide

## Prerequisites

- Node.js 18+ and npm/pnpm
- Python 3.8+
- Docker (for local database)
- Google Cloud SDK
- Terraform

## Local Development Setup

1. **Clone and setup the project:**
   ```bash
   git clone <repository-url>
   cd rag-medical-assistant
   ./scripts/setup-local-dev.sh
   ```

2. **Configure environment:**
   ```bash
   cp .env.local .env
   # Edit .env with your actual values
   ```

3. **Start local services:**
   ```bash
   # Start database containers
   docker start rag-medical-postgres rag-medical-redis
   
   # Start development servers
   ./start-dev.sh
   ```

## Project Structure

```
rag-medical-assistant/
├── src/                    # Frontend React application
├── api/                    # Node.js API server
├── ml_backend/            # Python ML backend
├── terraform/             # Infrastructure as Code
├── gcp/                   # GCP deployment configs
├── scripts/               # Deployment scripts
├── supabase/             # Database migrations
└── docs/                 # Documentation
```

## Development Workflow

1. **Frontend Development:**
   - Run `npm run dev` for hot reload
   - Access at http://localhost:3000
   - Uses Vite + React + TypeScript

2. **API Development:**
   - Run `npm run start:api` for API server
   - Access at http://localhost:3001
   - Uses Express.js + TypeScript

3. **ML Backend Development:**
   - Run `cd ml_backend && python app.py`
   - Access at http://localhost:5000
   - Uses Flask + Python

## Testing

```bash
# Run frontend tests
npm run test

# Run API tests
npm run test:api

# Run ML backend tests
cd ml_backend && python -m pytest
```

## Deployment

### Local Testing
```bash
# Build and test locally
docker build -t rag-medical-assistant .
docker run -p 8080:8080 rag-medical-assistant
```

### GCP Deployment
```bash
# Deploy to Google Cloud Platform
./scripts/deploy-gcp.sh
```

## Troubleshooting

### Common Issues

1. **Port conflicts:** Make sure ports 3000, 3001, 5000 are available
2. **Database connection:** Ensure PostgreSQL and Redis containers are running
3. **API keys:** Check that all required API keys are set in .env
4. **Dependencies:** Run `npm install` and `pip install -r requirements.txt`

### Logs

- Frontend: Check browser console
- API: Check terminal output or logs/api.log
- ML Backend: Check terminal output or logs/ml.log
- Database: `docker logs rag-medical-postgres`

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Submit a pull request

## Resources

- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Terraform Documentation](https://www.terraform.io/docs)
- [React Documentation](https://reactjs.org/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
EOF
    
    print_success "Development documentation created (DEVELOPMENT.md)"
}

# Function to display setup summary
display_summary() {
    print_success "Local development setup completed!"
    echo
    echo "=== Setup Summary ==="
    echo "✓ Development tools installed"
    echo "✓ Environment file created (.env.local)"
    echo "✓ Local database containers ready"
    echo "✓ Project dependencies installed"
    echo "✓ Development scripts created"
    echo "✓ Documentation created"
    echo
    echo "=== Next Steps ==="
    echo "1. Copy .env.local to .env and update with your values"
    echo "2. Start database containers: docker start rag-medical-postgres rag-medical-redis"
    echo "3. Start development servers: ./start-dev.sh"
    echo "4. Open http://localhost:3000 in your browser"
    echo
    echo "=== Useful Commands ==="
    echo "Start dev servers: ./start-dev.sh"
    echo "Deploy to GCP: ./scripts/deploy-gcp.sh"
    echo "View documentation: cat DEVELOPMENT.md"
    echo
}

# Main setup function
main() {
    echo "=== RAG Medical Assistant - Local Development Setup ==="
    echo
    
    setup_dev_tools
    authenticate_gcloud
    create_local_env
    setup_local_database
    install_dependencies
    start_dev_servers
    create_dev_docs
    display_summary
}

# Run the main function
main "$@"