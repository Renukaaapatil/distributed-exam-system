#!/usr/bin/env python3
"""
Node B - Port 5002
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
    """Create Flask app for Node B"""
    app = create_app('development')
    
    # Configure for Node B
    app.config['NODE_ID'] = 'node_5002'
    app.config['NODE_PORT'] = 5002
    
    # Initialize RPC handler
    from app.rpc_handlers import init_rpc_handler
    init_rpc_handler('node_5002')
    
    # Initialize node manager
    node_manager = NodeManager(node_id='node_5002', port=5002)
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
    """Main function for Node B"""
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
    port = 5002
    debug = False  # Production mode for nodes
    
    print("=" * 60)
    print("Distributed Exam System - Node B")
    print("=" * 60)
    print(f"Node ID: {node_manager.node_id}")
    print(f"Server running on: http://{host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("=" * 60)
    print("Node B is ready to handle requests...")
    print("Peers: Node A (port 5001), Node C (port 5003)")
    print("=" * 60)
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("Node B shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Node B error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
