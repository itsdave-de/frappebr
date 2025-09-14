#!/usr/bin/env python3
"""Test finding bench command on remote server"""

import sys
from pathlib import Path

# Add the parent directory to Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from frappebr.core.ssh_manager import SSHManager

def test_bench_command():
    print("=== Bench Command Discovery ===")
    
    ssh_manager = SSHManager()
    hostname = "qm.baecktrade.de"
    
    # Test different ways to find bench
    commands = [
        "which bench",
        "whereis bench", 
        "find /usr/local/bin -name bench 2>/dev/null",
        "find /home/itsdave -name bench 2>/dev/null",
        "ls -la /home/itsdave/frappe-15/env/bin/ | grep bench",
        "source /home/itsdave/frappe-15/env/bin/activate && which bench",
        "cd /home/itsdave/frappe-15 && ./env/bin/python -m bench --version",
        "cd /home/itsdave/frappe-15 && ls -la env/bin/bench*"
    ]
    
    for cmd in commands:
        try:
            print(f"\nTesting: {cmd}")
            exit_code, stdout, stderr = ssh_manager.execute_command(hostname, cmd)
            print(f"Exit code: {exit_code}")
            if stdout:
                print(f"Output: {stdout}")
            if stderr and stderr.strip():
                print(f"Error: {stderr}")
        except Exception as e:
            print(f"Command failed: {e}")
    
    ssh_manager.disconnect_all()

if __name__ == "__main__":
    test_bench_command()