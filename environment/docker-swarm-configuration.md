# Docker Swarm Configuration

Instructions for configuring a Docker Swarm across the agent machines so that containerized workloads can be scheduled across multiple hosts.

## Prerequisites

- Docker installed and running on every machine (see `terminal-sandbox.md` / `ubuntu-server.sh`).

## 1. Verify the static IP

Find each machine's LAN IP with:

```bash
ip -4 addr show
```

If a machine is not at its correctly configured static IP, refresh the network interface:

```bash
sudo ip link set <interface> down
sudo ip link set <interface> up
```

## 2. Initialize the swarm on the manager

Run this on the machine that will act as the manager. Replace `<manager-ip>` with the manager's LAN IP (e.g., `10.0.0.10`).

```bash
sudo docker swarm init --advertise-addr <manager-ip>
```

The output includes a join command for workers:

```
To add a worker to this swarm, run the following command:

	sudo docker swarm join \
	--token SWMTKN-1-... \
	10.0.0.10:2377
```

Copy the token — you will need it on each worker. You can also regenerate it later:

```bash
sudo docker swarm join-token -p worker
```

## 3. Firewall rules (if UFW is enabled)

Swarm nodes must be able to reach each other on the following ports:

| Port   | Protocol | Purpose                          |
| ------ | -------- | -------------------------------- |
| 2377   | TCP      | Control plane (manager API)      |
| 7946   | TCP      | Node-to-node communication       |
| 7946   | UDP      | Overlay network traffic          |

If UFW is enabled on the VMs, allow these ports on **every** node (manager and workers) before joining:

```bash
sudo ufw allow 2377/tcp
sudo ufw allow 7946/tcp
sudo ufw allow 7946/udp
```

## 4. Join the swarm from each worker

Run this on each worker machine. Replace `<token>` with the token from step 1 and `<manager-ip>` with the manager's LAN IP.

```bash
sudo docker swarm join \
  --token <token> \
  <manager-ip>:2377
```

A successful join prints `This node joined the swarm as a worker`.

## 5. Verify the swarm

On the manager:

```bash
sudo docker node ls
```

You should see the manager (with `manager` in the ROLE column) and each worker with a `Ready` status.

## 6. Deploying services

Services are the unit of deployment in a swarm; the manager schedules their replicas across the workers.

```bash
# Create a replicated service (2 replicas, scheduled across workers)
sudo docker service create --name my-service --replicas 2 <image>

# Inspect
sudo docker service ls
sudo docker service ps my-service
```

## 7. Managing nodes

```bash
# Drain a node (no new tasks scheduled; existing ones finish)
sudo docker node update --availability drain <node-name>

# Restore a drained node
sudo docker node update --availability active <node-name>

# Remove a node from the swarm
sudo docker node rm <node-name>
```

## 8. Leaving / tearing down the swarm

On a worker:

```bash
sudo docker swarm leave
```

On the last manager (removes the entire swarm):

```bash
sudo docker swarm leave --force
```

> **High availability:** A single manager is a single point of failure. To add a standby manager, generate a manager token on an existing manager (`sudo docker swarm join-token -p manager`) and join the new node with it using the same `docker swarm join` command.
