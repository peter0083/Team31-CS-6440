#!/bin/bash
# -------------------------------------------------------------
# Start script for ms1 microservice
# Usage:
#   ./start_ms1.sh build   -> builds the ms1 Docker image
#   ./start_ms1.sh run     -> runs ms1 container on port 8000
#   ./start_ms1.sh stop    -> stops and removes running ms1
# -------------------------------------------------------------

SERVICE_NAME=ms1
IMAGE_NAME=${SERVICE_NAME}:local
CONTAINER_NAME=${SERVICE_NAME}_container
CONTEXT_PATH=./Dockerfile.ms1

case "$1" in
  build)
    echo "🔨 Building Docker image for ${SERVICE_NAME}..."
    docker build -t ${IMAGE_NAME} ${CONTEXT_PATH}
    ;;
  run)
    echo "🚀 Running ${SERVICE_NAME} container..."
    docker run -d --rm --name ${CONTAINER_NAME} \
  -p 8001:8001 \
  -v "C:\Users\pravi\Documents\GATECH\IHI\GP\Team31-CS-6440:/workspace" \
  ${IMAGE_NAME}
    ;;
  stop)
    echo "🛑 Stopping ${SERVICE_NAME} container..."
    docker stop ${CONTAINER_NAME} || true
    ;;
  *)
    echo "Usage: $0 {build|run|stop}"
    exit 1
    ;;
esac