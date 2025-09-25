# Kubernetes ADK Agent

Google ADK agent for Kubernetes cluster interaction. Supports cloud (Google Gemini) and local (OpenAI-compatible) LLMs.

![Architecture diagram](pics/arch.png)

## Features

- **LLM Support**: Google Gemini (cloud) or OpenAI-compatible endpoints (local)
- **Authentication**: Kubeconfig file or in-cluster service account
- **Kubernetes Tools**: List/describe pods, nodes, namespaces, services, deployments, and retrieve logs
- **Web Interface**: Built-in ADK web UI for testing

## Prerequisites

- Kubernetes cluster access
- Valid kubeconfig or in-cluster permissions
- **Cloud LLM**: Google AI Studio API key
- **Local LLM**: OpenAI-compatible endpoint (LM Studio, Ollama, etc.)

## Quick Start

### Option 1: Local Testing (Docker)

Pre-built image: `ghcr.io/jimangel/adk-local-gemma:latest`

![Development setup](pics/dev.png)

```bash
# select kubeconfig to use
export KUBECONFIG="your-kubeconfig"

# Run using a cloud LLM
export GOOGLE_API_KEY="your-api-key"

docker run \
  --name adk-local-test \
  -p 8082:8081 \
  -v ${KUBECONFIG}:/home/appuser/kubeconfig:ro \
  -e KUBECONFIG=/home/appuser/kubeconfig \
  -e GOOGLE_API_KEY=${GOOGLE_API_KEY} \
  -e LLM_TYPE="cloud" \
  -e GEMINI_MODEL="gemini-2.5-pro" \
  -e GOOGLE_GENAI_USE_VERTEXAI="FALSE" \
  -e LLM_TYPE=cloud \
  ghcr.io/jimangel/adk-local-gemma:latest

# Access UI: http://localhost:8082

# Run using a local LLM
export LM_STUDIO_API_BASE=http://127.0.0.1:1234/v1/
export LM_STUDIO_MODEL=qwen/qwen3-1.7b

docker run \
  --name adk-local-test \
  --network host \
  -e PORT=8888 \
  -v ${KUBECONFIG}:/home/appuser/kubeconfig:ro \
  -e KUBECONFIG=/home/appuser/kubeconfig \
  -e LLM_TYPE=local \
  -e LM_STUDIO_MODEL=${LM_STUDIO_MODEL} \
  -e LM_STUDIO_API_BASE=${LM_STUDIO_API_BASE} \
  ghcr.io/jimangel/adk-local-gemma:latest

# Access UI: http://localhost:8888
```

**Clean up:**
```bash
docker stop adk-local-test && docker rm adk-local-test
```

### Option 2: Kubernetes Deployment

The `k8s-deployment.yaml` includes:
- ServiceAccount with read-only cluster permissions
- ClusterRole and ClusterRoleBinding
- Deployment configuration

**Deploy:**
```bash
export GOOGLE_API_KEY="your-api-key"

# 1. Create API key secret
kubectl create secret generic adk-secrets \
  --from-literal=GOOGLE_API_KEY=${GOOGLE_API_KEY}

# 2. Apply manifest
kubectl apply -f k8s-deployment.yaml
```

**Access service:**
```bash
# Option A: Port forward
kubectl port-forward svc/adk-local-gemma 8081:8081
```

**Clean up:**
```bash
kubectl delete -f k8s-deployment.yaml
kubectl delete secret adk-secrets

# debug // check env vars
kubectl exec -it deploy/adk-local-gemma -- sh
```

**Tweaking / Configuration:**

Modify environment variables in `k8s-deployment.yaml`:

```yaml
env:
- name: LLM_TYPE
  value: "local"  # or "local"
- name: LM_STUDIO_MODEL
  value: "qwen/qwen3-1.7b"
- name: LM_STUDIO_API_BASE
  value: "http://127.0.0.1:1234/v1"  # for local LLMs
```
