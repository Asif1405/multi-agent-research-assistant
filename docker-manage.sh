#!/bin/bash

# AI Research Assistant Docker Management Script
# This script helps you manage the Docker deployment of the AI Research Assistant

set -e

# Colors for output
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

# Function to check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env file not found!"
        if [ -f .env.example ]; then
            print_status "Copying .env.example to .env..."
            cp .env.example .env
            print_warning "Please edit .env file with your API keys before continuing."
            return 1
        else
            print_error ".env.example file not found. Please create .env file manually."
            return 1
        fi
    fi
    return 0
}

# Function to check if required API keys are set
check_api_keys() {
    if ! grep -q "OPENAI_API_KEY=your_openai_api_key_here" .env 2>/dev/null; then
        if ! grep -q "OPENAI_API_KEY=" .env 2>/dev/null || grep -q "OPENAI_API_KEY=$" .env 2>/dev/null; then
            print_error "OPENAI_API_KEY is not set in .env file"
            return 1
        fi
    else
        print_error "Please replace 'your_openai_api_key_here' with your actual OpenAI API key in .env"
        return 1
    fi
    
    if ! grep -q "SERPER_API_KEY=your_serper_api_key_here" .env 2>/dev/null; then
        if ! grep -q "SERPER_API_KEY=" .env 2>/dev/null || grep -q "SERPER_API_KEY=$" .env 2>/dev/null; then
            print_error "SERPER_API_KEY is not set in .env file"
            return 1
        fi
    else
        print_error "Please replace 'your_serper_api_key_here' with your actual Serper API key in .env"
        return 1
    fi
    
    return 0
}

# Function to start the application
start() {
    print_status "Starting AI Research Assistant..."
    
    if ! check_env_file; then
        return 1
    fi
    
    if ! check_api_keys; then
        return 1
    fi
    
    docker-compose up -d
    
    print_success "Application started successfully!"
    print_status "Access the app at: http://localhost:7860"
    print_status "View logs with: $0 logs"
}

# Function to stop the application
stop() {
    print_status "Stopping AI Research Assistant..."
    docker-compose down
    print_success "Application stopped successfully!"
}

# Function to restart the application
restart() {
    print_status "Restarting AI Research Assistant..."
    stop
    start
}

# Function to show logs
logs() {
    docker-compose logs -f
}

# Function to show status
status() {
    print_status "Application Status:"
    docker-compose ps
}

# Function to build the application
build() {
    print_status "Building AI Research Assistant..."
    docker-compose build
    print_success "Build completed successfully!"
}

# Function to update the application
update() {
    print_status "Updating AI Research Assistant..."
    print_status "Pulling latest changes..."
    git pull || print_warning "Git pull failed. Continuing with build..."
    
    print_status "Rebuilding container..."
    docker-compose build
    
    print_status "Restarting application..."
    docker-compose up -d
    
    print_success "Update completed successfully!"
}

# Function to clean up Docker resources
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v
    docker system prune -f
    print_success "Cleanup completed successfully!"
}

# Function to show help
show_help() {
    echo "AI Research Assistant Docker Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start the application"
    echo "  stop      Stop the application"
    echo "  restart   Restart the application"
    echo "  logs      Show application logs"
    echo "  status    Show application status"
    echo "  build     Build the Docker image"
    echo "  update    Update and restart the application"
    echo "  cleanup   Clean up Docker resources"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start    # Start the application"
    echo "  $0 logs     # View real-time logs"
    echo "  $0 stop     # Stop the application"
}

# Main script logic
case "${1:-}" in
    "start")
        start
        ;;
    "stop")
        stop
        ;;
    "restart")
        restart
        ;;
    "logs")
        logs
        ;;
    "status")
        status
        ;;
    "build")
        build
        ;;
    "update")
        update
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    "")
        print_error "No command specified."
        echo ""
        show_help
        exit 1
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
