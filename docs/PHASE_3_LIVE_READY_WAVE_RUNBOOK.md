# Phase 3 Live Ready Runbook: legacy hosts + embedded + AI/graph + QKD + neuromorphic

## Scope
This runbook covers:
- legacy host baselines (HP-UX, Oracle Solaris, OpenVMS)
- embedded control plane (VxWorks)
- graph and agentic AI
- QKD
- neuromorphic compute (Intel Loihi / IBM TrueNorth)

## Required env vars
- [ ] `SANCTUM_HOST_INVENTORY_URL`
- [ ] `SANCTUM_HOST_API_TOKEN`
- [ ] `SANCTUM_OS_FAMILY`
- [ ] `SANCTUM_VXWORKS_API_URL`
- [ ] `SANCTUM_VXWORKS_TOKEN`
- [ ] `SANCTUM_GNN_MODEL_REGISTRY`
- [ ] `SANCTUM_MODEL_API_TOKEN`
- [ ] `SANCTUM_AGENT_RUNTIME`
- [ ] `SANCTUM_AGENT_TOKEN`
- [ ] `SANCTUM_QKD_PEER_ID`
- [ ] `SANCTUM_QKD_KME_URL`
- [ ] `SANCTUM_QKD_TOKEN`
- [ ] `SANCTUM_NEUROMORPHIC_ACCELERATOR`
- [ ] `SANCTUM_NEUROMORPHIC_TOKEN`

## Gate checklist
- [ ] Host inventory endpoint responds successfully
- [ ] Legacy OS baseline is approved by system owner
- [ ] Embedded control-plane endpoint is authenticated and reachable
- [ ] Graph model registry is reachable and model metadata is valid
- [ ] Agent runtime is reachable and returns valid runtime state
- [ ] QKD peer is validated and session is active
- [ ] Neuromorphic hardware metadata is readable and policy-allowed
- [ ] Evidence is recorded and signed

## Notes
These environments are usually sensitive and may require dedicated enclaves, network segmentation, specialized certs, and explicit policy approval before a capability becomes `READY`.
