#!/usr/bin/env bash
# ==============================================================================
# TrustShare EC2 Setup & Bootstrap Script (Ubuntu 22.04 LTS)
# ==============================================================================
set -euo pipefail

REPO_URL="https://github.com/mythribanda/TrustShare.git"
INSTALL_DIR="${HOME}/TrustShare"

echo "=== [1/6] Updating system packages ==="
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release git

echo "=== [2/6] Configuring 2GB swap space (memory safeguard for t3.small) ==="
if [ ! -f /swapfile ]; then
  sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo "Swap enabled successfully."
else
  echo "Swapfile already exists."
fi

echo "=== [3/6] Installing Docker Engine & Docker Compose Plugin ==="
if ! command -v docker &> /dev/null; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  sudo systemctl enable docker
  sudo systemctl start docker
  sudo usermod -aG docker "${USER}"
  echo "Docker installed successfully."
else
  echo "Docker is already installed."
fi

echo "=== [4/6] Setting up repository ==="
if [ ! -d "${INSTALL_DIR}" ]; then
  echo "Cloning repository into ${INSTALL_DIR}..."
  git clone "${REPO_URL}" "${INSTALL_DIR}"
else
  echo "Repository exists at ${INSTALL_DIR}. Pulling latest changes..."
  cd "${INSTALL_DIR}"
  git fetch origin main
  git reset --hard origin/main
fi

cd "${INSTALL_DIR}"

echo "=== [5/6] Checking production environment file ==="
if [ ! -f ".env" ]; then
  if [ -f ".env.prod" ]; then
    cp .env.prod .env
    echo "Copied existing .env.prod to .env"
  else
    cp .env.prod.example .env
    echo "Created .env from .env.prod.example."
    echo "CRITICAL: You must edit .env and configure DOMAIN, S3_BUCKET, S3 credentials, and secrets!"
    echo "Run: nano ${INSTALL_DIR}/.env"
  fi
else
  echo ".env file already exists."
fi

echo "=== [6/6] Building and starting production stack ==="
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "=============================================================================="
echo "TrustShare production deployment completed!"
echo "Check container status: sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"
echo "View Caddy logs:         sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f caddy"
echo "Create your first admin: sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -m app.scripts.create_admin --email admin@yourdomain.com --name \"Admin User\""
echo "=============================================================================="
