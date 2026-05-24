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

Current verified RunPod state uses direct-process fallback because Docker daemon
is unavailable. These scripts are conservative: they do not install Docker,
delete remote data, or start real vLLM model downloads unless explicitly
configured with `AETHERVILLE_VLLM_MODE=real` and an approved `MODEL_NAME`.
