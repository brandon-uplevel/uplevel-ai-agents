# Redis MCP Persistent Memory Setup Guide

This guide provides comprehensive instructions for setting up and maintaining the Redis MCP (Model Context Protocol) persistent memory system for the Uplevel AI Agent System.

## 🎯 Overview

The Redis MCP persistent memory system ensures that agent context, project state, and workflow data survive system restarts, container restarts, and computer reboots. This is critical for maintaining continuity in multi-agent workflows and project development.

### Key Features
- **Persistent Storage**: Data survives all restart scenarios
- **Identifiable Naming**: Clear labeling for easy identification and maintenance  
- **Project Context**: Organized storage by Project ID for multi-project support
- **High Availability**: Auto-restart on failure with `--restart unless-stopped`
- **Performance**: Redis 7 with AOF (Append Only File) persistence

## 📋 Prerequisites

Before starting, ensure you have:

- Docker installed and running
- Port 6380 available (we use 6380 to avoid conflicts with system Redis)
- Sufficient disk space for persistent storage (minimum 1GB recommended)
- Administrative access to create Docker containers and volumes

## 🚀 Initial Setup

### 1. Create Persistent Redis Container

Run this command to create the Redis container with persistent storage:

```bash
docker run -d \
  --name agent-memory-redis \
  --label "project=uplevel-ai-agents" \
  --label "component=persistent-memory" \
  --label "purpose=agent-context-storage" \
  -p 6380:6379 \
  -v agent-memory-data:/data \
  --restart unless-stopped \
  redis:7-alpine redis-server --appendonly yes --save 60 1
```

**Command Breakdown:**
- `--name agent-memory-redis`: Identifiable container name
- `--label`: Metadata tags for easy identification
- `-p 6380:6379`: Maps internal Redis port to external port 6380
- `-v agent-memory-data:/data`: Creates persistent volume for data storage
- `--restart unless-stopped`: Auto-restart on failure or reboot
- `redis-server --appendonly yes --save 60 1`: Enable AOF persistence + snapshot every 60 seconds if 1 key changes

### 2. Verify Container Status

Check that the container is running:

```bash
# Check container status
docker ps | grep agent-memory-redis

# Expected output:
# CONTAINER ID   IMAGE           COMMAND                  CREATED          STATUS          PORTS                                           NAMES
# a18a85e594dd   redis:7-alpine  "docker-entrypoint.s…"   X minutes ago    Up X minutes    0.0.0.0:6380->6379/tcp, [::]:6380->6379/tcp   agent-memory-redis
```

### 3. Test Redis Connectivity

Verify Redis is responding:

```bash
# Test Redis ping
docker exec agent-memory-redis redis-cli ping

# Expected output: PONG
```

### 4. Test Data Persistence

Store and retrieve test data:

```bash
# Store test data
docker exec agent-memory-redis redis-cli set "test:setup" "Redis persistent memory working"

# Retrieve test data
docker exec agent-memory-redis redis-cli get "test:setup"

# Expected output: "Redis persistent memory working"
```

## 🔄 Project Context Management

### Storing Project Context

The system uses a hierarchical key structure for organizing project data:

```bash
# Store project metadata
docker exec agent-memory-redis redis-cli hset "project:uplevel-phase2-1756155822:scope" \
  "system_name" "Uplevel AI Agent System" \
  "architecture" "Multi-agent orchestrated system" \
  "components" "orchestrator,financial_intelligence,sales_marketing,hubspot_mcp,quickbooks_mcp,frontend_portal" \
  "deployment_status" "Complete" \
  "created_at" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Store task progress
docker exec agent-memory-redis redis-cli hset "project:uplevel-phase2-1756155822:tasks" \
  "readme_enhancement" "completed" \
  "github_deployment" "completed" \
  "redis_setup" "completed" \
  "documentation" "in_progress"

# Store artifacts and code references
docker exec agent-memory-redis redis-cli hset "project:uplevel-phase2-1756155822:artifacts" \
  "github_repo" "https://github.com/brandon-uplevel/uplevel-ai-agents" \
  "main_readme" "/home/brandon/projects/uplevel/README.md" \
  "redis_container" "agent-memory-redis" \
  "redis_port" "6380"
```

### Retrieving Project Context

```bash
# Get all project scope data
docker exec agent-memory-redis redis-cli hgetall "project:uplevel-phase2-1756155822:scope"

# Get specific project information
docker exec agent-memory-redis redis-cli hget "project:uplevel-phase2-1756155822:scope" "system_name"

# List all project keys
docker exec agent-memory-redis redis-cli keys "project:uplevel-phase2-1756155822:*"
```

## 🔧 Maintenance Operations

### Container Management

#### Start Container (if stopped)
```bash
docker start agent-memory-redis
```

#### Stop Container
```bash
docker stop agent-memory-redis
```

#### Restart Container
```bash
docker restart agent-memory-redis
```

#### View Container Logs
```bash
# View recent logs
docker logs agent-memory-redis

# Follow logs in real-time
docker logs -f agent-memory-redis

# View last 50 log lines
docker logs --tail 50 agent-memory-redis
```

### Data Management

#### Backup Redis Data
```bash
# Create backup of Redis data
docker exec agent-memory-redis redis-cli BGSAVE

# Copy backup file from container
docker cp agent-memory-redis:/data/dump.rdb ./redis-backup-$(date +%Y%m%d-%H%M%S).rdb
```

#### Restore Redis Data
```bash
# Stop container
docker stop agent-memory-redis

# Copy backup file to container volume
docker run --rm -v agent-memory-data:/data -v $(pwd):/backup alpine cp /backup/redis-backup-XXXXXX.rdb /data/dump.rdb

# Start container
docker start agent-memory-redis
```

#### View Data Statistics
```bash
# Get Redis info
docker exec agent-memory-redis redis-cli info

# Get memory usage
docker exec agent-memory-redis redis-cli info memory

# Get keyspace info
docker exec agent-memory-redis redis-cli info keyspace

# Count keys by pattern
docker exec agent-memory-redis redis-cli eval "return #redis.call('keys', ARGV[1])" 0 "project:*"
```

## 🖥️ Computer Restart Recovery

The container is configured with `--restart unless-stopped`, which means it will automatically start when Docker starts after a computer reboot.

### Manual Recovery Steps

If automatic restart fails, follow these steps:

#### 1. Check Docker Status
```bash
# Verify Docker is running
docker --version
docker ps
```

#### 2. Check Container Status
```bash
# List all containers (including stopped ones)
docker ps -a | grep agent-memory-redis

# Check container restart policy
docker inspect agent-memory-redis | grep RestartPolicy -A 3
```

#### 3. Start Container if Needed
```bash
# Start the container
docker start agent-memory-redis

# Verify it's running
docker ps | grep agent-memory-redis
```

#### 4. Verify Data Integrity
```bash
# Test Redis connectivity
docker exec agent-memory-redis redis-cli ping

# Check if project data is intact
docker exec agent-memory-redis redis-cli hget "project:uplevel-phase2-1756155822:scope" "system_name"
```

## 🔍 Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Container Won't Start
```bash
# Check if port is already in use
netstat -tlnp | grep 6380

# Check container logs for errors
docker logs agent-memory-redis

# Remove and recreate container if necessary
docker rm agent-memory-redis
# Then run the initial setup command again
```

#### Issue: Can't Connect to Redis
```bash
# Test connectivity from host
redis-cli -p 6380 ping

# If redis-cli not installed, use Docker
docker exec agent-memory-redis redis-cli ping

# Check if Redis is listening on correct port
docker exec agent-memory-redis netstat -tlnp | grep 6379
```

#### Issue: Data Not Persisting
```bash
# Check volume mount
docker inspect agent-memory-redis | grep -A 10 "Mounts"

# Verify AOF is enabled
docker exec agent-memory-redis redis-cli config get appendonly

# Check disk space
df -h
docker system df
```

#### Issue: High Memory Usage
```bash
# Check Redis memory usage
docker exec agent-memory-redis redis-cli info memory

# Check for memory leaks (keys that keep growing)
docker exec agent-memory-redis redis-cli --bigkeys

# Set memory limit if needed
docker update --memory="512m" agent-memory-redis
```

### Performance Optimization

#### Monitor Redis Performance
```bash
# Real-time Redis monitoring
docker exec -it agent-memory-redis redis-cli monitor

# Check slow queries
docker exec agent-memory-redis redis-cli slowlog get 10

# Get Redis statistics
docker exec agent-memory-redis redis-cli --stat
```

#### Optimize Configuration
```bash
# Adjust save intervals for your use case
docker exec agent-memory-redis redis-cli config set save "300 10 60 1000"

# Configure maximum memory if needed
docker exec agent-memory-redis redis-cli config set maxmemory 256mb
docker exec agent-memory-redis redis-cli config set maxmemory-policy allkeys-lru
```

## 🚨 Emergency Recovery

### Complete Container Recreation

If the container becomes corrupted, recreate it while preserving data:

```bash
# 1. Stop and remove container (data volume remains)
docker stop agent-memory-redis
docker rm agent-memory-redis

# 2. Recreate container using same volume
docker run -d \
  --name agent-memory-redis \
  --label "project=uplevel-ai-agents" \
  --label "component=persistent-memory" \
  --label "purpose=agent-context-storage" \
  -p 6380:6379 \
  -v agent-memory-data:/data \
  --restart unless-stopped \
  redis:7-alpine redis-server --appendonly yes --save 60 1

# 3. Verify data is intact
docker exec agent-memory-redis redis-cli keys "*" | wc -l
```

### Volume Recovery

If the volume becomes corrupted:

```bash
# 1. Create backup of existing volume
docker run --rm -v agent-memory-data:/source -v $(pwd):/backup alpine tar czf /backup/agent-memory-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C /source .

# 2. Remove corrupted volume
docker volume rm agent-memory-data

# 3. Recreate container (will create new volume)
docker run -d \
  --name agent-memory-redis \
  --label "project=uplevel-ai-agents" \
  --label "component=persistent-memory" \
  --label "purpose=agent-context-storage" \
  -p 6380:6379 \
  -v agent-memory-data:/data \
  --restart unless-stopped \
  redis:7-alpine redis-server --appendonly yes --save 60 1
```

## 📊 Monitoring and Alerting

### Health Check Script

Create a monitoring script to check Redis health:

```bash
#!/bin/bash
# redis-health-check.sh

CONTAINER_NAME="agent-memory-redis"
REDIS_PORT="6380"

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "ERROR: $CONTAINER_NAME container is not running"
    exit 1
fi

# Test Redis connectivity
if ! docker exec "$CONTAINER_NAME" redis-cli ping | grep -q "PONG"; then
    echo "ERROR: Redis is not responding to ping"
    exit 1
fi

# Check project data integrity
if ! docker exec "$CONTAINER_NAME" redis-cli exists "project:uplevel-phase2-1756155822:scope" | grep -q "1"; then
    echo "WARNING: Project context data may be missing"
    exit 1
fi

echo "SUCCESS: Redis persistent memory is healthy"
exit 0
```

### Automated Monitoring Setup

```bash
# Make script executable
chmod +x redis-health-check.sh

# Add to crontab for regular health checks (every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /path/to/redis-health-check.sh >> /var/log/redis-health.log 2>&1") | crontab -
```

## 🔐 Security Considerations

### Access Control

```bash
# Set Redis authentication (optional but recommended for production)
docker exec agent-memory-redis redis-cli config set requirepass "your-secure-password"

# Connect with password
docker exec agent-memory-redis redis-cli -a "your-secure-password" ping
```

### Network Security

```bash
# For production, bind to localhost only
docker run -d \
  --name agent-memory-redis \
  --label "project=uplevel-ai-agents" \
  -p 127.0.0.1:6380:6379 \
  -v agent-memory-data:/data \
  --restart unless-stopped \
  redis:7-alpine redis-server --appendonly yes --save 60 1 --bind 127.0.0.1
```

## 📈 Scaling Considerations

### Multi-Instance Setup

For high-availability setups:

```bash
# Create Redis cluster with multiple instances
docker run -d --name agent-memory-redis-1 -p 6380:6379 -v agent-memory-data-1:/data redis:7-alpine redis-server --cluster-enabled yes --cluster-config-file nodes-1.conf --cluster-node-timeout 5000 --appendonly yes --port 6379
docker run -d --name agent-memory-redis-2 -p 6381:6379 -v agent-memory-data-2:/data redis:7-alpine redis-server --cluster-enabled yes --cluster-config-file nodes-2.conf --cluster-node-timeout 5000 --appendonly yes --port 6379
docker run -d --name agent-memory-redis-3 -p 6382:6379 -v agent-memory-data-3:/data redis:7-alpine redis-server --cluster-enabled yes --cluster-config-file nodes-3.conf --cluster-node-timeout 5000 --appendonly yes --port 6379
```

## 📝 Configuration Reference

### Redis Container Labels

The container uses these labels for identification:

- `project=uplevel-ai-agents`: Identifies project association
- `component=persistent-memory`: Identifies component type  
- `purpose=agent-context-storage`: Describes the container's purpose

### Environment Variables

For programmatic access, set these environment variables:

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6380
export REDIS_DB=0
export PROJECT_ID=uplevel-phase2-1756155822
```

### Connection URLs

Applications can connect using these patterns:

- **Standard**: `redis://localhost:6380`
- **With DB selection**: `redis://localhost:6380/0`
- **With password**: `redis://:password@localhost:6380`

## 🎯 Best Practices

### Data Organization
- Use hierarchical keys: `project:ID:category:item`
- Set appropriate TTL for temporary data
- Use Redis data types effectively (hashes, sets, lists)
- Implement key naming conventions

### Performance
- Monitor memory usage regularly
- Use pipeline commands for bulk operations
- Implement proper error handling in applications
- Set up monitoring and alerting

### Maintenance
- Regular backups (daily recommended)
- Monitor disk space usage
- Update Redis image periodically
- Review and clean up old data

---

## 📞 Support

For issues with Redis MCP setup:

1. Check the troubleshooting guide above
2. Verify all prerequisites are met
3. Review container logs for specific error messages
4. Ensure Docker has sufficient resources
5. Check network connectivity and port availability

**Container Quick Commands:**
```bash
# Status check
docker ps | grep agent-memory-redis

# Health check  
docker exec agent-memory-redis redis-cli ping

# View logs
docker logs agent-memory-redis

# Restart if needed
docker restart agent-memory-redis
```

---

**Last updated**: August 2025  
**Redis Version**: 7-alpine  
**Container Name**: agent-memory-redis  
**Port**: 6380  
**Volume**: agent-memory-data  
**Project ID**: uplevel-phase2-1756155822
