# Build and start all services (including UI)

docker-compose up --build

# Start only the UI service

docker-compose up ui

# View logs

docker-compose logs -f ui

# Stop all services

docker-compose down
