"""
Fault Tolerance System for Distributed Exam System
Implements heartbeat checks, leader election, and automatic failover
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set
from core.rpc_client import RPCManager, RPCError

class NodeState(Enum):
    """Node states in the distributed system"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    RECOVERING = "recovering"

class LeaderState(Enum):
    """Leader election states"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"

class FailureLogger:
    """Handles comprehensive failure logging"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.logger = logging.getLogger(f"{__name__}.FailureLogger.{node_id}")
        self.failure_log = []  # Store recent failures
        self.max_log_size = 1000
    
    def log_heartbeat_failure(self, failed_node_id: str, reason: str):
        """Log heartbeat failure"""
        timestamp = datetime.utcnow()
        failure_entry = {
            'timestamp': timestamp.isoformat(),
            'type': 'heartbeat_failure',
            'failed_node': failed_node_id,
            'detected_by': self.node_id,
            'reason': reason,
            'severity': 'warning'
        }
        
        self._add_failure_entry(failure_entry)
        self.logger.warning(f"Heartbeat failure detected: {failed_node_id} - {reason}")
    
    def log_node_failure(self, failed_node_id: str, reason: str):
        """Log node failure"""
        timestamp = datetime.utcnow()
        failure_entry = {
            'timestamp': timestamp.isoformat(),
            'type': 'node_failure',
            'failed_node': failed_node_id,
            'detected_by': self.node_id,
            'reason': reason,
            'severity': 'critical'
        }
        
        self._add_failure_entry(failure_entry)
        self.logger.critical(f"Node failure detected: {failed_node_id} - {reason}")
    
    def log_leader_election(self, election_type: str, candidate_id: str, result: str):
        """Log leader election event"""
        timestamp = datetime.utcnow()
        election_entry = {
            'timestamp': timestamp.isoformat(),
            'type': 'leader_election',
            'candidate': candidate_id,
            'result': result,
            'detected_by': self.node_id,
            'election_type': election_type,
            'severity': 'info'
        }
        
        self._add_failure_entry(election_entry)
        self.logger.info(f"Leader election: {election_type} - {candidate_id} - {result}")
    
    def log_failover(self, failed_leader: str, new_leader: str):
        """Log failover event"""
        timestamp = datetime.utcnow()
        failover_entry = {
            'timestamp': timestamp.isoformat(),
            'type': 'failover',
            'failed_leader': failed_leader,
            'new_leader': new_leader,
            'detected_by': self.node_id,
            'severity': 'critical'
        }
        
        self._add_failure_entry(failover_entry)
        self.logger.critical(f"Failover: {failed_leader} -> {new_leader}")
    
    def log_recovery(self, recovered_node: str, recovery_type: str):
        """Log node recovery"""
        timestamp = datetime.utcnow()
        recovery_entry = {
            'timestamp': timestamp.isoformat(),
            'type': 'node_recovery',
            'recovered_node': recovered_node,
            'recovery_type': recovery_type,
            'detected_by': self.node_id,
            'severity': 'info'
        }
        
        self._add_failure_entry(recovery_entry)
        self.logger.info(f"Node recovery: {recovered_node} - {recovery_type}")
    
    def _add_failure_entry(self, entry: dict):
        """Add entry to failure log"""
        self.failure_log.append(entry)
        
        # Keep log size manageable
        if len(self.failure_log) > self.max_log_size:
            self.failure_log = self.failure_log[-self.max_log_size:]
    
    def get_recent_failures(self, hours: int = 24) -> List[dict]:
        """Get recent failures within specified hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_failures = []
        for entry in self.failure_log:
            entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            if entry_time > cutoff_time:
                recent_failures.append(entry)
        
        return recent_failures
    
    def get_failure_summary(self) -> dict:
        """Get summary of failures by type"""
        summary = {
            'total_failures': len(self.failure_log),
            'by_type': {},
            'by_severity': {},
            'by_node': {}
        }
        
        for entry in self.failure_log:
            # Count by type
            failure_type = entry['type']
            summary['by_type'][failure_type] = summary['by_type'].get(failure_type, 0) + 1
            
            # Count by severity
            severity = entry['severity']
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            
            # Count by failed node
            if 'failed_node' in entry:
                failed_node = entry['failed_node']
                summary['by_node'][failed_node] = summary['by_node'].get(failed_node, 0) + 1
        
        return summary

class HeartbeatMonitor:
    """Monitors heartbeat between nodes"""
    
    def __init__(self, node_id: str, rpc_manager: RPCManager, failure_logger: FailureLogger):
        self.node_id = node_id
        self.rpc_manager = rpc_manager
        self.failure_logger = failure_logger
        self.logger = logging.getLogger(f"{__name__}.HeartbeatMonitor.{node_id}")
        
        # Heartbeat configuration
        self.heartbeat_interval = 5  # seconds
        self.heartbeat_timeout = 15  # seconds
        self.max_missed_heartbeats = 3
        
        # Node state tracking
        self.node_states = {}  # {node_id: {'state': NodeState, 'last_heartbeat': datetime, 'missed_count': int}}
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Callbacks for state changes
        self.on_node_failure = None
        self.on_node_recovery = None
    
    def start_monitoring(self):
        """Start heartbeat monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Heartbeat monitoring started")
    
    def stop_monitoring(self):
        """Stop heartbeat monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("Heartbeat monitoring stopped")
    
    def register_node(self, node_id: str):
        """Register a node for monitoring"""
        self.node_states[node_id] = {
            'state': NodeState.INACTIVE,
            'last_heartbeat': None,
            'missed_count': 0
        }
        self.logger.info(f"Registered node {node_id} for heartbeat monitoring")
    
    def unregister_node(self, node_id: str):
        """Unregister a node from monitoring"""
        if node_id in self.node_states:
            del self.node_states[node_id]
            self.logger.info(f"Unregistered node {node_id} from heartbeat monitoring")
    
    def _heartbeat_loop(self):
        """Main heartbeat monitoring loop"""
        while self.monitoring_active:
            try:
                self._check_all_nodes()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(self.heartbeat_interval)
    
    def _check_all_nodes(self):
        """Check heartbeat for all registered nodes"""
        current_time = datetime.utcnow()
        
        for node_id, state_info in list(self.node_states.items()):
            try:
                # Send heartbeat via RPC
                response = self.rpc_manager.call(node_id, 'node.ping', timeout=3)
                
                if response.is_success:
                    # Heartbeat successful
                    self._handle_successful_heartbeat(node_id, current_time)
                else:
                    # Heartbeat failed
                    self._handle_failed_heartbeat(node_id, current_time, f"RPC error: {response.error_message}")
                    
            except RPCError as e:
                # Heartbeat failed
                self._handle_failed_heartbeat(node_id, current_time, f"RPC failure: {str(e)}")
            except Exception as e:
                # Unexpected error
                self._handle_failed_heartbeat(node_id, current_time, f"Unexpected error: {str(e)}")
    
    def _handle_successful_heartbeat(self, node_id: str, timestamp: datetime):
        """Handle successful heartbeat"""
        state_info = self.node_states[node_id]
        
        # Update heartbeat info
        state_info['last_heartbeat'] = timestamp
        state_info['missed_count'] = 0
        
        # Check if node was previously failed
        if state_info['state'] == NodeState.FAILED:
            state_info['state'] = NodeState.RECOVERING
            self.failure_logger.log_recovery(node_id, "heartbeat_recovery")
            
            if self.on_node_recovery:
                self.on_node_recovery(node_id)
        
        # Mark as active if recovering
        if state_info['state'] == NodeState.RECOVERING:
            state_info['state'] = NodeState.ACTIVE
            self.logger.info(f"Node {node_id} fully recovered and active")
        elif state_info['state'] != NodeState.ACTIVE:
            state_info['state'] = NodeState.ACTIVE
            self.logger.info(f"Node {node_id} is now active")
    
    def _handle_failed_heartbeat(self, node_id: str, timestamp: datetime, reason: str):
        """Handle failed heartbeat"""
        state_info = self.node_states[node_id]
        
        # Increment missed count
        state_info['missed_count'] += 1
        
        # Log heartbeat failure
        self.failure_logger.log_heartbeat_failure(node_id, reason)
        
        # Check if node should be marked as failed
        if state_info['missed_count'] >= self.max_missed_heartbeats:
            if state_info['state'] != NodeState.FAILED:
                # Mark as failed
                state_info['state'] = NodeState.FAILED
                self.failure_logger.log_node_failure(node_id, f"Missed {state_info['missed_count']} heartbeats")
                
                self.logger.critical(f"Node {node_id} marked as FAILED after {state_info['missed_count']} missed heartbeats")
                
                if self.on_node_failure:
                    self.on_node_failure(node_id)
        else:
            # Mark as inactive
            if state_info['state'] == NodeState.ACTIVE:
                state_info['state'] = NodeState.INACTIVE
                self.logger.warning(f"Node {node_id} marked as INACTIVE (missed {state_info['missed_count']} heartbeats)")
    
    def get_node_status(self, node_id: str) -> Optional[dict]:
        """Get status of a specific node"""
        if node_id not in self.node_states:
            return None
        
        state_info = self.node_states[node_id]
        return {
            'node_id': node_id,
            'state': state_info['state'].value,
            'last_heartbeat': state_info['last_heartbeat'].isoformat() if state_info['last_heartbeat'] else None,
            'missed_count': state_info['missed_count']
        }
    
    def get_all_node_status(self) -> List[dict]:
        """Get status of all monitored nodes"""
        return [self.get_node_status(node_id) for node_id in self.node_states]
    
    def get_active_nodes(self) -> List[str]:
        """Get list of active nodes"""
        active_nodes = []
        for node_id, state_info in self.node_states.items():
            if state_info['state'] == NodeState.ACTIVE:
                active_nodes.append(node_id)
        return active_nodes

class BullyLeaderElection:
    """Implements Bully algorithm for leader election"""
    
    def __init__(self, node_id: str, rpc_manager: RPCManager, failure_logger: FailureLogger):
        self.node_id = node_id
        self.rpc_manager = rpc_manager
        self.failure_logger = failure_logger
        self.logger = logging.getLogger(f"{__name__}.BullyLeaderElection.{node_id}")
        
        # Election state
        self.current_leader = None
        self.election_state = LeaderState.FOLLOWER
        self.election_timeout = 10  # seconds
        self.last_election_time = None
        
        # Node priority (higher port number = higher priority)
        self.node_priority = self._extract_priority_from_id(node_id)
        
        # Election tracking
        self.election_in_progress = False
        self.election_votes = set()
        self.election_lock = threading.Lock()
        
        # Callbacks
        self.on_leader_elected = None
        self.on_leader_changed = None
    
    def _extract_priority_from_id(self, node_id: str) -> int:
        """Extract priority from node ID (port number)"""
        try:
            # Extract port number from node_id (e.g., "node_5001" -> 5001)
            return int(node_id.split('_')[1])
        except (IndexError, ValueError):
            return 0
    
    def start_election(self):
        """Start leader election using Bully algorithm"""
        with self.election_lock:
            if self.election_in_progress:
                return
            
            self.election_in_progress = True
            self.election_state = LeaderState.CANDIDATE
            self.election_votes = {self.node_id}  # Vote for self
            self.last_election_time = datetime.utcnow()
            
            self.logger.info(f"Starting leader election as CANDIDATE (priority: {self.node_priority})")
            self.failure_logger.log_leader_election("bully_start", self.node_id, "candidate")
        
        try:
            # Get all nodes with higher priority
            higher_priority_nodes = self._get_higher_priority_nodes()
            
            if not higher_priority_nodes:
                # No higher priority nodes, become leader
                self._become_leader()
                return
            
            # Send election messages to higher priority nodes
            self._send_election_messages(higher_priority_nodes)
            
            # Wait for responses
            self._wait_for_election_responses()
            
        except Exception as e:
            self.logger.error(f"Error during leader election: {e}")
            self._end_election()
    
    def handle_election_message(self, candidate_id: str):
        """Handle election message from another node"""
        with self.election_lock:
            self.logger.info(f"Received election message from {candidate_id}")
            
            # If we have higher priority, respond and start election
            candidate_priority = self._extract_priority_from_id(candidate_id)
            
            if self.node_priority > candidate_priority:
                # Send OK response and start our own election
                self._send_ok_response(candidate_id)
                
                if not self.election_in_progress:
                    self.start_election()
            else:
                # Lower priority node, ignore
                self.logger.debug(f"Ignoring election from lower priority node {candidate_id}")
    
    def handle_ok_message(self, from_node_id: str):
        """Handle OK message during election"""
        with self.election_lock:
            if self.election_in_progress and self.election_state == LeaderState.CANDIDATE:
                self.election_votes.add(from_node_id)
                self.logger.info(f"Received OK from {from_node_id}, votes: {len(self.election_votes)}")
                
                # Check if we have enough votes to become leader
                higher_priority_nodes = self._get_higher_priority_nodes()
                
                # We become leader if we received OK from all higher priority nodes
                # or if no higher priority nodes responded within timeout
                if len(self.election_votes) >= len(higher_priority_nodes) + 1:
                    self._become_leader()
    
    def handle_leader_announcement(self, leader_id: str):
        """Handle leader announcement from new leader"""
        with self.election_lock:
            if leader_id != self.current_leader:
                old_leader = self.current_leader
                self.current_leader = leader_id
                self.election_state = LeaderState.FOLLOWER
                self.election_in_progress = False
                
                self.logger.info(f"New leader elected: {leader_id}")
                self.failure_logger.log_leader_election("bully_announcement", leader_id, "elected")
                
                if old_leader and self.on_leader_changed:
                    self.on_leader_changed(old_leader, leader_id)
                elif not old_leader and self.on_leader_elected:
                    self.on_leader_elected(leader_id)
    
    def _get_higher_priority_nodes(self) -> List[str]:
        """Get list of nodes with higher priority"""
        higher_nodes = []
        
        for node_id in self.rpc_manager.clients:
            if node_id != self.node_id:
                node_priority = self._extract_priority_from_id(node_id)
                if node_priority > self.node_priority:
                    higher_nodes.append(node_id)
        
        return sorted(higher_nodes, key=self._extract_priority_from_id, reverse=True)
    
    def _send_election_messages(self, nodes: List[str]):
        """Send election messages to higher priority nodes"""
        election_message = {
            'type': 'election',
            'candidate_id': self.node_id,
            'priority': self.node_priority,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for node_id in nodes:
            try:
                # Send election message via RPC
                response = self.rpc_manager.call(node_id, 'node.handle_election', election_message, timeout=3)
                if response.is_success:
                    self.logger.debug(f"Election message sent to {node_id}")
                else:
                    self.logger.warning(f"Failed to send election to {node_id}: {response.error_message}")
            except RPCError as e:
                self.logger.warning(f"Failed to send election to {node_id}: {e}")
    
    def _send_ok_response(self, candidate_id: str):
        """Send OK response to election candidate"""
        ok_message = {
            'type': 'ok',
            'from_node_id': self.node_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            response = self.rpc_manager.call(candidate_id, 'node.handle_ok', ok_message, timeout=3)
            if response.is_success:
                self.logger.debug(f"OK response sent to {candidate_id}")
        except RPCError as e:
            self.logger.warning(f"Failed to send OK to {candidate_id}: {e}")
    
    def _wait_for_election_responses(self):
        """Wait for election responses"""
        start_time = time.time()
        
        while time.time() - start_time < self.election_timeout:
            if not self.election_in_progress:
                break
            
            # Check if we have enough votes
            higher_priority_nodes = self._get_higher_priority_nodes()
            
            if len(self.election_votes) >= len(higher_priority_nodes) + 1:
                self._become_leader()
                return
            
            time.sleep(0.5)
        
        # Timeout reached, check if we should become leader
        if self.election_in_progress:
            # Become leader if no higher priority nodes responded
            active_higher_nodes = [n for n in higher_priority_nodes if self._is_node_active(n)]
            
            if not active_higher_nodes:
                self._become_leader()
            else:
                # Higher priority nodes exist, wait for them to elect leader
                self.logger.info("Waiting for higher priority nodes to elect leader")
                self._end_election()
    
    def _become_leader(self):
        """Become the leader"""
        with self.election_lock:
            self.current_leader = self.node_id
            self.election_state = LeaderState.LEADER
            self.election_in_progress = False
            
            self.logger.info(f"Node {self.node_id} became LEADER")
            self.failure_logger.log_leader_election("bully_victory", self.node_id, "leader")
            
            # Announce leadership to all nodes
            self._announce_leadership()
            
            if self.on_leader_elected:
                self.on_leader_elected(self.node_id)
    
    def _announce_leadership(self):
        """Announce leadership to all nodes"""
        announcement = {
            'type': 'leader_announcement',
            'leader_id': self.node_id,
            'priority': self.node_priority,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send to all nodes
        for node_id in self.rpc_manager.clients:
            if node_id != self.node_id:
                try:
                    response = self.rpc_manager.call(node_id, 'node.handle_leader_announcement', announcement, timeout=3)
                    if response.is_success:
                        self.logger.debug(f"Leadership announced to {node_id}")
                except RPCError as e:
                    self.logger.warning(f"Failed to announce leadership to {node_id}: {e}")
    
    def _is_node_active(self, node_id: str) -> bool:
        """Check if a node is active"""
        try:
            response = self.rpc_manager.call(node_id, 'node.ping', timeout=2)
            return response.is_success
        except RPCError:
            return False
    
    def _end_election(self):
        """End current election"""
        with self.election_lock:
            self.election_in_progress = False
            self.election_state = LeaderState.FOLLOWER
            self.election_votes.clear()
    
    def get_leader_info(self) -> dict:
        """Get current leader information"""
        return {
            'current_leader': self.current_leader,
            'node_state': self.election_state.value,
            'node_priority': self.node_priority,
            'election_in_progress': self.election_in_progress,
            'last_election_time': self.last_election_time.isoformat() if self.last_election_time else None
        }

class FaultToleranceManager:
    """Main fault tolerance manager"""
    
    def __init__(self, node_id: str, rpc_manager: RPCManager):
        self.node_id = node_id
        self.rpc_manager = rpc_manager
        self.logger = logging.getLogger(f"{__name__}.FaultToleranceManager.{node_id}")
        
        # Initialize components
        self.failure_logger = FailureLogger(node_id)
        self.heartbeat_monitor = HeartbeatMonitor(node_id, rpc_manager, self.failure_logger)
        self.leader_election = BullyLeaderElection(node_id, rpc_manager, self.failure_logger)
        
        # Set up callbacks
        self.heartbeat_monitor.on_node_failure = self._handle_node_failure
        self.heartbeat_monitor.on_node_recovery = self._handle_node_recovery
        self.leader_election.on_leader_elected = self._on_leader_elected
        self.leader_election.on_leader_changed = self._on_leader_changed
        
        # Data replication
        self.data_replication_enabled = True
        self.replication_interval = 30  # seconds
        self.replication_thread = None
        self.replication_active = False
        
        # Failover state
        self.failover_active = False
        self.failed_nodes = set()
    
    def start(self):
        """Start fault tolerance systems"""
        self.logger.info("Starting fault tolerance manager")
        
        # Start heartbeat monitoring
        self.heartbeat_monitor.start_monitoring()
        
        # Start data replication
        self._start_data_replication()
        
        # Start leader election if needed
        self._initialize_leadership()
    
    def stop(self):
        """Stop fault tolerance systems"""
        self.logger.info("Stopping fault tolerance manager")
        
        # Stop heartbeat monitoring
        self.heartbeat_monitor.stop_monitoring()
        
        # Stop data replication
        self._stop_data_replication()
    
    def register_node(self, node_id: str):
        """Register a node for fault tolerance monitoring"""
        self.heartbeat_monitor.register_node(node_id)
        self.logger.info(f"Registered node {node_id} for fault tolerance")
    
    def _handle_node_failure(self, failed_node_id: str):
        """Handle node failure"""
        self.failed_nodes.add(failed_node_id)
        
        # If failed node was leader, start election
        if self.leader_election.current_leader == failed_node_id:
            self.logger.warning(f"Leader {failed_node_id} failed, starting election")
            self.leader_election.start_election()
        
        # Handle data replication for failed node
        if self.data_replication_enabled:
            self._handle_failed_node_replication(failed_node_id)
    
    def _handle_node_recovery(self, recovered_node_id: str):
        """Handle node recovery"""
        if recovered_node_id in self.failed_nodes:
            self.failed_nodes.remove(recovered_node_id)
        
        # Sync data to recovered node
        if self.data_replication_enabled:
            self._sync_data_to_recovered_node(recovered_node_id)
    
    def _on_leader_elected(self, leader_id: str):
        """Handle leader election"""
        self.logger.info(f"New leader elected: {leader_id}")
        
        # If this node is leader, take on leader responsibilities
        if leader_id == self.node_id:
            self._assume_leadership()
    
    def _on_leader_changed(self, old_leader: str, new_leader: str):
        """Handle leader change"""
        self.failure_logger.log_failover(old_leader, new_leader)
        
        # Handle failover
        if old_leader and new_leader:
            self._handle_failover(old_leader, new_leader)
    
    def _initialize_leadership(self):
        """Initialize leadership state"""
        # Wait a bit for other nodes to start
        time.sleep(5)
        
        # Check if there's already a leader
        active_nodes = self.heartbeat_monitor.get_active_nodes()
        
        if not active_nodes:
            # No other nodes, become leader
            self.leader_election.start_election()
        else:
            # Check if any active node is leader
            for node_id in active_nodes:
                try:
                    response = self.rpc_manager.call(node_id, 'node.get_leader_info', timeout=3)
                    if response.is_success and response.result.get('current_leader'):
                        # Leader exists, become follower
                        self.leader_election.handle_leader_announcement(response.result['current_leader'])
                        return
                except RPCError:
                    continue
            
            # No leader found, start election
            self.leader_election.start_election()
    
    def _assume_leadership(self):
        """Take on leadership responsibilities"""
        self.logger.info(f"Node {self.node_id} assuming leadership responsibilities")
        
        # Leader takes on additional responsibilities
        # (e.g., coordinating data replication, load balancing, etc.)
    
    def _handle_failover(self, failed_leader: str, new_leader: str):
        """Handle failover from failed leader to new leader"""
        self.logger.info(f"Handling failover: {failed_leader} -> {new_leader}")
        
        # Redirect any operations from failed leader to new leader
        # Ensure data consistency during failover
        # Update any client connections
        
        self.failover_active = True
        
        try:
            # Perform failover operations
            self._perform_failover_operations(failed_leader, new_leader)
        finally:
            self.failover_active = False
    
    def _perform_failover_operations(self, failed_leader: str, new_leader: str):
        """Perform specific failover operations"""
        # This would include:
        # - Redirecting client connections
        # - Ensuring data consistency
        # - Updating routing tables
        # - Notifying external systems
        
        self.logger.info(f"Failover operations completed for {failed_leader} -> {new_leader}")
    
    def _start_data_replication(self):
        """Start data replication between nodes"""
        if not self.data_replication_enabled:
            return
        
        self.replication_active = True
        self.replication_thread = threading.Thread(target=self._replication_loop, daemon=True)
        self.replication_thread.start()
        
        self.logger.info("Data replication started")
    
    def _stop_data_replication(self):
        """Stop data replication"""
        self.replication_active = False
        if self.replication_thread:
            self.replication_thread.join(timeout=5)
        
        self.logger.info("Data replication stopped")
    
    def _replication_loop(self):
        """Main data replication loop"""
        while self.replication_active:
            try:
                self._perform_data_replication()
                time.sleep(self.replication_interval)
            except Exception as e:
                self.logger.error(f"Error in data replication: {e}")
                time.sleep(self.replication_interval)
    
    def _perform_data_replication(self):
        """Perform data replication to active nodes"""
        active_nodes = self.heartbeat_monitor.get_active_nodes()
        
        if len(active_nodes) <= 1:
            return  # No replication needed if only this node is active
        
        # Get backup data from this node
        try:
            backup_response = self.rpc_manager.clients[self.node_id].call('data.backup') if self.node_id in self.rpc_manager.clients else None
            
            if backup_response and backup_response.is_success:
                backup_data = backup_response.result
                
                # Replicate to other active nodes
                for node_id in active_nodes:
                    if node_id != self.node_id:
                        try:
                            response = self.rpc_manager.call(node_id, 'data.restore', {'backup_data': backup_data})
                            if response.is_success:
                                self.logger.debug(f"Data replicated to {node_id}")
                            else:
                                self.logger.warning(f"Failed to replicate to {node_id}: {response.error_message}")
                        except RPCError as e:
                            self.logger.warning(f"Failed to replicate to {node_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error during data replication: {e}")
    
    def _handle_failed_node_replication(self, failed_node_id: str):
        """Handle replication when a node fails"""
        self.logger.info(f"Handling replication for failed node: {failed_node_id}")
        
        # Ensure data is replicated to remaining active nodes
        self._perform_data_replication()
    
    def _sync_data_to_recovered_node(self, recovered_node_id: str):
        """Sync data to a recovered node"""
        self.logger.info(f"Syncing data to recovered node: {recovered_node_id}")
        
        try:
            # Get current data and send to recovered node
            backup_response = self.rpc_manager.clients[self.node_id].call('data.backup') if self.node_id in self.rpc_manager.clients else None
            
            if backup_response and backup_response.is_success:
                backup_data = backup_response.result
                
                response = self.rpc_manager.call(recovered_node_id, 'data.restore', {'backup_data': backup_data})
                if response.is_success:
                    self.logger.info(f"Data synced to recovered node {recovered_node_id}")
                else:
                    self.logger.warning(f"Failed to sync to {recovered_node_id}: {response.error_message}")
        
        except RPCError as e:
            self.logger.error(f"Failed to sync data to {recovered_node_id}: {e}")
    
    def get_fault_tolerance_status(self) -> dict:
        """Get comprehensive fault tolerance status"""
        return {
            'node_id': self.node_id,
            'heartbeat_status': {
                'monitoring_active': self.heartbeat_monitor.monitoring_active,
                'monitored_nodes': len(self.heartbeat_monitor.node_states),
                'active_nodes': len(self.heartbeat_monitor.get_active_nodes()),
                'node_states': self.heartbeat_monitor.get_all_node_status()
            },
            'leader_election': self.leader_election.get_leader_info(),
            'data_replication': {
                'enabled': self.data_replication_enabled,
                'active': self.replication_active,
                'interval': self.replication_interval
            },
            'failover': {
                'active': self.failover_active,
                'failed_nodes': list(self.failed_nodes)
            },
            'failure_summary': self.failure_logger.get_failure_summary()
        }
