# RunPod Environment Variables

Create `infra/runpod/.env.runpod` from `.env.runpod.example`.

Required:

See `infra/runpod/.env.runpod.example` for the variable names. Fill values only
in the ignored `infra/runpod/.env.runpod` file or process environment.

For the verified direct-process pod, use:

- orchestrator public URL mapped to service port `8080`
- Socket.IO public URL mapped to the same orchestrator service
- vision public URL mapped to verified service port `18001`
- vLLM fallback public URL mapped to service port `8000` with `/v1`

Optional:

Optional model/runtime secret variables stay local only. Do not copy values into
tracked docs or chat.

Never commit this file.
