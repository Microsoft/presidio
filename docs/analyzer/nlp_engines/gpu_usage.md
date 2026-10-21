# GPU Acceleration

Presidio supports GPU acceleration for NLP models, which can significantly improve performance when processing large volumes of text. GPU is automatically detected and used when available—no code changes required.

## Environment Variable Override

You can explicitly control device selection using the `PRESIDIO_DEVICE` environment variable. Any valid PyTorch device string is accepted:

```bash
# Force CPU usage
export PRESIDIO_DEVICE=cpu

# Force GPU usage
export PRESIDIO_DEVICE=cuda

# Use a specific GPU
export PRESIDIO_DEVICE=cuda:0
export PRESIDIO_DEVICE=cuda:1

# Or when running Docker containers
docker run -e PRESIDIO_DEVICE=cuda ghcr.io/data-privacy-stack/presidio-analyzer:latest
```

!!! note "Priority"
    When `PRESIDIO_DEVICE` is set, it takes priority over automatic detection. If not set (or empty), Presidio will auto-detect available hardware.

## Prerequisites

### Hardware Requirements

| Hardware | Requirement |
|----------|-------------|
| **NVIDIA GPU** | CUDA Toolkit 11.x or 12.x |
| **Apple Silicon** | MPS (Metal Performance Shaders) on M1/M2/M3 |
| **CPU** | Automatic fallback when GPU is unavailable |

### Software Dependencies

=== "NVIDIA GPU"

    Install the appropriate CUDA library matching your CUDA version:

    ```bash
    pip install "spacy[cuda12x]"  # For CUDA 12.x
    # or
    pip install "spacy[cuda11x]"  # For CUDA 11.x
    ```

    !!! warning "Silent Fallback"
        If `cupy` is not installed or the version mismatches your CUDA driver, spaCy will silently fall back to CPU. Always verify your setup using the methods below.

=== "Apple Silicon"

    No additional dependencies required. MPS is detected automatically.




## Verifying GPU Usage

To check if GPU is available and being used:

```python
import torch

if torch.cuda.is_available():
    print(f"GPU available: CUDA ({torch.cuda.get_device_name(0)})")
elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    print("GPU available: MPS (Apple Silicon)")
else:
    print("Using CPU")
```

You can also monitor GPU usage during processing:

```bash
# For NVIDIA GPUs
watch -n 1 nvidia-smi

# For Apple Silicon
sudo powermetrics --samplers gpu_power
```

## GPU-Enabled NLP Engines

| Engine | GPU Support |
|--------|-------------|
| **TransformersNlpEngine** | ✅ Full |
| **GLiNER** | ✅ Full |
| **Stanza** | ✅ Full |
| **spaCy (transformer models)** | ✅ Full |
| **spaCy (standard models)** | ⚠️ Not recommended |

!!! warning "Standard spaCy Models"
    GPU is recommended for Transformers, Stanza, and GLiNER workloads. Standard spaCy models (e.g., `en_core_web_lg`) may be slower on GPU due to data transfer overhead.

## Troubleshooting

### GPU not detected

1. Check CUDA is installed:
   ```bash
   nvidia-smi
   nvcc --version
   ```

2. Verify cupy can see your GPU:
   ```python
   import cupy as cp
   print(cp.cuda.runtime.getDeviceCount())  # Should be > 0
   ```

3. Reinstall cupy with correct CUDA version:
   ```bash
   pip uninstall cupy cupy-cuda11x cupy-cuda12x
   pip install cupy-cuda12x  # Match your CUDA version
   ```

### Out of memory errors

If you see `RuntimeError: CUDA out of memory`:

- Use a smaller transformer model (e.g., `dslim/bert-base-NER` instead of larger models)
- Split longer texts into smaller chunks before processing
- Reduce the maximum sequence length if using Hugging Face transformers

### CPU fallback

Presidio automatically uses CPU if:

- No GPU is detected
- CUDA or cupy are not installed
- GPU initialization fails

This ensures code portability across different environments.

## Additional Resources

- [spaCy: GPU Usage](https://spacy.io/usage/embeddings-transformers#gpu)
- [NVIDIA CUDA Installation Guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
- [cupy Documentation](https://docs.cupy.dev/en/stable/install.html)

Related Presidio documentation:

- [Transformer Models](transformers.md)
- [spaCy and Stanza Models](spacy_stanza.md)
- [Customizing NLP Models](../customizing_nlp_models.md)
- [HuggingFace NER inference backends](../huggingface_ner_inference.md) — ORT execution providers (CUDA, TensorRT, OpenVINO, CoreML, ROCm) and Intel-specific acceleration via `HuggingFaceNerRecognizer`
