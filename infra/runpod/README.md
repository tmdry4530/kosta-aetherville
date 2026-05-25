# RunPod Infra Files

1. Copy `.env.runpod.example` to `.env.runpod`.
2. Fill SSH variables locally. Do not commit or print the filled file.
3. Verify SSH/GPU/runtime state:

```bash
bash infra/runpod/verify_runpod.sh
```

4. Dry-run deploy/sync:

```bash
bash infra/runpod/deploy_over_ssh.sh --dry-run --mode direct
```

5. Actual direct-process deploy after local verification:

```bash
bash infra/runpod/deploy_over_ssh.sh --mode direct
```

Direct-process scripts:

```bash
bash infra/runpod/start_direct_processes.sh
bash infra/runpod/health_check_direct.sh
bash infra/runpod/stop_direct_processes.sh
```

Current verified RunPod state uses direct-process runtime because Docker daemon
is unavailable and not required. These scripts are conservative: they do not
install Docker, run Docker Compose, or delete remote data. Real vLLM model
downloads start only when explicitly configured with
`AETHERVILLE_VLLM_MODE=real`, `AETHERVILLE_BOOTSTRAP_VLLM=1`, and a selected
`MODEL_NAME`; the current 4090 pod uses a CUDA-12.8-compatible vLLM pin such as
`AETHERVILLE_VLLM_INSTALL_PACKAGE="vllm==0.10.2"` plus
`AETHERVILLE_VLLM_COMPAT_PACKAGE="transformers==4.55.4"`, and model cache
should live under `/workspace`.
