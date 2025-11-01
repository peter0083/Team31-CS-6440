#!/bin/bash

# MS2 Test Runner Script
# Runs unit tests in Docker container with proper environment variables

set -e

echo "🧪 MS2 Unit Tests - Docker Runner"
echo "=================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

print_success "Docker is running"

# Parse arguments
TEST_PATH="tests/ms2/test_ms2.py"
VERBOSE="-v"
COVERAGE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE="--cov=src.ms2 --cov-report=term-missing --cov-report=html"
            shift
            ;;
        --specific)
            TEST_PATH="$2"
            shift 2
            ;;
        --quiet)
            VERBOSE=""
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Option 1: Run in existing MS2 container (if running)
if docker ps | grep -q "ms2_service"; then
    print_info "Running tests in existing MS2 container..."
    docker-compose exec ms2 pytest $TEST_PATH $VERBOSE $COVERAGE
    exit $?
fi

# Option 2: Use dedicated test container
print_info "Building test container..."
docker-compose build ms2-test

print_info "Running tests in dedicated test container..."
docker-compose run --rm ms2-test pytest $TEST_PATH $VERBOSE $COVERAGE

TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    print_success "All tests passed!"
else
    print_error "Some tests failed"
fi

exit $TEST_RESULT
