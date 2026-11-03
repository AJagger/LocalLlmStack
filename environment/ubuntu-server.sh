#!/usr/bin/env base
set -euo pipefail

# =============================================================================
# Initial Update
# =============================================================================
sudo apt update
sudo apt full-upgrade -y
sudo reboot

# =============================================================================
# Install Nvidia Driver
# =============================================================================
sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers list --gpgpu
sudo ubuntu-drivers install --gpgpu
sudo reboot

# Check driver is registered
nvidia-smi

# =============================================================================
# Install Docker
# =============================================================================
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

# =============================================================================
# Install NVIDIA Container Toolkit
# =============================================================================
sudo apt install -y curl gnupg

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# =============================================================================
# Install & Configure VM Capabilities (KVM, QEMU, Virtual Machine Manager)
# =============================================================================
# Ref: https://thecybersecguru.com/self-hosting/install-kvm-virt-manager-ubuntu-server-guide/

egrep -c '(vmx|svm)' /proc/cpuinfo
# If 0, enable Intel VT-x or AMD-V in BIOS

sudo apt update sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager
sudo adduser $USER libvirt sudo adduser your_username kvm
# Restart Shell

systemctl status libvirtd
# Should be running

virsh list --all
# Should have table output

sudo apt install -y openbox
sudo nano /etc/ssh/sshd_config
# Find X11Forwarding, set to Yes
sudo systemctl restart sshd
