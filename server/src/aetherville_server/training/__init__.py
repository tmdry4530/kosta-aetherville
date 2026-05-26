"""Model training pipeline surfaces for Aetherville.

The package provides the production boundary for moving from live JSON-backed
adaptation into model-weight training. Expensive trainer execution is guarded by
explicit opt-in environment variables; dry-run cycles still build datasets and
registry/evaluation evidence so demo operators can verify the full handoff path
without spending GPU time.
"""

from .pipeline import TrainingPipeline, default_training_pipeline

__all__ = ["TrainingPipeline", "default_training_pipeline"]
