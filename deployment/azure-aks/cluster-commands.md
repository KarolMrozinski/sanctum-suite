# Azure AKS cluster commands

```bash
az login
az account set --subscription sanctum-prod-sub
az aks get-credentials --resource-group rg-sanctum-prod --name sanctum-aks-prod --overwrite-existing

kubectl create namespace sanctum-phase1
kubectl -n sanctum-phase1 create serviceaccount sanctum-phase1-sa
kubectl -n sanctum-phase1 create role sanctum-phase1-reader --verb=get,list,watch --resource=configmaps,secrets,pods
kubectl -n sanctum-phase1 create rolebinding sanctum-phase1-binding --role=sanctum-phase1-reader --serviceaccount=sanctum-phase1:sanctum-phase1-sa
kubectl -n sanctum-phase1 create secret generic sanctum-phase1-secrets --from-env-file=.env.phase1.aks.example
kubectl apply -f k8s/phase1-live-ready-aks.yaml
kubectl -n sanctum-phase1 get pods
kubectl -n sanctum-phase1 logs deploy/sanctum-suite-phase1
```
