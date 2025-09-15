# ADK with Local Gemma Model on Kubernetes

This repository demonstrates using ADK with a local Gemma model running in Ollama on Kubernetes, plus additional deployments for Nginx and ADK with shared storage.

## Prerequisites

- Kubernetes cluster with GPU support (optional, can run on CPU)
- kubectl configured to access your cluster

## Deployments

### 1. Ollama with Gemma Model

#### Option A: GPU Deployment with Local Storage

Deploy Ollama with GPU support and Gemma model using hostPath storage:

```bash
# Create namespace
kubectl create namespace ollama-system

# Deploy Ollama with GPU
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-gpu
  namespace: ollama-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama-gpu
  template:
    metadata:
      labels:
        app: ollama-gpu
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        env:
        - name: OLLAMA_HOST
          value: "0.0.0.0"
        volumeMounts:
        - name: ollama-storage
          mountPath: /root/.ollama
        resources:
          limits:
            nvidia.com/gpu: 1
          requests:
            memory: "8Gi"
            cpu: "4"
        command: ["/bin/bash", "-c"]
        args:
        - |
          ollama serve &
          sleep 10
          ollama pull gemma:2b
          wait
      volumes:
      - name: ollama-storage
        hostPath:
          path: /var/ollama-data
          type: DirectoryOrCreate
---
apiVersion: v1
kind: Service
metadata:
  name: ollama-service
  namespace: ollama-system
spec:
  selector:
    app: ollama-gpu
  ports:
  - protocol: TCP
    port: 11434
    targetPort: 11434
  type: ClusterIP
EOF
```

#### Option B: CPU Deployment with Local Storage

Deploy Ollama on CPU with hostPath storage:

```bash
# Deploy Ollama with CPU and local storage
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-cpu
  namespace: ollama-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama-cpu
  template:
    metadata:
      labels:
        app: ollama-cpu
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        env:
        - name: OLLAMA_HOST
          value: "0.0.0.0"
        volumeMounts:
        - name: ollama-storage
          mountPath: /root/.ollama
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        command: ["/bin/bash", "-c"]
        args:
        - |
          ollama serve &
          sleep 10
          ollama pull gemma:2b
          wait
      volumes:
      - name: ollama-storage
        hostPath:
          path: /var/ollama-data
          type: DirectoryOrCreate
---
apiVersion: v1
kind: Service
metadata:
  name: ollama-cpu-service
  namespace: ollama-system
spec:
  selector:
    app: ollama-cpu
  ports:
  - protocol: TCP
    port: 11434
    targetPort: 11434
  type: ClusterIP
EOF
```

### 2. Nginx Deployment

Deploy a simple Nginx web server:

```bash
# Deploy Nginx
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: web-apps
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
  namespace: web-apps
data:
  index.html: |
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kubernetes Nginx</title>
    </head>
    <body>
        <h1>Welcome to Nginx on Kubernetes!</h1>
        <p>This page is served from a Kubernetes pod.</p>
    </body>
    </html>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: web-apps
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
        volumeMounts:
        - name: nginx-content
          mountPath: /usr/share/nginx/html
        - name: nginx-logs
          mountPath: /var/log/nginx
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
      volumes:
      - name: nginx-content
        configMap:
          name: nginx-config
      - name: nginx-logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
  namespace: web-apps
spec:
  selector:
    app: nginx
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: LoadBalancer
EOF
```

### 3. ADK Deployment with Shared Storage

Deploy ADK as a sidecar container sharing storage with Nginx to read logs:

```bash
# Deploy ADK with shared storage for log reading
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-with-adk
  namespace: web-apps
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx-with-adk
  template:
    metadata:
      labels:
        app: nginx-with-adk
    spec:
      containers:
      # Nginx container
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
        volumeMounts:
        - name: shared-logs
          mountPath: /var/log/nginx
        - name: nginx-config
          mountPath: /etc/nginx/conf.d
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
      # ADK container for log analysis
      - name: adk-log-reader
        image: busybox:latest
        command: ["/bin/sh", "-c"]
        args:
        - |
          echo "ADK Log Reader Started"
          while true; do
            echo "=== Nginx Access Logs (Last 10 lines) ==="
            tail -n 10 /var/log/nginx/access.log 2>/dev/null || echo "No access logs yet"
            echo ""
            echo "=== Nginx Error Logs (Last 10 lines) ==="
            tail -n 10 /var/log/nginx/error.log 2>/dev/null || echo "No error logs yet"
            echo ""
            sleep 30
          done
        volumeMounts:
        - name: shared-logs
          mountPath: /var/log/nginx
          readOnly: true
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
      volumes:
      - name: shared-logs
        emptyDir: {}
      - name: nginx-config
        configMap:
          name: nginx-log-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-log-config
  namespace: web-apps
data:
  custom.conf: |
    server {
        listen 80;
        server_name localhost;
        
        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;
        
        location / {
            root /usr/share/nginx/html;
            index index.html;
        }
    }
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-adk-service
  namespace: web-apps
spec:
  selector:
    app: nginx-with-adk
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
EOF
```

## Verification Commands

After deploying, use these commands to verify your deployments:

```bash
# Check Ollama deployment
kubectl get pods -n ollama-system
kubectl logs -n ollama-system -l app=ollama-gpu  # or app=ollama-cpu

# Test Ollama API
kubectl port-forward -n ollama-system svc/ollama-service 11434:11434
# In another terminal:
curl http://localhost:11434/api/tags

# Check Nginx deployment
kubectl get pods -n web-apps
kubectl get svc -n web-apps

# Check ADK log reader
kubectl logs -n web-apps -l app=nginx-with-adk -c adk-log-reader

# Access Nginx web page
kubectl port-forward -n web-apps svc/nginx-service 8080:80
# Browse to http://localhost:8080
```

## Cleanup

To remove all deployments:

```bash
kubectl delete namespace ollama-system
kubectl delete namespace web-apps
```

## Using ADK with the Local Gemma Model

Once Ollama is running with the Gemma model, you can configure ADK to use it:

```bash
# Port-forward Ollama service
kubectl port-forward -n ollama-system svc/ollama-service 11434:11434 &

# Configure ADK to use local Ollama
export OLLAMA_HOST=http://localhost:11434

# Run ADK web interface
adk web
```

## Notes

- The deployments use hostPath storage which stores data at `/var/ollama-data` on the node
- The GPU deployment requires nodes with NVIDIA GPU support and appropriate drivers installed
- The ADK log reader continuously monitors Nginx logs every 30 seconds
- Adjust resource limits based on your cluster capacity and model requirements
- For production use, consider using proper PersistentVolumes for better data management

## Troubleshooting

If pods are not starting:
```bash
# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Check resource availability
kubectl top nodes
kubectl top pods -n <namespace>

# Check GPU availability (if using GPU)
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"
