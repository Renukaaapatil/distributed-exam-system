"""
Fault Tolerance System for Distributed Exam System
Handles node failures, session recovery, and automatic failover
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask import current_app
from app.session_service import session_service

logger = logging.getLogger(__name__)

class FaultToleranceManager:
    """Manages fault tolerance for distributed exam system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.nodes = {
            'A': {'url': 'http://127.0.0.1:5001', 'status': 'unknown', 'last_check': None, 'failures': 0},
            'B': {'url': 'http://127.0.0.1:5002', 'status': 'unknown', 'last_check': None, 'failures': 0},
            'C': {'url': 'http://127.0.0.1:5003', 'status': 'unknown', 'last_check': None, 'failures': 0}
        }
        self.health_check_interval = 10  # seconds
        self.max_failures = 3  # Max failures before marking node as down
        self.session_migration_enabled = True
        self._health_check_thread = None
        self._running = False
    
    def start_health_monitoring(self):
        """Start background health monitoring"""
        if self._running:
            return
        
        self._running = True
        self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_check_thread.start()
        self.logger.info("Health monitoring started")
    
    def stop_health_monitoring(self):
        """Stop background health monitoring"""
        self._running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
        self.logger.info("Health monitoring stopped")
    
    def _health_check_loop(self):
        """Background health check loop"""
        while self._running:
            try:
                self.check_all_nodes_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
    
    def check_node_health(self, node_id: str) -> bool:
        """
        Check health of a specific node
        
        Args:
            node_id: Node ID to check
            
        Returns:
            True if node is healthy, False otherwise
        """
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        url = node['url']
        
        try:
            import requests
            response = requests.get(f"{url}/health", timeout=3)
            
            if response.status_code == 200:
                node['status'] = 'healthy'
                node['last_check'] = datetime.utcnow()
                node['failures'] = max(0, node['failures'] - 1)  # Decrement failures on success
                
                self.logger.debug(f"Node {node_id} is healthy")
                return True
            else:
                node['failures'] += 1
                self.logger.warning(f"Node {node_id} returned status {response.status_code}")
                
        except Exception as e:
            node['failures'] += 1
            self.logger.warning(f"Health check failed for Node {node_id}: {e}")
        
        node['last_check'] = datetime.utcnow()
        
        # Mark node as down if too many failures
        if node['failures'] >= self.max_failures:
            if node['status'] != 'down':
                node['status'] = 'down'
                self.logger.error(f"Node {node_id} marked as DOWN after {node['failures']} failures")
                self._handle_node_failure(node_id)
        
        return False
    
    def check_all_nodes_health(self) -> Dict[str, bool]:
        """
        Check health of all nodes
        
        Returns:
            Dictionary of node health status
        """
        results = {}
        
        for node_id in self.nodes:
            results[node_id] = self.check_node_health(node_id)
        
        return results
    
    def _handle_node_failure(self, failed_node_id: str):
        """
        Handle node failure by migrating sessions
        
        Args:
            failed_node_id: ID of the failed node
        """
        if not self.session_migration_enabled:
            self.logger.warning("Session migration disabled, not handling node failure")
            return
        
        try:
            # Get active sessions on failed node
            sessions = session_service.get_active_sessions(failed_node_id)
            
            if not sessions:
                self.logger.info(f"No active sessions on failed Node {failed_node_id}")
                return
            
            self.logger.warning(f"Migrating {len(sessions)} sessions from failed Node {failed_node_id}")
            
            # Find healthy nodes
            healthy_nodes = self.get_healthy_nodes()
            
            if not healthy_nodes:
                self.logger.error("No healthy nodes available for session migration!")
                return
            
            # Migrate sessions
            migrated_count = 0
            for session in sessions:
                target_node = self._select_target_node(healthy_nodes)
                if target_node:
                    success = self._migrate_session(session['session_id'], failed_node_id, target_node)
                    if success:
                        migrated_count += 1
            
            self.logger.info(f"Successfully migrated {migrated_count}/{len(sessions)} sessions from Node {failed_node_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle node failure: {e}")
    
    def _migrate_session(self, session_id: str, from_node: str, to_node: str) -> bool:
        """
        Migrate a session to another node
        
        Args:
            session_id: Session ID to migrate
            from_node: Source node ID
            to_node: Target node ID
            
        Returns:
            True if migration successful, False otherwise
        """
        try:
            # Update session node in database
            result = session_service.update_node(session_id, to_node)
            
            if 'error' in result:
                self.logger.error(f"Failed to update session node: {result['error']}")
                return False
            
            # Notify target node about incoming session
            success = self._notify_target_node(to_node, session_id)
            
            if success:
                self.logger.info(f"Successfully migrated session {session_id} from Node {from_node} to Node {to_node}")
                return True
            else:
                self.logger.error(f"Failed to notify target Node {to_node} about session migration")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to migrate session {session_id}: {e}")
            return False
    
    def _notify_target_node(self, target_node: str, session_id: str) -> bool:
        """
        Notify target node about incoming session
        
        Args:
            target_node: Target node ID
            session_id: Session ID
            
        Returns:
            True if notification successful, False otherwise
        """
        try:
            import requests
            
            url = self.nodes[target_node]['url']
            data = {
                'session_id': session_id,
                'migration': True
            }
            
            response = requests.post(f"{url}/session_migration", json=data, timeout=5)
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Failed to notify target node {target_node}: {e}")
            return False
    
    def _select_target_node(self, healthy_nodes: List[str]) -> Optional[str]:
        """
        Select best target node for migration
        
        Args:
            healthy_nodes: List of healthy node IDs
            
        Returns:
            Selected node ID or None
        """
        if not healthy_nodes:
            return None
        
        # Simple round-robin selection (could be enhanced with load-based selection)
        # For now, select the node with the fewest active sessions
        node_loads = {}
        
        for node_id in healthy_nodes:
            sessions = session_service.get_active_sessions(node_id)
            node_loads[node_id] = len(sessions)
        
        # Select node with minimum load
        target_node = min(node_loads, key=node_loads.get)
        
        self.logger.info(f"Selected Node {target_node} for migration (load: {node_loads[target_node]})")
        
        return target_node
    
    def get_healthy_nodes(self) -> List[str]:
        """
        Get list of healthy nodes
        
        Returns:
            List of healthy node IDs
        """
        healthy_nodes = []
        
        for node_id, node_info in self.nodes.items():
            if node_info['status'] == 'healthy':
                healthy_nodes.append(node_id)
        
        return healthy_nodes
    
    def get_node_status(self) -> Dict:
        """
        Get status of all nodes
        
        Returns:
            Dictionary with node status information
        """
        return {
            node_id: {
                'url': info['url'],
                'status': info['status'],
                'last_check': info['last_check'].isoformat() if info['last_check'] else None,
                'failures': info['failures']
            }
            for node_id, info in self.nodes.items()
        }
    
    def is_node_healthy(self, node_id: str) -> bool:
        """
        Check if a specific node is healthy
        
        Args:
            node_id: Node ID to check
            
        Returns:
            True if node is healthy, False otherwise
        """
        if node_id not in self.nodes:
            return False
        
        return self.nodes[node_id]['status'] == 'healthy'
    
    def get_best_node(self) -> Optional[str]:
        """
        Get the best available node for new sessions
        
        Returns:
            Best node ID or None
        """
        healthy_nodes = self.get_healthy_nodes()
        
        if not healthy_nodes:
            return None
        
        # Select node with minimum load
        node_loads = {}
        
        for node_id in healthy_nodes:
            sessions = session_service.get_active_sessions(node_id)
            node_loads[node_id] = len(sessions)
        
        return min(node_loads, key=node_loads.get)
    
    def enable_session_migration(self, enabled: bool = True):
        """Enable or disable session migration"""
        self.session_migration_enabled = enabled
        self.logger.info(f"Session migration {'enabled' if enabled else 'disabled'}")
    
    def set_health_check_interval(self, interval: int):
        """Set health check interval in seconds"""
        self.health_check_interval = max(1, interval)
        self.logger.info(f"Health check interval set to {self.health_check_interval} seconds")
    
    def set_max_failures(self, max_failures: int):
        """Set maximum failures before marking node as down"""
        self.max_failures = max(1, max_failures)
        self.logger.info(f"Max failures set to {self.max_failures}")

# Global fault tolerance manager instance
fault_tolerance_manager = FaultToleranceManager()
