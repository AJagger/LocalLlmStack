# Terminal Sandbox Server Setup

Step-by-step instructions for setting up an Ubuntu Server as a sandbox for OpenWebUI open-terminal sessions.

## 1. Update the system

Make sure all installed packages are up to date before installing anything new.

```bash
sudo apt update
sudo apt upgrade -y
```

## 2. Install Qemu-guest-agent

Install the QEMU guest agent so the hypervisor can manage the VM (e.g., graceful shutdown, time sync).

> **Prerequisite (Proxmox host):** The guest agent needs a virtio-serial channel exposed by the hypervisor. Before running the commands below, enable it on the Proxmox host — either via the GUI (VM → **Options** → **QEMU Guest Agent** → **Enabled**) or with `qm set <vmid> -agent 1` — then restart the VM. Without this, the service times out waiting for the `org.qemu.guest_agent.0` device.

```bash
sudo apt install -y qemu-guest-agent
```

Enable and start the service.

```bash
sudo systemctl enable --now qemu-guest-agent
```

Verify it is running.

```bash
systemctl status qemu-guest-agent
```

## 3. Install Docker

Add Docker's official GPG key and apt repository.

```bash
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Add the Docker repository to apt sources.

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

Install the Docker packages.

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Enable and start the Docker service.

```bash
sudo systemctl enable --now docker
```

Verify the installation.

```bash
sudo docker run hello-world
```

## 4. Clone the repository

Create the target directory and clone the repository into it. Replace `<repoName>` and `<repoUrl>` with the actual repository name and URL.

```bash
sudo mkdir -p /opt/docker
sudo git clone <repoUrl> /opt/docker/<repoName>
```