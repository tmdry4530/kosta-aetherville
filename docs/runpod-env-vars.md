# RunPod Environment Variables

Create `infra/runpod/.env.runpod` from `.env.runpod.example`.

Required:

```bash
RUNPOD_HOST=
RUNPOD_SSH_PORT=22
RUNPOD_USER=root
RUNPOD_SSH_KEY=/absolute/path/to/private_key
RUNPOD_REMOTE_DIR=/workspace/aetherville
RUNPOD_PUBLIC_ORCHESTRATOR_URL=http://<host>:8080
RUNPOD_PUBLIC_VISION_URL=http://<host>:8001
RUNPOD_PUBLIC_VLLM_URL=http://<host>:8000/v1
```

Optional:

```bash
HF_TOKEN=
AETHERVILLE_JWT_SECRET=
AETHERVILLE_DEMO_TOKEN=
MODEL_NAME=Qwen/Qwen2.5-14B-Instruct-AWQ
VLLM_GPU_MEMORY_UTILIZATION=0.90
```

Never commit this file.
