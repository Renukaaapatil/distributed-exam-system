"""
RPC Client for Distributed Exam System
Handles remote function calls between nodes with retry mechanisms and logging
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List
import uuid

class RPCError(Exception):
    """Custom RPC error class"""
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}

class RPCRequest:
    """RPC Request wrapper"""
    def __init__(self, method: str, params: Dict = None, request_id: str = None):
        self.method = method
        self.params = params or {}
        self.request_id = request_id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self):
        """Convert request to dictionary"""
        return {
            'jsonrpc': '2.0',
            'method': self.method,
            'params': self.params,
            'id': self.request_id,
            'timestamp': self.timestamp
        }

class RPCResponse:
    """RPC Response wrapper"""
    def __init__(self, data: Dict):
        self.jsonrpc = data.get('jsonrpc', '2.0')
        self.result = data.get('result')
        self.error = data.get('error')
        self.id = data.get('id')
        self.timestamp = data.get('timestamp')
    
    @property
    def is_success(self) -> bool:
        """Check if response is successful"""
        return self.error is None and self.result is not None
    
    @property
    def error_message(self) -> str:
        """Get error message if any"""
        if self.error:
            return self.error.get('message', 'Unknown error')
        return None

class RPCClient:
    """RPC Client for making remote function calls"""
    
    def __init__(self, node_id: str, base_url: str, timeout: int = 10, max_retries: int = 3):
        self.node_id = node_id
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"{__name__}.{node_id}")
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_count': 0,
            'total_response_time': 0.0
        }
    
    def call(self, method: str, params: Dict = None, timeout: int = None) -> RPCResponse:
        """
        Make a remote function call with retry mechanism
        
        Args:
            method: Remote method name
            params: Method parameters
            timeout: Request timeout (overrides default)
            
        Returns:
            RPCResponse object
            
        Raises:
            RPCError: If call fails after all retries
        """
        request = RPCRequest(method, params)
        actual_timeout = timeout or self.timeout
        
        self.logger.info(f"RPC Call: {method} to {self.node_id} (ID: {request.request_id})")
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                response = self._make_request(request, actual_timeout)
                end_time = time.time()
                
                # Update statistics
                self.stats['total_requests'] += 1
                self.stats['total_response_time'] += (end_time - start_time)
                
                if response.is_success:
                    self.stats['successful_requests'] += 1
                    self.logger.info(
                        f"RPC Success: {method} from {self.node_id} "
                        f"(ID: {request.request_id}, Time: {end_time - start_time:.3f}s)"
                    )
                    return response
                else:
                    self.logger.warning(
                        f"RPC Error Response: {method} from {self.node_id} "
                        f"(ID: {request.request_id}, Error: {response.error_message})"
                    )
                    raise RPCError(response.error_message, response_data=response.error)
                    
            except requests.exceptions.RequestException as e:
                self.stats['retry_count'] += 1
                wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"RPC Retry: {method} to {self.node_id} failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {wait_time}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    self.stats['failed_requests'] += 1
                    self.logger.error(
                        f"RPC Failed: {method} to {self.node_id} after {self.max_retries + 1} attempts. "
                        f"Final error: {e}"
                    )
                    raise RPCError(f"RPC call failed after {self.max_retries + 1} attempts: {e}")
            
            except RPCError as e:
                self.stats['failed_requests'] += 1
                if attempt < self.max_retries:
                    wait_time = min(2 ** attempt, 10)
                    self.logger.warning(
                        f"RPC Retry: {method} to {self.node_id} failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {wait_time}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(
                        f"RPC Failed: {method} to {self.node_id} after {self.max_retries + 1} attempts. "
                        f"Final error: {e}"
                    )
                    raise e
        
        # This should never be reached
        raise RPCError("Unexpected error in RPC call")
    
    def call_async(self, method: str, params: Dict = None, timeout: int = None) -> RPCResponse:
        """
        Make an asynchronous RPC call (fire and forget)
        
        Args:
            method: Remote method name
            params: Method parameters
            timeout: Request timeout
        """
        request = RPCRequest(method, params)
        actual_timeout = timeout or self.timeout
        
        self.logger.info(f"RPC Async Call: {method} to {self.node_id} (ID: {request.request_id})")
        
        try:
            response = self._make_request(request, actual_timeout)
            self.stats['total_requests'] += 1
            
            if response.is_success:
                self.stats['successful_requests'] += 1
                self.logger.info(f"RPC Async Success: {method} from {self.node_id}")
            else:
                self.stats['failed_requests'] += 1
                self.logger.warning(f"RPC Async Error: {method} from {self.node_id}: {response.error_message}")
                
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"RPC Async Failed: {method} to {self.node_id}: {e}")
    
    def _make_request(self, request: RPCRequest, timeout: int) -> RPCResponse:
        """Make HTTP request to remote node"""
        headers = {
            'Content-Type': 'application/json',
            'X-RPC-Node-ID': self.node_id,
            'X-RPC-Request-ID': request.request_id
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/rpc/call",
                json=request.to_dict(),
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return RPCResponse(response.json())
            else:
                raise RPCError(f"HTTP {response.status_code}: {response.text}", status_code=response.status_code)
                
        except requests.exceptions.Timeout:
            raise RPCError(f"Request timeout after {timeout}s")
        except requests.exceptions.ConnectionError:
            raise RPCError("Connection error")
        except requests.exceptions.RequestException as e:
            raise RPCError(f"Request error: {e}")
    
    def get_stats(self) -> Dict:
        """Get RPC client statistics"""
        avg_response_time = (
            self.stats['total_response_time'] / self.stats['total_requests']
            if self.stats['total_requests'] > 0 else 0
        )
        
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_requests'] / self.stats['total_requests']
                if self.stats['total_requests'] > 0 else 0
            ),
            'avg_response_time': avg_response_time
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retry_count': 0,
            'total_response_time': 0.0
        }

class RPCManager:
    """Manages multiple RPC clients for different nodes"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.clients = {}  # {target_node_id: RPCClient}
        self.logger = logging.getLogger(f"{__name__}.RPCManager.{node_id}")
    
    def add_client(self, target_node_id: str, base_url: str, **kwargs):
        """Add RPC client for a target node"""
        client = RPCClient(target_node_id, base_url, **kwargs)
        self.clients[target_node_id] = client
        self.logger.info(f"Added RPC client for {target_node_id} at {base_url}")
    
    def call(self, target_node_id: str, method: str, params: Dict = None, **kwargs) -> RPCResponse:
        """Make RPC call to specific node"""
        if target_node_id not in self.clients:
            raise RPCError(f"No RPC client configured for node {target_node_id}")
        
        return self.clients[target_node_id].call(method, params, **kwargs)
    
    def broadcast(self, method: str, params: Dict = None, **kwargs) -> Dict[str, RPCResponse]:
        """Broadcast RPC call to all nodes"""
        results = {}
        
        for node_id, client in self.clients.items():
            try:
                response = client.call(method, params, **kwargs)
                results[node_id] = response
            except RPCError as e:
                # Create error response for failed calls
                error_response = RPCResponse({
                    'jsonrpc': '2.0',
                    'error': {'message': str(e)},
                    'id': None
                })
                results[node_id] = error_response
        
        return results
    
    def broadcast_async(self, method: str, params: Dict = None, **kwargs):
        """Broadcast async RPC call to all nodes"""
        for node_id, client in self.clients.items():
            try:
                client.call_async(method, params, **kwargs)
            except Exception as e:
                self.logger.error(f"Async broadcast failed to {node_id}: {e}")
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all clients"""
        return {node_id: client.get_stats() for node_id, client in self.clients.items()}
    
    def reset_all_stats(self):
        """Reset statistics for all clients"""
        for client in self.clients.values():
            client.reset_stats()
