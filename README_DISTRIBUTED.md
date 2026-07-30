# Distributed Exam System - Architecture Guide

## Overview

This distributed exam system consists of 3 nodes that communicate via REST APIs to provide high availability, load balancing, and data synchronization across the cluster.

## Architecture

### Node Structure
- **Node A** (Port 5001): Primary node
- **Node B** (Port 5002): Secondary node  
- **Node C** (Port 5003): Secondary node

### Key Features
- **Inter-node Communication**: REST API endpoints for data synchronization
- **Heartbeat Monitoring**: Nodes monitor each other's health
- **Data Replication**: Exam data and responses synchronized across nodes
- **Load Distribution**: Exam sessions distributed across available nodes
- **Failover Handling**: Automatic detection and handling of node failures

## Quick Start

### 1. Start the Cluster

```bash
# Start all 3 nodes simultaneously
python start_cluster.py
```

This will start:
- Node A: http://127.0.0.1:5001
- Node B: http://127.0.0.1:5002  
- Node C: http://127.0.0.1:5003

### 2. Monitor the Cluster

```bash
# Check status of all nodes
python cluster_manager.py status

# Test inter-node communication
python cluster_manager.py test

# Monitor cluster for 60 seconds
python cluster_manager.py monitor --duration 60
```

### 3. Access the System

You can access the exam system through any node:
- http://127.0.0.1:5001 (Node A)
- http://127.0.0.1:5002 (Node B)
- http://127.0.0.1:5003 (Node C)

## Node Communication APIs

### Heartbeat API
```http
POST /node/heartbeat
Content-Type: application/json

{
  "node_id": "node_5001",
  "port": 5001,
  "timestamp": "2024-01-01T12:00:00"
}
```

### Exam Broadcast API
```http
POST /node/exam/start
Content-Type: application/json

{
  "exam_id": 1,
  "user_id": 123,
  "node_id": "node_5001"
}
```

### Response Sync API
```http
POST /node/response/sync
Content-Type: application/json

{
  "response_id": 456,
  "user_id": 123,
  "exam_id": 1,
  "answers": {"1": "A", "2": "B"},
  "score": 85,
  "node_id": "node_5001"
}
```

### Node Status API
```http
GET /node/status

Response:
{
  "node_id": "node_5001",
  "port": 5001,
  "active_nodes": 2,
  "total_exams": 5,
  "total_responses": 150,
  "timestamp": "2024-01-01T12:00:00"
}
```

## Data Synchronization

### Automatic Synchronization
- **Heartbeat**: Every 10 seconds between nodes
- **Exam Events**: Real-time broadcast when exams start
- **Response Data**: Immediate sync when students submit exams
- **Full Sync**: Manual or periodic complete data synchronization

### Synchronization Flow
1. Student starts exam on Node A
2. Node A broadcasts exam start to Nodes B and C
3. Student submits answers
4. Node A syncs response data to Nodes B and C
5. All nodes maintain consistent dataset

## Node Management

### Starting Individual Nodes
```bash
# Start specific node
python node_a.py    # Port 5001
python node_b.py    # Port 5002
python node_c.py    # Port 5003
```

### Cluster Management Commands
```bash
# Check all node status
python cluster_manager.py status

# Force synchronization
python cluster_manager.py sync

# Test communication
python cluster_manager.py test

# Monitor cluster health
python cluster_manager.py monitor --duration 120

# Broadcast exam event
python cluster_manager.py broadcast --exam-id 1 --user-id 123
```

## Database Configuration

Each node can use its own database or share a common database:

### Individual Databases (Recommended for Production)
```bash
# Node A
export DB_NAME=exam_system_node_a
python node_a.py

# Node B  
export DB_NAME=exam_system_node_b
python node_b.py

# Node C
export DB_NAME=exam_system_node_c
python node_c.py
```

### Shared Database (For Development)
```bash
# All nodes share the same database
export DB_NAME=exam_system_shared
python start_cluster.py
```

## Load Balancing

### Session Distribution
- Exam sessions are distributed across available nodes
- Round-robin algorithm for initial assignment
- Automatic failover to healthy nodes

### Request Routing
- Client can connect to any node
- Nodes internally coordinate for data consistency
- No external load balancer required

## Fault Tolerance

### Node Failure Detection
- Heartbeat timeout: 30 seconds
- Automatic marking of failed nodes
- Graceful degradation of service

### Failover Process
1. Node failure detected via missed heartbeats
2. Active exam sessions redistributed
3. Data synchronization from remaining nodes
4. Client requests rerouted to healthy nodes

### Recovery
- Failed nodes can rejoin cluster automatically
- Data resynchronization on reconnection
- No data loss due to replication

## Monitoring and Logging

### Node Logs
Each node logs:
- Inter-node communication
- Synchronization events
- Error conditions
- Performance metrics

### Cluster Monitoring
```bash
# Real-time monitoring
python cluster_manager.py monitor

# Status overview
python cluster_manager.py status

# Communication test
python cluster_manager.py test
```

## Security Considerations

### Inter-node Security
- All nodes should be on the same trusted network
- Consider adding API authentication for production
- Use HTTPS for inter-node communication in production

### Data Protection
- Sensitive exam data replicated across nodes
- Ensure proper database security
- Regular backup of all node databases

## Performance Optimization

### Synchronization Optimization
- Incremental sync for large datasets
- Compressed data transfer
- Async processing for non-critical sync

### Resource Management
- Connection pooling for inter-node requests
- Memory-efficient data structures
- Background thread management

## Troubleshooting

### Common Issues

#### Node Won't Start
```bash
# Check if port is available
netstat -an | grep :5001

# Check dependencies
python -c "from app import create_app; print('OK')"
```

#### Nodes Can't Communicate
```bash
# Test network connectivity
python cluster_manager.py test

# Check firewall settings
telnet localhost 5001
```

#### Data Inconsistency
```bash
# Force full synchronization
python cluster_manager.py sync

# Check node status
python cluster_manager.py status
```

### Debug Mode
Start nodes with debug logging:
```bash
export FLASK_DEBUG=True
python node_a.py
```

## Scaling the System

### Adding New Nodes
1. Create new node script (e.g., `node_d.py`)
2. Update node configuration in `core/node_manager.py`
3. Add to cluster startup script
4. Update cluster manager

### Horizontal Scaling
- Add more nodes as needed
- Load automatically distributed
- No code changes required

### Vertical Scaling
- Increase node resources
- Optimize database performance
- Add caching layers

## Production Deployment

### Recommended Setup
- 3+ nodes for high availability
- Separate database servers
- Load balancer for client connections
- Monitoring and alerting system

### Configuration
```bash
# Production environment
export FLASK_ENV=production
export DB_TYPE=mysql
export DB_HOST=db-server.example.com
export DB_NAME=exam_system
export DB_USER=exam_user
export DB_PASSWORD=secure_password
```

## API Reference

### Distributed APIs
- `POST /node/heartbeat` - Node health check
- `POST /node/exam/start` - Broadcast exam start
- `POST /node/response/sync` - Sync response data
- `GET /node/status` - Get node status
- `GET /node/exams` - Get exam data
- `GET /node/responses` - Get response data
- `POST /node/sync/full` - Full data sync

### Standard APIs
All standard exam system APIs are available on each node:
- `GET /` - Homepage
- `POST /login` - User authentication
- `GET /dashboard` - User dashboard
- `GET /exam/<id>` - Take exam
- `POST /submit_exam` - Submit exam

## Development

### Running Tests
```bash
# Test individual node
python -m pytest tests/test_node.py

# Test cluster communication
python -m pytest tests/test_distributed.py
```

### Code Structure
```
distributed_exam_system/
|
|-- app/
|   |-- distributed_routes.py  # Inter-node APIs
|   |-- services.py           # Business logic
|   |-- models.py             # Database models
|
|-- core/
|   |-- node_manager.py       # Node management
|   |-- node.py               # Original node code
|
|-- node_a.py                 # Node A startup
|-- node_b.py                 # Node B startup  
|-- node_c.py                 # Node C startup
|-- start_cluster.py         # Cluster startup
|-- cluster_manager.py       # Management CLI
```

## Support

For issues with the distributed system:
1. Check individual node logs
2. Verify network connectivity
3. Test with cluster management tools
4. Review synchronization logs
