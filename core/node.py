import socket
import json
import threading
import time
from datetime import datetime

class Node:
    """
    A simple node class for distributed exam system.
    This can be extended for clustering and load balancing.
    """
    
    def __init__(self, node_id, host='localhost', port=5000):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers = []
        self.active = True
        self.last_heartbeat = datetime.utcnow()
        
    def start_server(self):
        """Start the node server to handle peer connections"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            print(f"Node {self.node_id} listening on {self.host}:{self.port}")
            
            while self.active:
                try:
                    client_socket, addr = server_socket.accept()
                    threading.Thread(target=self.handle_client, args=(client_socket, addr)).start()
                except Exception as e:
                    print("ERROR:", e)
                    break
                    
        except Exception as e:
            print(f"Error starting server for node {self.node_id}: {e}")
        finally:
            server_socket.close()
    
    def handle_client(self, client_socket, addr):
        """Handle incoming connections from peers"""
        try:
            data = client_socket.recv(4096).decode('utf-8')
            if data:
                message = json.loads(data)
                self.process_message(message, addr)
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()
    
    def process_message(self, message, addr):
        """Process incoming messages from peers"""
        message_type = message.get('type')
        
        if message_type == 'heartbeat':
            self.update_heartbeat(message.get('node_id'))
        elif message_type == 'exam_submission':
            self.handle_exam_submission(message.get('data'))
        elif message_type == 'sync_request':
            self.handle_sync_request(message.get('data'))
        
        print(f"Node {self.node_id} received {message_type} from {addr}")
    
    def send_message(self, peer_host, peer_port, message):
        """Send message to a peer node"""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect((peer_host, peer_port))
            
            message_data = json.dumps(message).encode('utf-8')
            client_socket.send(message_data)
            client_socket.close()
            
            return True
        except Exception as e:
            print(f"Error sending message to {peer_host}:{peer_port}: {e}")
            return False
    
    def add_peer(self, peer_host, peer_port):
        """Add a peer node to the network"""
        peer_info = {
            'host': peer_host,
            'port': peer_port,
            'last_seen': datetime.utcnow(),
            'active': True
        }
        self.peers.append(peer_info)
        print(f"Added peer {peer_host}:{peer_port} to node {self.node_id}")
    
    def send_heartbeat(self):
        """Send heartbeat to all peers"""
        message = {
            'type': 'heartbeat',
            'node_id': self.node_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for peer in self.peers:
            if peer['active']:
                self.send_message(peer['host'], peer['port'], message)
    
    def update_heartbeat(self, peer_node_id):
        """Update heartbeat timestamp for a peer"""
        for peer in self.peers:
            if peer.get('node_id') == peer_node_id:
                peer['last_seen'] = datetime.utcnow()
                peer['active'] = True
                break
    
    def handle_exam_submission(self, exam_data):
        """Handle exam submission from another node"""
        # This can be extended to sync exam data across nodes
        print(f"Node {self.node_id} received exam submission: {exam_data}")
    
    def handle_sync_request(self, sync_data):
        """Handle synchronization request from another node"""
        # This can be extended to sync database state
        print(f"Node {self.node_id} received sync request: {sync_data}")
    
    def start_heartbeat_thread(self):
        """Start a thread to send periodic heartbeats"""
        def heartbeat_loop():
            while self.active:
                self.send_heartbeat()
                time.sleep(10)  # Send heartbeat every 10 seconds
        
        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
    
    def stop(self):
        """Stop the node"""
        self.active = False
        print(f"Node {self.node_id} stopped")

class NodeCluster:
    """
    A cluster manager for multiple nodes in the distributed exam system
    """
    
    def __init__(self):
        self.nodes = []
        self.load_balancer_index = 0
    
    def add_node(self, node):
        """Add a node to the cluster"""
        self.nodes.append(node)
        print(f"Added node {node.node_id} to cluster")
    
    def get_least_loaded_node(self):
        """Simple round-robin load balancing"""
        if not self.nodes:
            return None
        
        node = self.nodes[self.load_balancer_index]
        self.load_balancer_index = (self.load_balancer_index + 1) % len(self.nodes)
        return node
    
    def broadcast_message(self, message):
        """Broadcast message to all nodes in the cluster"""
        for node in self.nodes:
            for peer in node.peers:
                node.send_message(peer['host'], peer['port'], message)
    
    def sync_exam_data(self, exam_data):
        """Sync exam data across all nodes"""
        message = {
            'type': 'exam_submission',
            'data': exam_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.broadcast_message(message)
