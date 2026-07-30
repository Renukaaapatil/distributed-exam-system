#!/usr/bin/env python3
"""
Node C - Port 5003
Distributed Exam System Node
"""

import os
import sys
from app import create_app, db
from app.routes import main_bp
from app.distributed_routes import distributed_bp
from core.node_manager import NodeManager, DistributedCoordinator
import logging

def create_node_app():
    """Create Flask app for Node C"""
    app = create_app('development')
    
    # Configure for Node C
    app.config['NODE_ID'] = 'node_5003'
    app.config['NODE_PORT'] = 5003
    
    # Initialize RPC handler
    from app.rpc_handlers import init_rpc_handler
    init_rpc_handler('node_5003')
    
    # Initialize node manager
    node_manager = NodeManager(node_id='node_5003', port=5003)
    node_manager.initialize_peers()
    
    # Store node manager in app context
    app.node_manager = node_manager
    app.distributed_coordinator = DistributedCoordinator(node_manager)
    app.fault_tolerance_manager = node_manager.fault_tolerance_manager
    
    # Start heartbeat and fault tolerance systems
    node_manager.start_heartbeat_thread()
    node_manager.start_fault_tolerance()
    
    return app, node_manager

def main():
    """Main function for Node C"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Create app and node manager
    app, node_manager = create_node_app()
    
    # Node configuration
    host = '127.0.0.1'
    port = 5003
    debug = False  # Production mode for nodes
    
    print("=" * 60)
    print("Distributed Exam System - Node C")
    print("=" * 60)
    print(f"Node ID: {node_manager.node_id}")
    print(f"Server running on: http://{host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("=" * 60)
    print("Node C is ready to handle requests...")
    print("Peers: Node A (port 5001), Node B (port 5002)")
    print("=" * 60)
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("Node C shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Node C error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
