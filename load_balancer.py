#!/usr/bin/env python3
"""
Distributed Load Balancer for Online Exam System
Routes traffic to multiple worker nodes with smart routing and failover
"""

import requests
import time
from flask import Flask, request, jsonify, redirect, render_template_string
from threading import Lock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Node configuration
NODES = [
    {"id": "A", "url": "http://127.0.0.1:5001", "port": 5001, "load": 0, "active": True},
    {"id": "B", "url": "http://127.0.0.1:5002", "port": 5002, "load": 0, "active": True},
    {"id": "C", "url": "http://127.0.0.1:5003", "port": 5003, "load": 0, "active": True}
]

# Lock for thread-safe operations
node_lock = Lock()

# Round robin counter
round_robin_index = 0

# Routing statistics
routing_stats = {
    "total_requests": 0,
    "node_requests": {"A": 0, "B": 0, "C": 0},
    "failures": 0,
    "health_checks": 0
}

class LoadBalancer:
    """Load balancer with multiple routing strategies"""
    
    def __init__(self):
        self.nodes = NODES
        self.round_robin_index = 0
        self.stats = routing_stats
        
    def health_check(self, node):
        """Check if a node is healthy"""
        try:
            response = requests.get(f"{node['url']}/health", timeout=2)
            if response.status_code == 200:
                node['active'] = True
                return True
            else:
                node['active'] = False
                return False
        except Exception as e:
            logger.warning(f"Health check failed for Node {node['id']}: {e}")
            node['active'] = False
            return False
    
    def check_all_nodes(self):
        """Check health of all nodes"""
        with node_lock:
            for node in self.nodes:
                self.health_check(node)
            self.stats["health_checks"] += 1
    
    def get_active_nodes(self):
        """Get list of active nodes"""
        return [node for node in self.nodes if node['active']]
    
    def round_robin_routing(self):
        """Round robin routing strategy"""
        active_nodes = self.get_active_nodes()
        
        if not active_nodes:
            logger.error("No active nodes available!")
            return None
        
        with node_lock:
            # Find next active node
            attempts = 0
            while attempts < len(self.nodes):
                node = self.nodes[self.round_robin_index]
                self.round_robin_index = (self.round_robin_index + 1) % len(self.nodes)
                
                if node['active']:
                    logger.info(f"Round Robin: Routing to Node {node['id']}")
                    return node
                attempts += 1
            
            return None
    
    def smart_routing(self):
        """Smart routing based on node load"""
        active_nodes = self.get_active_nodes()
        
        if not active_nodes:
            logger.error("No active nodes available!")
            return None
        
        # Find node with minimum load
        min_load_node = min(active_nodes, key=lambda x: x['load'])
        
        logger.info(f"Smart Routing: Routing to Node {min_load_node['id']} (least load: {min_load_node['load']})")
        return min_load_node
    
    def route_request(self, strategy="smart"):
        """Route request to selected node with enhanced failover"""
        self.stats["total_requests"] += 1
        
        # Select node based on strategy
        if strategy == "round_robin":
            node = self.round_robin_routing()
        else:  # smart routing (default)
            node = self.smart_routing()
        
        if not node:
            self.stats["failures"] += 1
            return None, "No active nodes available"
        
        # Try to register session on the node
        try:
            response = requests.post(f"{node['url']}/api/fault_tolerance/register_session", 
                                   json={"exam_id": 1, "node_id": node['id']}, 
                                   timeout=3)
            if response.status_code == 200:
                with node_lock:
                    node['load'] += 1
                    self.stats["node_requests"][node['id']] += 1
                logger.info(f"Successfully routed to Node {node['id']}")
                return node, None
            else:
                # Node failed, mark as inactive and try next
                logger.error(f"Failed to register session on Node {node['id']}: {response.status_code}")
                self.handle_node_failure(node['id'])
                return self.route_request(strategy)  # Recursive call to try next node
                
        except Exception as e:
            logger.error(f"Error routing to Node {node['id']}: {e}")
            self.handle_node_failure(node['id'])
            self.stats["failures"] += 1
            return self.route_request(strategy)  # Recursive call to try next node
    
    def handle_node_failure(self, node_id):
        """Handle node failure with logging and failover"""
        logger.error(f"Node {node_id} failed! Initiating failover...")
        
        # Mark node as inactive
        for node in self.nodes:
            if node['id'] == node_id:
                node['active'] = False
                break
        
        # Log failover action
        active_nodes = self.get_active_nodes()
        if active_nodes:
            next_node = active_nodes[0]
            logger.info(f"Node {node_id} is down. Switching to Node {next_node['id']}")
        else:
            logger.error("No backup nodes available!")
    
    def route_to_resume_session(self, session_id):
        """Route user to appropriate node for session resumption"""
        try:
            # Try to find which node has the session
            for node in self.nodes:
                if not node['active']:
                    continue
                
                try:
                    response = requests.get(f"{node['url']}/api/fault_tolerance/resume_exam/{session_id}", timeout=3)
                    if response.status_code == 200:
                        logger.info(f"Session {session_id} found on Node {node['id']}")
                        return node, None
                except:
                    # Node not responding, try next
                    continue
            
            # If no active node has the session, try to restore on any healthy node
            healthy_nodes = self.get_active_nodes()
            if healthy_nodes:
                target_node = healthy_nodes[0]
                logger.info(f"Restoring session {session_id} on Node {target_node['id']}")
                return target_node, None
            
            return None, "No healthy nodes available for session recovery"
            
        except Exception as e:
            logger.error(f"Error in session recovery routing: {e}")
            return None, str(e)

# Initialize load balancer
load_balancer = LoadBalancer()

# HTML template for status dashboard
STATUS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Load Balancer Status</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h1 class="mb-4">Distributed Load Balancer Status</h1>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Node Status</h5>
                    </div>
                    <div class="card-body">
                        {% for node in nodes %}
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span>
                                <strong>Node {{ node.id }} ({{ node.port }})</strong>
                                {% if node.active %}
                                <span class="badge bg-success">Active</span>
                                {% else %}
                                <span class="badge bg-danger">Down</span>
                                {% endif %}
                            </span>
                            <span class="badge bg-primary">{{ node.load }} users</span>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Routing Statistics</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Total Requests:</strong> {{ stats.total_requests }}</p>
                        <p><strong>Failures:</strong> {{ stats.failures }}</p>
                        <p><strong>Health Checks:</strong> {{ stats.health_checks }}</p>
                        <hr>
                        {% for node_id, count in stats.node_requests.items() %}
                        <p><strong>Node {{ node_id }}:</strong> {{ count }} requests</p>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-4">
            <a href="/route_exam" class="btn btn-primary">Route to Exam (Smart Routing)</a>
            <a href="/route_exam?strategy=round_robin" class="btn btn-secondary">Route to Exam (Round Robin)</a>
            <a href="/check_health" class="btn btn-info">Check All Nodes Health</a>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Load balancer dashboard"""
    return render_template_string(STATUS_TEMPLATE, nodes=NODES, stats=routing_stats)

@app.route('/route_exam')
def route_exam():
    """Route user to an available node"""
    strategy = request.args.get('strategy', 'smart')
    
    logger.info(f"Routing request received - Strategy: {strategy}")
    
    # Get node for routing
    node, error = load_balancer.route_request(strategy)
    
    if error:
        logger.error(f"Routing failed: {error}")
        return jsonify({"error": error}), 503
    
    # Redirect user to selected node
    exam_url = f"{node['url']}/"
    logger.info(f"Redirecting user to {exam_url}")
    
    return redirect(exam_url)

@app.route('/resume_exam/<session_id>')
def resume_exam(session_id):
    """Route user to appropriate node for session recovery"""
    logger.info(f"Session recovery request for session {session_id}")
    
    # Find node with the session
    node, error = load_balancer.route_to_resume_session(session_id)
    
    if error:
        logger.error(f"Session recovery failed: {error}")
        return jsonify({"error": error}), 503
    
    # Redirect user to node with session recovery
    resume_url = f"{node['url']}/api/fault_tolerance/resume_exam/{session_id}"
    logger.info(f"Redirecting session recovery to {resume_url}")
    
    return redirect(resume_url)

@app.route('/node_status')
def node_status():
    """Get status of all nodes"""
    with node_lock:
        status = {
            "nodes": [
                {
                    "id": node["id"],
                    "url": node["url"],
                    "port": node["port"],
                    "load": node["load"],
                    "active": node["active"]
                }
                for node in NODES
            ],
            "statistics": routing_stats
        }
    
    return jsonify(status)

@app.route('/check_health')
def check_health():
    """Check health of all nodes"""
    logger.info("Performing health check on all nodes...")
    load_balancer.check_all_nodes()
    
    active_nodes = load_balancer.get_active_nodes()
    health_status = {
        "total_nodes": len(NODES),
        "active_nodes": len(active_nodes),
        "nodes": [{"id": node["id"], "status": "healthy" if node["active"] else "unhealthy"} for node in NODES]
    }
    
    return jsonify(health_status)

@app.route('/end_session/<node_id>', methods=['POST'])
def end_session(node_id):
    """End session on specific node"""
    try:
        # Find the node
        node = next((n for n in NODES if n['id'] == node_id), None)
        
        if not node:
            return jsonify({"error": f"Node {node_id} not found"}), 404
        
        # Call node to end session
        response = requests.post(f"{node['url']}/end_session", timeout=3)
        
        if response.status_code == 200:
            with node_lock:
                if node['load'] > 0:
                    node['load'] -= 1
            logger.info(f"Session ended on Node {node_id}")
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to end session"}), response.status_code
            
    except Exception as e:
        logger.error(f"Error ending session on Node {node_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/reset_stats', methods=['POST'])
def reset_stats():
    """Reset routing statistics"""
    global routing_stats
    with node_lock:
        routing_stats = {
            "total_requests": 0,
            "node_requests": {"A": 0, "B": 0, "C": 0},
            "failures": 0,
            "health_checks": 0
        }
    
    logger.info("Routing statistics reset")
    return jsonify({"success": True, "message": "Statistics reset"})

def start_background_health_checker():
    """Start background health checker"""
    import threading
    
    def health_checker():
        while True:
            time.sleep(10)  # Check every 10 seconds
            load_balancer.check_all_nodes()
    
    health_thread = threading.Thread(target=health_checker, daemon=True)
    health_thread.start()
    logger.info("Background health checker started")

if __name__ == '__main__':
    logger.info("Starting Distributed Load Balancer on port 5000...")
    logger.info("Available endpoints:")
    logger.info("  GET  /                 - Dashboard")
    logger.info("  GET  /route_exam       - Route to exam (smart routing)")
    logger.info("  GET  /route_exam?strategy=round_robin - Route to exam (round robin)")
    logger.info("  GET  /node_status      - Node status JSON")
    logger.info("  GET  /check_health     - Health check all nodes")
    logger.info("  POST /end_session/<id> - End session on node")
    logger.info("  POST /reset_stats      - Reset statistics")
    
    # Start background health checker
    start_background_health_checker()
    
    # Start Flask app
    app.run(host='127.0.0.1', port=5000, debug=True)
