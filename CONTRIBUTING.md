## TODO
- https://google.github.io/adk-docs/deploy/gke/#code-files

## Steps

First clone the repo and create a virtual environment:

```bash
# Clone repo
git clone https://github.com/jimangel/adk-local-gemma.git
cd adk-local-gemma

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment on macOS/Linux:
source .venv/bin/activate

# install prereqs
pip install -r requirements.txt
```

### 3. Configure Environment

All settings are configured in `.env`, for local development. Use the example to get started:

```bash
cp .env.example .env
```

To test with a **cloud** model (Gemini) you MUST set the following values:

```bash
# cloud vs. local
LLM_TYPE=cloud

# Google AI Studio API Key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_actual_api_key_here

# Gemini model (default: gemini-2.5-pro)
GEMINI_MODEL=gemini-2.5-pro

# Kubernetes Configuration
KUBECONFIG=your_kubeconfig_path_here
```

To test with a **local** model (OpenAI API endpoint / tool use) you MUST set the following values:

```bash
# Choose LLM type
LLM_TYPE=local

# LM Studio settings
LM_STUDIO_API_BASE=http://127.0.0.1:1234/v1/
LM_STUDIO_MODEL=lm_studio/qwen3-1.7b

# Kubernetes Configuration
KUBECONFIG=your_kubeconfig_path_here
```

### Using ADK Web Interface (Recommended for Testing)

Navigate to the parent directory of your agent project and run:

```bash
adk web
```

This will launch a browser-based interface where you can interact with the agent.

---


## Extending the Agent

To add more Kubernetes functionality:

1. Import additional Kubernetes API clients:
   ```python
   from kubernetes import client
   batch_v1 = client.BatchV1Api()  # For Jobs
   networking_v1 = client.NetworkingV1Api()  # For Ingresses
   ```

2. Create new tool functions following the pattern:
   ```python
   def get_jobs(namespace: str = "all") -> Dict[str, Any]:
       # Implementation
       pass
   ```

3. Add the new tools to the agent:
   ```python
   tools=[..., get_jobs]
   ```

### Example: Adding ConfigMap Support

```python
def get_configmaps(namespace: str = "all") -> Dict[str, Any]:
    try:
        config_status = load_kubernetes_config()
        v1 = client.CoreV1Api()
        
        if namespace.lower() == "all":
            configmaps = v1.list_config_map_for_all_namespaces(watch=False)
        else:
            configmaps = v1.list_namespaced_config_map(namespace=namespace, watch=False)
        
        cm_list = [
            {
                "name": cm.metadata.name,
                "namespace": cm.metadata.namespace,
                "data_keys": list(cm.data.keys()) if cm.data else []
            }
            for cm in configmaps.items
        ]
        
        return {
            "status": "success",
            "configmaps": cm_list
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
```

---

#### Build Your Own Image

```bash
# Build the Docker image
docker build -t adk-local-gemma:latest .

# TO PUBLISH:
# Tag for your registry
docker tag adk-local-gemma:latest ghcr.io/jimangel/adk-local-gemma:latest

# Push to registry
docker push ghcr.io/jimangel/adk-local-gemma:latest
```