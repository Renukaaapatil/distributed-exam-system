"""
Node Manager for Distributed Exam System
Handles node discovery, communication, and synchronization
"""

import requests
import json
import threading
import time
from datetime import datetime, timedelta
from flask import current_app
from core.rpc_client import RPCManager, RPCError
from core.fault_tolerance import FaultToleranceManager
import logging

class NodeManager:
    """Manages distributed node operations"""
    
    def __init__(self, node_id=None, port=5001):
        self.node_id = node_id or f"node_{port}"
        self.port = port
        self.peers = {}  # {node_id: {'port': int, 'last_heartbeat': datetime}}
        self.exam_sessions = {}  # {exam_session_key: {metadata}}
        self.sync_log = []  # Log of sync operations
        self.logger = logging.getLogger(__name__)
        
        # Initialize RPC manager
        self.rpc_manager = RPCManager(self.node_id)
        
        # Initialize fault tolerance manager (will be set after RPC manager is ready)
        self.fault_tolerance_manager = None
        
        # Default peer nodes (can be configured)
        self.default_peers = {
            'node_5001': 5001,
            'node_5002': 5002,
            'node_5003': 5003
        }
    
    def initialize_peers(self):
        """Initialize peer nodes and RPC clients"""
        for node_id, port in self.default_peers.items():
            if node_id != self.node_id:
                self.peers[node_id] = {
                    'port': port,
                    'last_heartbeat': None,
                    'status': 'unknown'
                }
                
                # Add RPC client for this peer
                base_url = f"http://127.0.0.1:{port}"
                self.rpc_manager.add_client(node_id, base_url, timeout=5, max_retries=3)
                self.logger.info(f"Added RPC client for {node_id} at {base_url}")
        
        # Initialize fault tolerance manager after RPC clients are set up
        self.fault_tolerance_manager = FaultToleranceManager(self.node_id, self.rpc_manager)
        self.logger.info("Fault tolerance manager initialized")
    
    def register_heartbeat(self, node_id, port, timestamp):
        """Register heartbeat from a peer node"""
        if node_id not in self.peers:
            self.peers[node_id] = {
                'port': port,
                'last_heartbeat': None,
                'status': 'unknown'
            }
        
        try:
            heartbeat_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            self.peers[node_id]['last_heartbeat'] = heartbeat_time
            self.peers[node_id]['status'] = 'active'
            self.logger.info(f"Received heartbeat from {node_id}")
        except Exception as e:
            self.logger.error(f"Error processing heartbeat from {node_id}: {e}")
    
    def get_active_nodes(self):
        """Get list of active nodes"""
        active_nodes = []
        current_time = datetime.utcnow()
        
        for node_id, peer_info in self.peers.items():
            if peer_info['last_heartbeat']:
                # Consider node active if heartbeat received in last 30 seconds
                if current_time - peer_info['last_heartbeat'] < timedelta(seconds=30):
                    active_nodes.append({
                        'node_id': node_id,
                        'port': peer_info['port'],
                        'last_seen': peer_info['last_heartbeat'].isoformat()
                    })
        
        return active_nodes
    
    def send_heartbeat_to_peers(self):
        """Send heartbeat to all peer nodes"""
        heartbeat_data = {
            'node_id': self.node_id,
            'port': self.port,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for node_id, peer_info in self.peers.items():
            try:
                url = f"http://localhost:{peer_info['port']}/node/heartbeat"
                response = requests.post(url, json=heartbeat_data, timeout=5)
                if response.status_code == 200:
                    self.logger.debug(f"Heartbeat sent to {node_id}")
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Failed to send heartbeat to {node_id}: {e}")
                peer_info['status'] = 'inactive'
    
    def broadcast_exam_start(self, exam_id, user_id):
        """Broadcast exam start to all nodes using RPC"""
        params = {
            'exam_id': exam_id,
            'user_id': user_id
        }
        
        try:
            # Use RPC to broadcast exam start
            results = self.rpc_manager.broadcast('exam.start', params)
            
            successful_nodes = []
            for node_id, response in results.items():
                if response.is_success:
                    successful_nodes.append(node_id)
                    self.logger.info(f"Exam start broadcast to {node_id} via RPC")
                else:
                    self.logger.error(f"RPC exam.start failed for {node_id}: {response.error_message}")
            
            return successful_nodes
            
        except Exception as e:
            self.logger.error(f"RPC broadcast exam start failed: {e}")
            return []
    
    def sync_response_to_peers(self, response_id, user_id, exam_id, answers, score):
        """Sync response to all peer nodes using RPC"""
        params = {
            'response_id': response_id,
            'user_id': user_id,
            'exam_id': exam_id,
            'answers': answers,
            'score': score,
            'submitted_at': datetime.utcnow().isoformat()
        }
        
        try:
            # Use RPC to sync response
            results = self.rpc_manager.broadcast('response.sync', params)
            
            successful_nodes = []
            for node_id, response in results.items():
                if response.is_success:
                    successful_nodes.append(node_id)
                    self.logger.info(f"Response synced to {node_id} via RPC")
                else:
                    self.logger.error(f"RPC response.sync failed for {node_id}: {response.error_message}")
            
            return successful_nodes
            
        except Exception as e:
            self.logger.error(f"RPC sync response failed: {e}")
            return []
    
    def record_exam_start(self, exam_id, user_id, node_id):
        """Record exam start event"""
        session_key = f"{exam_id}_{user_id}"
        self.exam_sessions[session_key] = {
            'exam_id': exam_id,
            'user_id': user_id,
            'started_by': node_id,
            'started_at': datetime.utcnow()
        }
        self.logger.info(f"Exam start recorded: {session_key} by {node_id}")
    
    def record_response_sync(self, response_id, node_id):
        """Record response sync event"""
        self.sync_log.append({
            'response_id': response_id,
            'synced_from': node_id,
            'synced_at': datetime.utcnow()
        })
        
        # Keep only last 100 sync events
        if len(self.sync_log) > 100:
            self.sync_log = self.sync_log[-100:]
    
    def full_sync_with_peer(self, peer_node_id):
        """Perform full synchronization with a peer using RPC"""
        if peer_node_id not in self.peers:
            self.logger.error(f"Peer {peer_node_id} not found")
            return False
        
        try:
            # Use RPC to get backup data from peer
            response = self.rpc_manager.call(peer_node_id, 'data.backup')
            
            if response.is_success:
                # Process and sync data
                self._process_sync_data(response.result, peer_node_id)
                return True
            else:
                self.logger.error(f"RPC full sync failed with {peer_node_id}: {response.error_message}")
                return False
                
        except RPCError as e:
            self.logger.error(f"RPC full sync error with {peer_node_id}: {e}")
            return False
    
    def _process_sync_data(self, data, source_node):
        """Process synchronization data from peer node"""
        try:
            # This would integrate with the database models
            # For now, just log the sync
            self.logger.info(f"Received sync data from {source_node}:")
            self.logger.info(f"  - Exams: {len(data.get('exams', []))}")
            self.logger.info(f"  - Questions: {len(data.get('questions', []))}")
            self.logger.info(f"  - Responses: {len(data.get('responses', []))}")
            
            # Store sync log
            self.sync_log.append({
                'source_node': source_node,
                'sync_type': 'full',
                'timestamp': datetime.utcnow(),
                'data_counts': {
                    'exams': len(data.get('exams', [])),
                    'questions': len(data.get('questions', [])),
                    'responses': len(data.get('responses', []))
                }
            })
            
        except Exception as e:
            self.logger.error(f"Error processing sync data: {e}")
    
    def start_heartbeat_thread(self):
        """Start background thread for sending heartbeats"""
        def heartbeat_loop():
            while True:
                try:
                    self.send_heartbeat_to_peers()
                    time.sleep(10)  # Send heartbeat every 10 seconds
                except Exception as e:
                    self.logger.error(f"Heartbeat loop error: {e}")
                    time.sleep(10)
        
        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()
        self.logger.info("Heartbeat thread started")
    
    def start_fault_tolerance(self):
        """Start fault tolerance systems"""
        if not self.fault_tolerance_manager:
            self.logger.error("Fault tolerance manager not initialized")
            return
        
        # Register all peers for fault tolerance monitoring
        for node_id in self.peers:
            if node_id != self.node_id:
                self.fault_tolerance_manager.register_node(node_id)
        
        # Start fault tolerance systems
        self.fault_tolerance_manager.start()
        self.logger.info("Fault tolerance systems started")
    
    def stop_fault_tolerance(self):
        """Stop fault tolerance systems"""
        if self.fault_tolerance_manager:
            self.fault_tolerance_manager.stop()
            self.logger.info("Fault tolerance systems stopped")
    
    def get_node_status(self):
        """Get comprehensive node status"""
        active_nodes = self.get_active_nodes()
        rpc_stats = self.rpc_manager.get_all_stats()
        
        status = {
            'node_id': self.node_id,
            'port': self.port,
            'total_peers': len(self.peers),
            'active_peers': len(active_nodes),
            'active_nodes': active_nodes,
            'exam_sessions': len(self.exam_sessions),
            'sync_operations': len(self.sync_log),
            'rpc_stats': rpc_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add fault tolerance status if available
        if self.fault_tolerance_manager:
            status['fault_tolerance'] = self.fault_tolerance_manager.get_fault_tolerance_status()
        
        return status
    
    def ping_all_nodes(self):
        """Ping all nodes using RPC"""
        results = {}
        
        for node_id in self.peers:
            try:
                response = self.rpc_manager.call(node_id, 'node.ping')
                if response.is_success:
                    results[node_id] = {
                        'status': 'online',
                        'response_time': response.timestamp,
                        'node_id': response.result.get('node_id')
                    }
                    self.logger.info(f"Ping successful to {node_id}")
                else:
                    results[node_id] = {
                        'status': 'error',
                        'error': response.error_message
                    }
                    self.logger.warning(f"Ping failed to {node_id}: {response.error_message}")
                    
            except RPCError as e:
                results[node_id] = {
                    'status': 'offline',
                    'error': str(e)
                }
                self.logger.error(f"Ping error to {node_id}: {e}")
        
        return results
    
    def sync_all_data(self):
        """Sync all data with all nodes using RPC"""
        self.logger.info("Starting full data synchronization with all nodes")
        
        # Get backup data from this node
        try:
            backup_response = self.rpc_manager.clients[self.node_id].call('data.backup') if self.node_id in self.rpc_manager.clients else None
            
            if backup_response and backup_response.is_success:
                backup_data = backup_response.result
                
                # Send backup data to all other nodes
                for node_id in self.peers:
                    if node_id != self.node_id:
                        try:
                            restore_response = self.rpc_manager.call(node_id, 'data.restore', {'backup_data': backup_data})
                            if restore_response.is_success:
                                self.logger.info(f"Data sync successful to {node_id}")
                            else:
                                self.logger.error(f"Data sync failed to {node_id}: {restore_response.error_message}")
                        except RPCError as e:
                            self.logger.error(f"Data sync error to {node_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Data sync failed: {e}")
    
    def get_rpc_stats(self):
        """Get RPC statistics"""
        return self.rpc_manager.get_all_stats()

class DistributedCoordinator:
    """Coordinates distributed operations across nodes"""
    
    def __init__(self, node_manager):
        self.node_manager = node_manager
        self.logger = logging.getLogger(__name__)
    
    def distribute_exam_load(self, exam_id):
        """Distribute exam load across available nodes"""
        active_nodes = self.node_manager.get_active_nodes()
        
        if not active_nodes:
            self.logger.warning("No active nodes available for load distribution")
            return None
        
        # Simple round-robin selection (could be enhanced with actual load metrics)
        selected_node = active_nodes[0]  # For now, select first active node
        
        self.logger.info(f"Exam {exam_id} assigned to node {selected_node['node_id']}")
        return selected_node
    
    def ensure_data_consistency(self):
        """Ensure data consistency across all nodes"""
        active_nodes = self.node_manager.get_active_nodes()
        
        for node in active_nodes:
            if node['node_id'] != self.node_manager.node_id:
                success = self.node_manager.full_sync_with_peer(node['node_id'])
                if success:
                    self.logger.info(f"Sync completed with {node['node_id']}")
                else:
                    self.logger.warning(f"Sync failed with {node['node_id']}")
    
    def handle_node_failure(self, failed_node_id):
        """Handle node failure and redistribute load"""
        self.logger.warning(f"Node failure detected: {failed_node_id}")
        
        # Remove failed node from active peers
        if failed_node_id in self.node_manager.peers:
            self.node_manager.peers[failed_node_id]['status'] = 'failed'
        
        # Redistribute any active exam sessions from failed node
        affected_sessions = [
            session for session in self.node_manager.exam_sessions.values()
            if session.get('started_by') == failed_node_id
        ]
        
        if affected_sessions:
            self.logger.info(f"Redistributing {len(affected_sessions)} affected sessions")
            # Logic to redistribute sessions would go here
