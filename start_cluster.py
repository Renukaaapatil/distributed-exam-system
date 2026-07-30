#!/usr/bin/env python3
"""
Cluster Startup Script for Distributed Exam System
Starts all 3 nodes (A, B, C) simultaneously
"""

import subprocess
import sys
import time
import signal
import os
from threading import Thread

class ClusterManager:
    """Manages the distributed cluster startup and shutdown"""
    
    def __init__(self):
        self.processes = {}
        self.running = True
    
    def start_node(self, node_name, script_path):
        """Start a single node"""
        try:
            print(f"Starting {node_name}...")
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            self.processes[node_name] = process
            
            # Start thread to monitor output
            output_thread = Thread(target=self._monitor_output, args=(node_name, process))
            output_thread.daemon = True
            output_thread.start()
            
            return True
        except Exception as e:
            print(f"Failed to start {node_name}: {e}")
            return False
    
    def _monitor_output(self, node_name, process):
        """Monitor and display node output"""
        try:
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    print(f"[{node_name}] {line.strip()}")
        except Exception as e:
            print(f"Error monitoring {node_name} output: {e}")
    
    def start_all_nodes(self):
        """Start all nodes in the cluster"""
        nodes = [
            ("Node A", "node_a.py"),
            ("Node B", "node_b.py"),
            ("Node C", "node_c.py")
        ]
        
        print("=" * 60)
        print("Starting Distributed Exam System Cluster")
        print("=" * 60)
        
        # Start nodes with slight delays to avoid port conflicts
        for i, (node_name, script) in enumerate(nodes):
            if self.start_node(node_name, script):
                print(f"  {node_name} started successfully")
                if i < len(nodes) - 1:
                    time.sleep(2)  # Delay between starts
            else:
                print(f"  Failed to start {node_name}")
                self.shutdown_all_nodes()
                return False
        
        print("=" * 60)
        print("All nodes started successfully!")
        print("Cluster Status:")
        for node_name, process in self.processes.items():
            status = "Running" if process.poll() is None else "Stopped"
            print(f"  {node_name}: {status}")
        print("=" * 60)
        print("Access URLs:")
        print("  Node A: http://127.0.0.1:5001")
        print("  Node B: http://127.0.0.1:5002")
        print("  Node C: http://127.0.0.1:5003")
        print("=" * 60)
        print("Press Ctrl+C to shutdown the cluster")
        print()
        
        return True
    
    def shutdown_all_nodes(self):
        """Shutdown all nodes"""
        print("\nShutting down cluster...")
        
        for node_name, process in self.processes.items():
            try:
                print(f"Stopping {node_name}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                    print(f"  {node_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"  {node_name} didn't stop gracefully, killing...")
                    process.kill()
                    process.wait()
                    print(f"  {node_name} killed")
                    
            except Exception as e:
                print(f"Error stopping {node_name}: {e}")
        
        print("Cluster shutdown complete.")
    
    def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        try:
            while self.running:
                # Check if any process has died
                for node_name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        print(f"\nWarning: {node_name} has stopped unexpectedly!")
                        self.running = False
                        break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nReceived interrupt signal...")
        finally:
            self.shutdown_all_nodes()

def check_dependencies():
    """Check if all required files exist"""
    required_files = [
        'node_a.py',
        'node_b.py', 
        'node_c.py',
        'app/__init__.py',
        'app/routes.py',
        'app/distributed_routes.py',
        'core/node_manager.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("Error: Missing required files:")
        for file_path in missing_files:
            print(f"  {file_path}")
        print("\nPlease ensure all files are present before starting the cluster.")
        return False
    
    return True

def main():
    """Main function"""
    print("Distributed Exam System - Cluster Manager")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create cluster manager
    cluster = ClusterManager()
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}")
        cluster.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start all nodes
    if cluster.start_all_nodes():
        # Wait for shutdown
        cluster.wait_for_shutdown()
    else:
        print("Failed to start cluster")
        sys.exit(1)

if __name__ == '__main__':
    main()
