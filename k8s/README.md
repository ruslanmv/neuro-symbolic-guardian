# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the Neuro-Symbolic Guardian in production.

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3 (optional, for monitoring stack)
- cert-manager (for TLS certificates)
- nginx-ingress-controller

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f deployment.yaml
```

This will create:
- Namespace: `neuro-symbolic-guardian`
- ConfigMap for configuration
- Secret for sensitive data (you must update this!)
- Deployment with 3 replicas
- Service
- ServiceAccount
- PodDisruptionBudget
- HorizontalPodAutoscaler

### 2. Update Secrets

**IMPORTANT:** Before deploying, update the secret with your actual API key:

```bash
# Create secret from file
kubectl create secret generic guardian-secrets \
  --from-literal=AEGIS_LLM_API_KEY='your-actual-api-key' \
  -n neuro-symbolic-guardian \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 3. Deploy Policy ConfigMap

```bash
kubectl create configmap guardian-policy \
  --from-file=production.yaml=../policies/production.yaml \
  -n neuro-symbolic-guardian
```

### 4. Deploy Ingress (Optional)

Update `ingress.yaml` with your domain name, then:

```bash
kubectl apply -f ingress.yaml
```

### 5. Verify Deployment

```bash
# Check pods
kubectl get pods -n neuro-symbolic-guardian

# Check logs
kubectl logs -f deployment/guardian-api -n neuro-symbolic-guardian

# Check service
kubectl get svc -n neuro-symbolic-guardian

# Port forward for local testing
kubectl port-forward svc/guardian-api 8000:80 -n neuro-symbolic-guardian
```

## Configuration

### Environment Variables

Configure via ConfigMap (`guardian-config`):

- `AEGIS_ENV`: Environment name (production/staging/dev)
- `AEGIS_LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)
- `AEGIS_FAIL_MODE`: Fail mode (open/closed)
- `AEGIS_SOLVER_TIMEOUT`: Z3 solver timeout in milliseconds

### Secrets

Configure via Secret (`guardian-secrets`):

- `AEGIS_LLM_API_KEY`: LLM API key (OpenAI, etc.)

### Policy Updates

To update the policy without redeploying:

```bash
# Update policy
kubectl create configmap guardian-policy \
  --from-file=production.yaml=../policies/production.yaml \
  -n neuro-symbolic-guardian \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new policy
kubectl rollout restart deployment/guardian-api -n neuro-symbolic-guardian
```

## Monitoring

### Prometheus

If you have Prometheus installed, the pods are already annotated for scraping:

```yaml
prometheus.io/scrape: "true"
prometheus.io/port: "8000"
prometheus.io/path: "/metrics"
```

### Health Checks

- Liveness probe: `http://localhost:8000/healthz`
- Readiness probe: `http://localhost:8000/readyz`
- Metrics: `http://localhost:8000/metrics`

## Scaling

### Manual Scaling

```bash
kubectl scale deployment/guardian-api --replicas=5 -n neuro-symbolic-guardian
```

### Auto-scaling

The HPA is configured to scale based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Min replicas: 3
- Max replicas: 10

## Security

### Pod Security

- Runs as non-root user (UID 1000)
- Read-only root filesystem
- No privilege escalation
- All capabilities dropped

### Network Policies (Optional)

Create network policies to restrict traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: guardian-api-netpol
  namespace: neuro-symbolic-guardian
spec:
  podSelector:
    matchLabels:
      app: guardian-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443  # HTTPS for LLM API
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53  # DNS
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n neuro-symbolic-guardian

# Check events
kubectl get events -n neuro-symbolic-guardian --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n neuro-symbolic-guardian
```

### Policy not loading

```bash
# Check configmap
kubectl get configmap guardian-policy -n neuro-symbolic-guardian -o yaml

# Check if mounted correctly
kubectl exec <pod-name> -n neuro-symbolic-guardian -- ls -la /app/policies
```

### High memory usage

Increase resource limits in `deployment.yaml`:

```yaml
resources:
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### API key issues

Verify secret is created correctly:

```bash
kubectl get secret guardian-secrets -n neuro-symbolic-guardian -o yaml
```

## Production Checklist

Before going to production:

- [ ] Update API key in secret
- [ ] Configure custom domain in ingress
- [ ] Set up TLS certificates
- [ ] Configure appropriate resource limits
- [ ] Enable monitoring (Prometheus/Grafana)
- [ ] Set up log aggregation
- [ ] Configure backup strategy for policies
- [ ] Set up alerting rules
- [ ] Perform load testing
- [ ] Document incident response procedures
- [ ] Configure pod security policies
- [ ] Set up network policies
- [ ] Enable audit logging
- [ ] Configure rate limiting
- [ ] Set up disaster recovery

## Clean Up

To remove all resources:

```bash
kubectl delete namespace neuro-symbolic-guardian
```
