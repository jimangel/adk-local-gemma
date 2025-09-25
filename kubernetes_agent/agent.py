"""
Kubernetes ADK Agent
A basic ADK agent that can interact with Kubernetes clusters using either
kubeconfig or service account authentication.

Supports both cloud LLMs (Gemini) and local LLMs (LM Studio).
"""

import os
import json
from typing import Dict, List, Optional, Any
from google.adk.agents import Agent
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from dotenv import load_dotenv

# Try to import LiteLlm for local model support
try:
    from google.adk.models.lite_llm import LiteLlm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    print("Warning: LiteLlm not available. Local LLM support disabled.")
    print("To enable local LLM support, ensure you have the latest google-adk version.")

# Load environment variables from .env file
load_dotenv()


def load_kubernetes_config(kubeconfig_path: Optional[str] = None) -> str:
    """
    Load Kubernetes configuration from kubeconfig file or service account.
    
    Args:
        kubeconfig_path: Optional path to kubeconfig file. If not provided,
                        will try to use KUBECONFIG env var or in-cluster config.
    
    Returns:
        str: Status message indicating which config was loaded
    """
    try:
        if kubeconfig_path and os.path.exists(kubeconfig_path):
            # Load from specified kubeconfig file
            config.load_kube_config(config_file=kubeconfig_path)
            return f"Loaded kubeconfig from: {kubeconfig_path}"
        elif os.environ.get('KUBECONFIG'):
            # Load from KUBECONFIG environment variable
            kubeconfig_env = os.environ.get('KUBECONFIG')
            config.load_kube_config(config_file=kubeconfig_env)
            return f"Loaded kubeconfig from KUBECONFIG env var: {kubeconfig_env}"
        else:
            # Try to load in-cluster config (for running inside a pod)
            config.load_incluster_config()
            return "Loaded in-cluster config (running inside Kubernetes)"
    except config.ConfigException as e:
        # Fallback to default kubeconfig location
        try:
            config.load_kube_config()
            return "Loaded kubeconfig from default location (~/.kube/config)"
        except Exception as fallback_error:
            return f"Failed to load any Kubernetes config: {str(e)}, {str(fallback_error)}"


def get_pods(namespace: str = "all", label_selector: Optional[str] = None) -> Dict[str, Any]:
    """
    List pods in the Kubernetes cluster.
    
    Args:
        namespace: The namespace to list pods from. Use "all" for all namespaces.
        label_selector: Optional label selector to filter pods (e.g., "app=nginx")
    
    Returns:
        dict: Status and list of pods with their details
    """
    try:
        # Load config
        config_status = load_kubernetes_config()
        
        # Create API client
        v1 = client.CoreV1Api()
        
        # List pods
        if namespace.lower() == "all":
            pods = v1.list_pod_for_all_namespaces(
                watch=False,
                label_selector=label_selector
            )
        else:
            pods = v1.list_namespaced_pod(
                namespace=namespace,
                watch=False,
                label_selector=label_selector
            )
        
        # Format pod information
        pod_list = []
        for pod in pods.items:
            pod_info = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "pod_ip": pod.status.pod_ip,
                "node": pod.spec.node_name,
                "containers": len(pod.spec.containers),
                "labels": pod.metadata.labels or {}
            }
            
            # Add container statuses
            if pod.status.container_statuses:
                pod_info["container_statuses"] = [
                    {
                        "name": cs.name,
                        "ready": cs.ready,
                        "restart_count": cs.restart_count
                    }
                    for cs in pod.status.container_statuses
                ]
            
            pod_list.append(pod_info)
        
        return {
            "status": "success",
            "config_info": config_status,
            "pod_count": len(pod_list),
            "pods": pod_list
        }
        
    except ApiException as e:
        return {
            "status": "error",
            "error_message": f"Kubernetes API error: {e.reason}",
            "error_code": e.status
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error listing pods: {str(e)}"
        }


def get_nodes() -> Dict[str, Any]:
    """
    List nodes in the Kubernetes cluster.
    
    Returns:
        dict: Status and list of nodes with their details
    """
    try:
        # Load config
        config_status = load_kubernetes_config()
        
        # Create API client
        v1 = client.CoreV1Api()
        
        # List nodes
        nodes = v1.list_node(watch=False)
        
        # Format node information
        node_list = []
        for node in nodes.items:
            # Get node conditions
            conditions = {}
            if node.status.conditions:
                for condition in node.status.conditions:
                    conditions[condition.type] = condition.status
            
            # Get node capacity and allocatable resources
            capacity = node.status.capacity if node.status.capacity else {}
            allocatable = node.status.allocatable if node.status.allocatable else {}
            
            node_info = {
                "name": node.metadata.name,
                "status": "Ready" if conditions.get("Ready") == "True" else "NotReady",
                "roles": [],
                "version": node.status.node_info.kubelet_version if node.status.node_info else "Unknown",
                "os": node.status.node_info.operating_system if node.status.node_info else "Unknown",
                "architecture": node.status.node_info.architecture if node.status.node_info else "Unknown",
                "capacity": {
                    "cpu": capacity.get("cpu", "Unknown"),
                    "memory": capacity.get("memory", "Unknown"),
                    "pods": capacity.get("pods", "Unknown")
                },
                "allocatable": {
                    "cpu": allocatable.get("cpu", "Unknown"),
                    "memory": allocatable.get("memory", "Unknown"),
                    "pods": allocatable.get("pods", "Unknown")
                },
                "conditions": conditions
            }
            
            # Extract roles from labels
            if node.metadata.labels:
                for label_key in node.metadata.labels:
                    if "node-role.kubernetes.io/" in label_key:
                        role = label_key.replace("node-role.kubernetes.io/", "")
                        if role:
                            node_info["roles"].append(role)
            
            if not node_info["roles"]:
                node_info["roles"] = ["worker"]  # Default role if no specific role found
                
            node_list.append(node_info)
        
        return {
            "status": "success",
            "config_info": config_status,
            "node_count": len(node_list),
            "nodes": node_list
        }
        
    except ApiException as e:
        return {
            "status": "error",
            "error_message": f"Kubernetes API error: {e.reason}",
            "error_code": e.status
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error listing nodes: {str(e)}"
        }


def get_namespaces() -> Dict[str, Any]:
    """
    List all namespaces in the Kubernetes cluster.
    
    Returns:
        dict: Status and list of namespaces
    """
    try:
        # Load config
        config_status = load_kubernetes_config()
        
        # Create API client
        v1 = client.CoreV1Api()
        
        # List namespaces
        namespaces = v1.list_namespace(watch=False)
        
        # Format namespace information
        namespace_list = []
        for ns in namespaces.items:
            namespace_info = {
                "name": ns.metadata.name,
                "status": ns.status.phase,
                "created": str(ns.metadata.creation_timestamp),
                "labels": ns.metadata.labels or {}
            }
            namespace_list.append(namespace_info)
        
        return {
            "status": "success",
            "config_info": config_status,
            "namespace_count": len(namespace_list),
            "namespaces": namespace_list
        }
        
    except ApiException as e:
        return {
            "status": "error",
            "error_message": f"Kubernetes API error: {e.reason}",
            "error_code": e.status
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error listing namespaces: {str(e)}"
        }


def get_services(namespace: str = "all") -> Dict[str, Any]:
    """
    List services in the Kubernetes cluster.
    
    Args:
        namespace: The namespace to list services from. Use "all" for all namespaces.
    
    Returns:
        dict: Status and list of services with their details
    """
    try:
        # Load config
        config_status = load_kubernetes_config()
        
        # Create API client
        v1 = client.CoreV1Api()
        
        # List services
        if namespace.lower() == "all":
            services = v1.list_service_for_all_namespaces(watch=False)
        else:
            services = v1.list_namespaced_service(namespace=namespace, watch=False)
        
        # Format service information
        service_list = []
        for svc in services.items:
            service_info = {
                "name": svc.metadata.name,
                "namespace": svc.metadata.namespace,
                "type": svc.spec.type,
                "cluster_ip": svc.spec.cluster_ip,
                "external_ip": svc.spec.external_i_ps if svc.spec.external_i_ps else [],
                "ports": []
            }
            
            # Add port information
            if svc.spec.ports:
                for port in svc.spec.ports:
                    port_info = {
                        "name": port.name,
                        "protocol": port.protocol,
                        "port": port.port,
                        "target_port": str(port.target_port) if port.target_port else None,
                        "node_port": port.node_port
                    }
                    service_info["ports"].append(port_info)
            
            # Add load balancer IP if applicable
            if svc.spec.type == "LoadBalancer" and svc.status.load_balancer:
                if svc.status.load_balancer.ingress:
                    service_info["load_balancer_ip"] = [
                        ing.ip for ing in svc.status.load_balancer.ingress if ing.ip
                    ]
            
            service_list.append(service_info)
        
        return {
            "status": "success",
            "config_info": config_status,
            "service_count": len(service_list),
            "services": service_list
        }
        
    except ApiException as e:
        return {
            "status": "error",
            "error_message": f"Kubernetes API error: {e.reason}",
            "error_code": e.status
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error listing services: {str(e)}"
        }


def get_deployments(namespace: str = "all") -> Dict[str, Any]:
    """
    List deployments in the Kubernetes cluster.
    
    Args:
        namespace: The namespace to list deployments from. Use "all" for all namespaces.
    
    Returns:
        dict: Status and list of deployments with their details
    """
    try:
        # Load config
        config_status = load_kubernetes_config()
        
        # Create API client
        apps_v1 = client.AppsV1Api()
        
        # List deployments
        if namespace.lower() == "all":
            deployments = apps_v1.list_deployment_for_all_namespaces(watch=False)
        else:
            deployments = apps_v1.list_namespaced_deployment(namespace=namespace, watch=False)
        
        # Format deployment information
        deployment_list = []
        for dep in deployments.items:
            deployment_info = {
                "name": dep.metadata.name,
                "namespace": dep.metadata.namespace,
                "replicas": dep.spec.replicas,
                "ready_replicas": dep.status.ready_replicas or 0,
                "available_replicas": dep.status.available_replicas or 0,
                "updated_replicas": dep.status.updated_replicas or 0,
                "labels": dep.metadata.labels or {},
                "conditions": []
            }
            
            # Add deployment conditions
            if dep.status.conditions:
                for condition in dep.status.conditions:
                    deployment_info["conditions"].append({
                        "type": condition.type,
                        "status": condition.status,
                        "reason": condition.reason,
                        "message": condition.message
                    })
            
            deployment_list.append(deployment_info)
        
        return {
            "status": "success",
            "config_info": config_status,
            "deployment_count": len(deployment_list),
            "deployments": deployment_list
        }
        
    except ApiException as e:
        return {
            "status": "error",
            "error_message": f"Kubernetes API error: {e.reason}",
            "error_code": e.status
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error listing deployments: {str(e)}"
        }


def get_logs(
    pod_name: str, 
    namespace: str = "default", 
    container: Optional[str] = None,
    previous: bool = False,
    tail_lines: Optional[int] = None,
    since_seconds: Optional[int] = None,
    timestamps: bool = False
) -> Dict[str, Any]:
    """
    Get logs from a pod container.
    
    Args:
        pod_name: Name of the pod
        namespace: Namespace of the pod (default: "default")
        container: Container name (required if pod has multiple containers)
        previous: If True, get logs from previous terminated container
        tail_lines: Number of lines from the end of logs to return (e.g., 100)
        since_seconds: Return logs newer than this many seconds (e.g., 3600 for last hour)
        timestamps: If True, include timestamps in log output
    
    Returns:
        dict: Status and logs from the pod
    """
    try:
        # Load config
        config_status = load_kubernetes_config()
        
        # Create API client
        v1 = client.CoreV1Api()
        
        # First, get pod info to check containers
        try:
            pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Get container names
            container_names = [c.name for c in pod.spec.containers]
            
            # If no container specified and pod has multiple containers, return container list
            if not container and len(container_names) > 1:
                return {
                    "status": "error",
                    "error_message": f"Pod has multiple containers. Please specify one: {container_names}",
                    "containers": container_names
                }
            
            # Use first container if not specified
            if not container and container_names:
                container = container_names[0]
                
        except ApiException as e:
            return {
                "status": "error",
                "error_message": f"Pod '{pod_name}' not found in namespace '{namespace}'",
                "error_code": e.status
            }
        
        # Prepare log options
        kwargs = {
            "name": pod_name,
            "namespace": namespace,
            "container": container,
            "previous": previous,
            "timestamps": timestamps
        }
        
        # Add optional parameters
        if tail_lines is not None:
            kwargs["tail_lines"] = tail_lines
        if since_seconds is not None:
            kwargs["since_seconds"] = since_seconds
            
        # Get logs
        logs = v1.read_namespaced_pod_log(**kwargs)
        
        # Split logs into lines for better readability
        log_lines = logs.split('\n') if logs else []
        
        # Prepare response
        response = {
            "status": "success",
            "config_info": config_status,
            "pod": pod_name,
            "namespace": namespace,
            "container": container,
            "log_lines_count": len(log_lines),
            "logs": logs  # Full log text
        }
        
        # Add additional info if relevant
        if tail_lines:
            response["tail_lines_requested"] = tail_lines
        if since_seconds:
            response["since_seconds"] = since_seconds
        if previous:
            response["from_previous_container"] = True
        if timestamps:
            response["timestamps_included"] = True
            
        # If logs are empty, add helpful message
        if not logs or logs.strip() == "":
            response["message"] = "No logs found. The container might be starting up or not producing any output."
            
        return response
        
    except ApiException as e:
        error_msg = f"Failed to get logs: {e.reason}"
        
        # Provide more helpful error messages
        if e.status == 400:
            if "previous terminated container" in str(e.body).lower():
                error_msg = "No previous terminated container found for this pod"
            elif "container" in str(e.body).lower():
                error_msg = f"Container '{container}' not found in pod. Available containers: {container_names}"
        elif e.status == 404:
            error_msg = f"Pod '{pod_name}' not found in namespace '{namespace}'"
            
        return {
            "status": "error",
            "error_message": error_msg,
            "error_code": e.status
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting logs: {str(e)}"
        }


def describe_pod(name: str, namespace: str = "default") -> Dict[str, Any]:
    """
    Get detailed information about a specific pod.
    
    Args:
        name: The name of the pod
        namespace: The namespace of the pod (default: "default")
    
    Returns:
        dict: Status and detailed pod information
    """
    try:
        # Load config
        config_status = load_kubernetes_config()
        
        # Create API client
        v1 = client.CoreV1Api()
        
        # Get pod details
        pod = v1.read_namespaced_pod(name=name, namespace=namespace)
        
        # Format detailed pod information
        pod_details = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "uid": pod.metadata.uid,
            "created": str(pod.metadata.creation_timestamp),
            "labels": pod.metadata.labels or {},
            "annotations": pod.metadata.annotations or {},
            "status": {
                "phase": pod.status.phase,
                "message": pod.status.message,
                "reason": pod.status.reason,
                "pod_ip": pod.status.pod_ip,
                "host_ip": pod.status.host_ip,
                "start_time": str(pod.status.start_time) if pod.status.start_time else None
            },
            "spec": {
                "node_name": pod.spec.node_name,
                "restart_policy": pod.spec.restart_policy,
                "service_account": pod.spec.service_account_name,
                "containers": []
            },
            "conditions": [],
            "events": []
        }
        
        # Add container details
        for container in pod.spec.containers:
            container_info = {
                "name": container.name,
                "image": container.image,
                "ports": [],
                "env": [],
                "resources": {}
            }
            
            if container.ports:
                container_info["ports"] = [
                    {"container_port": p.container_port, "protocol": p.protocol}
                    for p in container.ports
                ]
            
            if container.env:
                container_info["env"] = [
                    {"name": e.name, "value": e.value}
                    for e in container.env if e.value  # Only include env vars with direct values
                ]
            
            if container.resources:
                if container.resources.requests:
                    container_info["resources"]["requests"] = dict(container.resources.requests)
                if container.resources.limits:
                    container_info["resources"]["limits"] = dict(container.resources.limits)
            
            pod_details["spec"]["containers"].append(container_info)
        
        # Add container statuses
        if pod.status.container_statuses:
            pod_details["container_statuses"] = []
            for cs in pod.status.container_statuses:
                status_info = {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "image": cs.image,
                    "image_id": cs.image_id,
                    "container_id": cs.container_id
                }
                
                # Add current state
                if cs.state:
                    if cs.state.running:
                        status_info["state"] = {"running": {"started_at": str(cs.state.running.started_at)}}
                    elif cs.state.terminated:
                        status_info["state"] = {
                            "terminated": {
                                "exit_code": cs.state.terminated.exit_code,
                                "reason": cs.state.terminated.reason,
                                "message": cs.state.terminated.message
                            }
                        }
                    elif cs.state.waiting:
                        status_info["state"] = {
                            "waiting": {
                                "reason": cs.state.waiting.reason,
                                "message": cs.state.waiting.message
                            }
                        }
                
                pod_details["container_statuses"].append(status_info)
        
        # Add pod conditions
        if pod.status.conditions:
            for condition in pod.status.conditions:
                pod_details["conditions"].append({
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message,
                    "last_transition_time": str(condition.last_transition_time)
                })
        
        return {
            "status": "success",
            "config_info": config_status,
            "pod": pod_details
        }
        
    except ApiException as e:
        return {
            "status": "error",
            "error_message": f"Kubernetes API error: {e.reason}",
            "error_code": e.status
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error getting pod details: {str(e)}"
        }


# Configure the model based on environment variable
def get_model_config():
    """
    Get the model configuration based on LLM_TYPE environment variable.
    
    Returns:
        Model object configured for either cloud or local LLM
    """
    llm_type = os.getenv('LLM_TYPE', 'cloud').lower()
    
    if llm_type == 'local':
        if not LITELLM_AVAILABLE:
            print("Error: Local LLM requested but LiteLlm not available.")
            print("Falling back to cloud LLM (Gemini).")
            llm_type = 'cloud'
        else:
            # Local LLM configuration (LM Studio)
            lm_studio_base = os.getenv('LM_STUDIO_API_BASE', 'http://127.0.0.1:1234/v1/')
            lm_studio_model = os.getenv('LM_STUDIO_MODEL', 'lm_studio/qwen3-1.7b')
            
            # Set the API base for LM Studio
            os.environ['LM_STUDIO_API_BASE'] = lm_studio_base
            
            print(f"Using Local LLM: {lm_studio_model} at {lm_studio_base}")
            return LiteLlm(model=lm_studio_model)
    
    # Cloud LLM configuration (Gemini)
    # Default to Gemini 2.0 Pro for best performance
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.0-pro-exp')
    
    print(f"Using Cloud LLM: {gemini_model}")
    return gemini_model


# Create the root agent with Kubernetes tools
root_agent = Agent(
    name="kubernetes_agent",
    model=get_model_config(),  # Dynamic model selection
    description=(
        "An agent that can interact with Kubernetes clusters to retrieve information "
        "about pods, nodes, services, deployments, and other Kubernetes resources."
    ),
    instruction=(
        "You are a helpful Kubernetes assistant that can query and retrieve information "
        "from Kubernetes clusters. You can list pods, nodes, services, deployments, and "
        "namespaces. You can also get detailed information about specific resources and "
        "retrieve logs from pod containers. "
        "When users ask about their Kubernetes cluster, use the appropriate tools to "
        "fetch the information they need. Always provide clear and organized responses "
        "about the cluster state and resources. "
        "For log requests, you can retrieve recent logs, tail a specific number of lines, "
        "get logs from a specific time period, or even get logs from previously crashed containers."
    ),
    tools=[
        get_pods,
        get_nodes,
        get_namespaces,
        get_services,
        get_deployments,
        describe_pod,
        get_logs
    ]
)