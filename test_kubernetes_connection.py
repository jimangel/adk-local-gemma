#!/usr/bin/env python3
"""
Test script to diagnose and fix Kubernetes connection issues.
"""

import os
import sys
from pathlib import Path

def test_kubernetes_connection():
    """Test Kubernetes connection and provide diagnostics."""
    
    print("=" * 60)
    print("Kubernetes Connection Test")
    print("=" * 60)
    print()
    
    # 1. Check environment variables
    print("1. Checking environment variables...")
    kubeconfig_env = os.environ.get('KUBECONFIG')
    if kubeconfig_env:
        print(f"   KUBECONFIG is set to: {kubeconfig_env}")
        # Check if file exists
        for path in kubeconfig_env.split(':'):
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                print(f"   ✓ Config file exists: {expanded_path}")
            else:
                print(f"   ✗ Config file NOT found: {expanded_path}")
    else:
        print("   KUBECONFIG is NOT set")
    print()
    
    # 2. Check common kubeconfig locations
    print("2. Checking common kubeconfig locations...")
    config_locations = [
        "~/.kube/config",
        "~/kubespray/inventory/onemachine/artifacts/admin.conf",
        "${HOME}/kubespray/inventory/onemachine/artifacts/admin.conf"
    ]
    
    found_configs = []
    for location in config_locations:
        expanded = os.path.expanduser(os.path.expandvars(location))
        if os.path.exists(expanded):
            print(f"   ✓ Found: {expanded}")
            found_configs.append(expanded)
        else:
            print(f"   ✗ Not found: {expanded}")
    print()
    
    # 3. Try to load Kubernetes config
    print("3. Attempting to load Kubernetes configuration...")
    try:
        from kubernetes import client, config
        
        # Try different config sources
        config_loaded = False
        
        # Try KUBECONFIG env first
        if kubeconfig_env and not config_loaded:
            for path in kubeconfig_env.split(':'):
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    try:
                        config.load_kube_config(config_file=expanded_path)
                        print(f"   ✓ Successfully loaded config from: {expanded_path}")
                        config_loaded = True
                        break
                    except Exception as e:
                        print(f"   ✗ Failed to load {expanded_path}: {e}")
        
        # Try found configs
        if not config_loaded:
            for config_path in found_configs:
                try:
                    config.load_kube_config(config_file=config_path)
                    print(f"   ✓ Successfully loaded config from: {config_path}")
                    config_loaded = True
                    break
                except Exception as e:
                    print(f"   ✗ Failed to load {config_path}: {e}")
        
        # Try default location
        if not config_loaded:
            try:
                config.load_kube_config()
                print("   ✓ Successfully loaded config from default location")
                config_loaded = True
            except Exception as e:
                print(f"   ✗ Failed to load default config: {e}")
        
        if not config_loaded:
            print("   ✗ Could not load any Kubernetes configuration!")
            print()
            print("SOLUTION:")
            print("-" * 40)
            if found_configs:
                print(f"Set the KUBECONFIG environment variable:")
                print(f"  export KUBECONFIG={found_configs[0]}")
            else:
                print("No kubeconfig files found. Please ensure you have a valid kubeconfig.")
            return False
            
    except ImportError as e:
        print(f"   ✗ Error importing kubernetes module: {e}")
        print("   Please install: pip install kubernetes")
        return False
    print()
    
    # 4. Test API connection
    print("4. Testing Kubernetes API connection...")
    try:
        v1 = client.CoreV1Api()
        
        # Try to list namespaces (lightweight operation)
        namespaces = v1.list_namespace(timeout_seconds=5)
        print(f"   ✓ Successfully connected to Kubernetes API")
        print(f"   ✓ Found {len(namespaces.items)} namespaces")
        
        # Show first few namespaces
        print("   Namespaces:")
        for ns in namespaces.items[:5]:
            print(f"     - {ns.metadata.name}")
        if len(namespaces.items) > 5:
            print(f"     ... and {len(namespaces.items) - 5} more")
            
    except Exception as e:
        print(f"   ✗ Failed to connect to Kubernetes API: {e}")
        print()
        print("TROUBLESHOOTING:")
        print("-" * 40)
        print("1. Check if your Kubernetes cluster is running")
        print("2. Verify the kubeconfig has correct server address")
        print("3. Check network connectivity to the cluster")
        return False
    print()
    
    # 5. Test with ADK agent
    print("5. Testing ADK agent import...")
    try:
        # Set KUBECONFIG if we found a working config
        if config_loaded and found_configs:
            os.environ['KUBECONFIG'] = found_configs[0]
            print(f"   Set KUBECONFIG={found_configs[0]}")
        
        from kubernetes_agent.agent import root_agent, get_pods
        
        if root_agent:
            print("   ✓ ADK agent created successfully")
        else:
            print("   ✗ ADK agent not created (check ADK installation)")
            
        # Test get_pods function
        print("   Testing get_pods function...")
        result = get_pods(namespace="kube-system")
        if result.get("status") == "success":
            print(f"   ✓ get_pods works! Found {result.get('pod_count', 0)} pods in kube-system")
        else:
            print(f"   ✗ get_pods failed: {result.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ✗ Error with ADK agent: {e}")
    print()
    
    print("=" * 60)
    print("Test Complete")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    # Set KUBECONFIG if provided as argument
    if len(sys.argv) > 1:
        os.environ['KUBECONFIG'] = sys.argv[1]
        print(f"Using KUBECONFIG from argument: {sys.argv[1]}")
    
    success = test_kubernetes_connection()
    sys.exit(0 if success else 1)
