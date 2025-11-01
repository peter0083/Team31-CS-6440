#!/bin/bash

# MS2 Docker Quick Start Script
# This script helps you quickly start MS2 microservice with Docker

set -e

echo "🚀 MS2 Microservice - Docker Quick Start"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating one..."
    echo "OPENAI_API_KEY=your-api-key-here" > .env
    echo "✅ Created .env file. Please update it with your OpenAI API key."
    echo "   Edit .env and replace 'your-api-key-here' with your actual key."
    read -p "Press Enter after updating .env to continue..."
fi

# Load environment variables
source .env

# Check if OPENAI_API_KEY is set
if [ "$OPENAI_API_KEY" == "your-api-key-here" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Please set your OPENAI_API_KEY in .env file"
    exit 1
fi

echo "✅ Environment variables loaded"

# Create data directory if it doesn't exist
mkdir -p data/ms2
echo "✅ Created data directory"

# Build and start services
echo ""
echo "📦 Building MS2 Docker image..."
docker-compose build ms2

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "🔍 Checking service health..."

# Check if MS2 is running
if docker-compose ps | grep -q "ms2_service.*Up"; then
    echo "✅ MS2 service is running"
else
    echo "❌ MS2 service failed to start"
    docker-compose logs ms2
    exit 1
fi

# Check if PostgreSQL is running
if docker-compose ps | grep -q "ms2_postgres.*Up"; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL failed to start"
    docker-compose logs postgres
    exit 1
fi

# Test MS2 health endpoint
echo ""
echo "🔍 Testing MS2 health endpoint..."
if curl -f http://localhost:8002/api/ms2/health &> /dev/null; then
    echo "✅ MS2 health check passed"
else
    echo "⚠️  MS2 health check failed (this might be temporary)"
fi

echo ""
echo "🎉 MS2 microservice is up and running!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🌐 Available Endpoints:"
echo "   - MS2 API: http://localhost:8002/api/ms2/"
echo "   - Health Check: http://localhost:8002/api/ms2/health"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:        docker-compose logs -f ms2"
echo "   Stop services:    docker-compose down"
echo "   Restart:          docker-compose restart ms2"
echo "   View status:      docker-compose ps"
echo ""
echo "📖 For more information, see DOCKER_README.md"
