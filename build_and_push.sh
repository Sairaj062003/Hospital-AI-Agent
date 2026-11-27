#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Run from the project root, wherever the script is called from
cd "$(dirname "$0")"

echo "Loading ACR credentials from .env..."
if [ -f .env ]; then
  # Load only the ACR_ variables and strip Windows line endings
  set -a
  source <(grep '^ACR_' .env | tr -d '\r')
  set +a
else
  echo "Error: .env file not found!"
  exit 1
fi

# Ensure required ACR variables are set
if [ -z "$ACR_LOGIN_SERVER" ] || [ -z "$ACR_USERNAME" ] || [ -z "$ACR_PASSWORD" ]; then
  echo "Error: Missing ACR credentials in .env file (ACR_LOGIN_SERVER, ACR_USERNAME, ACR_PASSWORD)."
  exit 1
fi

IMAGE_NAME="hospital-ai-agent"
TAG=$(date +%Y%m%d%H%M%S) # Creates a timestamp tag like 20261002104500
LATEST_IMAGE="$ACR_LOGIN_SERVER/$IMAGE_NAME:latest"
TAGGED_IMAGE="$ACR_LOGIN_SERVER/$IMAGE_NAME:$TAG"

echo "Logging into Azure Container Registry ($ACR_LOGIN_SERVER)..."
echo "$ACR_PASSWORD" | docker login "$ACR_LOGIN_SERVER" --username "$ACR_USERNAME" --password-stdin

echo "Building Docker image..."
docker build -t "$LATEST_IMAGE" -t "$TAGGED_IMAGE" .

echo "Pushing images to ACR..."
docker push "$LATEST_IMAGE"
docker push "$TAGGED_IMAGE"

echo "✅ Successfully built and pushed:"
echo "   - $LATEST_IMAGE"
echo "   - $TAGGED_IMAGE"
