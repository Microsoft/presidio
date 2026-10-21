# HuggingFace NER inference backends

The `HuggingFaceNerRecognizer` runs a HuggingFace token-classification model
to detect PII. It supports two inference backends, selected by the `backend`
constructor parameter — set it in the recognizer YAML or pass it directly
when constructing the recognizer in Python:

- `torch` (default) — PyTorch via the `transformers` pipeline. Works on CPU
  and NVIDIA GPU (CUDA).
- `ort` — ONNX Runtime via `optimum`. Works on CPU, NVIDIA GPU, AMD GPU,
  Intel CPU/iGPU/NPU, and Apple Silicon, by selecting an ONNX Runtime
  *execution provider*.

Any extra keyword arguments — whether passed in Python or as extra
fields in the YAML — are captured into `**model_kwargs` and forwarded to
the underlying loader. You do not need to edit the recognizer to plumb
new knobs. Which keys are valid depends on the backend:

| Key | `torch` | `ort` |
|-----|---------|-------|
| `revision`, `token`, `trust_remote_code`, `cache_dir`, `subfolder`, `local_files_only` | yes | yes |
| `file_name`, `provider`, `provider_options`, `session_options`, `export` | no | yes |

Passing an ort-only key to the torch backend raises a `TypeError` from
transformers at load time.

The examples below use YAML (the
[recognizer registry configuration](recognizer_registry_provider.md));
every field shown maps 1:1 to a constructor argument. The Python
equivalent of an ort configuration:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import HuggingFaceNerRecognizer

recognizer = HuggingFaceNerRecognizer(
    model_name="onnx-community/stanford-deidentifier-base-ONNX",
    backend="ort",
    subfolder="onnx",                 # forwarded via **model_kwargs
    file_name="model_quantized.onnx",  # forwarded via **model_kwargs
    label_mapping={
        "PATIENT": "PERSON",
        "HCW": "PERSON",
        "PHONE": "PHONE_NUMBER",
    },
    threshold=0.5,
)

analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(recognizer)
results = analyzer.analyze(text="Dr. Sarah Chen, 555-123-4567", language="en")
```

## Choosing a backend

| Hardware | Recommended backend | Why |
|----------|---------------------|-----|
| NVIDIA GPU, baseline | `torch` with `device: cuda` | Zero extra install, no model conversion |
| NVIDIA GPU + quantized ONNX | `ort` with `CUDAExecutionProvider` | Runs pre-quantized FP16/INT8 ONNX files that torch can't use directly |
| NVIDIA GPU + high throughput | `ort` with `TensorrtExecutionProvider` | Designed for sustained batch inference; slow first request (engine build) |
| Intel Xeon Scalable (Sapphire Rapids+) | `ort` with `OpenVINOExecutionProvider` | Uses native AVX-512 BF16 / AMX kernels not fully exploited by the default CPU EP |
| Intel iGPU / Arc / NPU | `ort` with `OpenVINOExecutionProvider` (`device_type=GPU` or `NPU`) | Only practical path for Intel accelerators |
| Apple Silicon | `ort` with `CoreMLExecutionProvider`, or CPU | The recognizer's device handling does not support MPS; CoreML EP is the only acceleration path |
| Generic cloud CPU | `torch` with `device: cpu`, or `ort` with default CPU EP | Comparable for FP32; ort additionally runs quantized variants |

## torch backend

The default. Uses `transformers.pipeline` directly. Best for "just works"
deployments.

```yaml
- name: "HF NER (torch)"
  type: predefined
  class_name: HuggingFaceNerRecognizer
  model_name: dslim/bert-base-NER
  backend: torch
  # device: cuda        # omit to let Presidio's device detector decide
  aggregation_strategy: simple
  threshold: 0.3
  supported_languages: [en]
  supported_entities: [PERSON, LOCATION, ORGANIZATION]
```

Device selection precedence:

1. **Explicit `device`** (`cpu` | `cuda` | `cuda:N` | int index) — hard
   override; bypasses the detector *and* `PRESIDIO_DEVICE`.
2. **`device` omitted** — Presidio's `DeviceDetector` singleton decides:
   the `PRESIDIO_DEVICE` environment variable if set, otherwise
   auto-detection (CUDA if available, else CPU). See
   [GPU Acceleration](nlp_engines/gpu_usage.md).

In most deployments, omit `device` and control hardware via
`PRESIDIO_DEVICE` — that keeps the YAML portable across CPU and GPU
environments. Set `device` explicitly only to pin a recognizer to
specific hardware regardless of environment (e.g. force a heavyweight
model onto `cuda:1`).

If CUDA is requested but unavailable, the recognizer logs a warning and
falls back to CPU.

!!! note "MPS (Apple Silicon) is not supported"
    Presidio's device detector does not support MPS, and the recognizer
    normalizes any non-CUDA device to CPU. On Apple Silicon the torch
    backend runs on CPU; for acceleration use the ort backend with the
    CoreML execution provider.

## ort backend

Uses optimum's `ORTModelForTokenClassification` plus ONNX Runtime.

### Installation

For CPU (also covers Apple Silicon via the CoreML EP), use the
`onnxruntime` extra:

```bash
pip install 'presidio-analyzer[onnxruntime]'
```

The extra installs the **CPU** build of ONNX Runtime. For GPU or other
accelerators, skip the extra and install the optimum stack with the
ONNX Runtime build matching your hardware — e.g. in a CUDA Docker image:

```bash
# NVIDIA GPU: onnxruntime-gpu instead of onnxruntime
pip install presidio-analyzer optimum 'optimum-onnx[onnxruntime-gpu]' 'transformers<5'
```

| Hardware | ONNX Runtime build |
|----------|--------------------|
| CPU (default) | `onnxruntime` — via `presidio-analyzer[onnxruntime]` |
| NVIDIA GPU | `optimum-onnx[onnxruntime-gpu]` (pulls `onnxruntime-gpu`) |
| Apple Silicon (CoreML) | `onnxruntime` — CoreML EP ships in the default package |
| Intel CPU/GPU/NPU | `onnxruntime-openvino` (install instead of `onnxruntime`) |
| AMD GPU (ROCm) | `onnxruntime-rocm` (install instead of `onnxruntime`) |

!!! warning "Do not combine the extra with a GPU build"
    `onnxruntime`, `onnxruntime-gpu`, `onnxruntime-openvino`, etc. all
    ship the same Python module and shadow each other when several are
    installed. If you use a non-CPU build, install it *instead of* the
    `[onnxruntime]` extra, not on top of it. To recover from a mixed
    install:

    ```bash
    pip uninstall onnxruntime onnxruntime-gpu onnxruntime-openvino
    pip install onnxruntime-gpu          # the one you actually want
    ```

### YAML — CPU (default ORT)

```yaml
- name: "HF NER (ORT CPU)"
  type: predefined
  class_name: HuggingFaceNerRecognizer
  model_name: optimum/bert-base-NER
  backend: ort
  aggregation_strategy: simple
  threshold: 0.3
  supported_languages: [en]
  supported_entities: [PERSON, LOCATION, ORGANIZATION]
```

For models published under the dual-runtime convention
(`onnx-community/*`, `Xenova/*`) where ONNX files
sit under `onnx/` while config/tokenizer live at the repo root, also
specify `subfolder` and `file_name`:

```yaml
- name: "HF NER (ORT, FP16 ONNX)"
  type: predefined
  class_name: HuggingFaceNerRecognizer
  model_name: onnx-community/stanford-deidentifier-base-ONNX
  backend: ort
  subfolder: onnx
  file_name: model_fp16.onnx     # or model.onnx, model_quantized.onnx, model_int8.onnx, ...
  aggregation_strategy: simple
  threshold: 0.3
```

The recognizer pre-loads the ORT model with these kwargs scoped to the
model loader, so they don't leak into transformers' tokenizer/config
loading.

### YAML — NVIDIA GPU

Install `onnxruntime-gpu` and select the CUDA provider:

```yaml
- name: "HF NER (ORT, CUDA)"
  type: predefined
  class_name: HuggingFaceNerRecognizer
  model_name: optimum/bert-base-NER
  backend: ort
  provider: CUDAExecutionProvider
  provider_options:
    - device_id: 0
  aggregation_strategy: simple
  threshold: 0.3
```

For TensorRT (higher throughput, slow first request because of engine
build):

```yaml
- name: "HF NER (ORT, TensorRT)"
  type: predefined
  class_name: HuggingFaceNerRecognizer
  model_name: optimum/bert-base-NER
  backend: ort
  provider: TensorrtExecutionProvider
  provider_options:
    - trt_fp16_enable: true
      trt_engine_cache_enable: true
      trt_engine_cache_path: /var/cache/trt
  aggregation_strategy: simple
  threshold: 0.3
```

### YAML — Intel CPU / iGPU / NPU via OpenVINO

Install `onnxruntime-openvino`:

```bash
pip uninstall onnxruntime onnxruntime-gpu
pip install onnxruntime-openvino
```

Then route through the OpenVINO execution provider:

```yaml
- name: "HF NER (ORT, OpenVINO)"
  type: predefined
  class_name: HuggingFaceNerRecognizer
  model_name: optimum/bert-base-NER
  backend: ort
  provider: OpenVINOExecutionProvider
  provider_options:
    - device_type: CPU      # CPU | GPU | NPU | AUTO
  aggregation_strategy: simple
  threshold: 0.3
```

OpenVINO is most worthwhile on:

- Intel Xeon Scalable (Sapphire Rapids and newer) — its kernels use
  AVX-512 BF16 / AMX instructions that the default CPU EP does not fully
  exploit. Intel publishes substantial speedups for BERT-class models on
  this hardware; actual gains depend heavily on model, sequence length,
  and batch size.
- Intel Arc / iGPU / Data Center GPU Max — native GPU acceleration without
  CUDA.
- Intel NPUs (Meteor Lake, Lunar Lake, Arrow Lake) — currently the only
  practical runtime for on-device NPU inference.

!!! note "Benchmark before adopting"
    The throughput figures published for these providers come from vendor
    benchmarks under favorable conditions (large batches, long
    sequences). Typical Presidio traffic — short texts at low batch
    sizes — usually sees smaller gains, and on generic cloud VMs (where
    the CPU generation isn't guaranteed) the difference over the default
    CPU EP can be negligible. Measure on your target hardware with your
    own traffic shape before committing to a provider.

### Apple Silicon (CoreML)

The default `onnxruntime` package ships the CoreML execution provider on
macOS:

```yaml
- name: "HF NER (ORT, CoreML)"
  type: predefined
  class_name: HuggingFaceNerRecognizer
  model_name: optimum/bert-base-NER
  backend: ort
  provider: CoreMLExecutionProvider
```

On Apple Silicon the torch backend runs on CPU (the recognizer does not
support MPS), so the CoreML EP is the only acceleration path — at the
cost of needing an ONNX model (pre-built or exported).

### AMD GPU (ROCm)

```yaml
- name: "HF NER (ORT, ROCm)"
  type: predefined
  class_name: HuggingFaceNerRecognizer
  model_name: optimum/bert-base-NER
  backend: ort
  provider: ROCMExecutionProvider
```

Requires `onnxruntime-rocm`.

## Picking an ONNX variant

When the repo ships multiple quantized ONNX files (common in
`onnx-community/*`), the precision/quantization knob is the `file_name`,
not a runtime flag:

| File | Precision | Notes |
|------|-----------|-------|
| `model.onnx` | FP32 | Baseline; largest |
| `model_fp16.onnx` | FP16 | ~half the size; benefits from NVIDIA tensor cores, limited CPU support |
| `model_bf16.onnx` | BF16 | Needs BF16-capable hardware (Sapphire Rapids+, recent NVIDIA) |
| `model_int8.onnx` | INT8 (dynamic) | ~quarter the size; aimed at CPU inference |
| `model_quantized.onnx` | INT8 (static) | Pre-calibrated variant of INT8 |
| `model_uint8.onnx` | UINT8 | Similar to INT8 |
| `model_q4.onnx`, `model_q4f16.onnx` | 4-bit | Smallest; expect an accuracy trade-off |

Smaller is not automatically faster — quantized kernels, hardware
support, and accuracy interact. Validate both latency *and* detection
quality (precision/recall on your own data) when switching variants.

Pick by setting `file_name:` in the YAML. Inference precision otherwise
follows what's baked into the ONNX file — there is no separate `dtype`
parameter at the recognizer level.

## Troubleshooting

- **`FileNotFoundError: Could not find any ONNX files`** — the repo uses a
  mixed layout. Set `subfolder: onnx` and a *bare* `file_name`
  (e.g. `model.onnx`, not `onnx/model.onnx`). Path-in-`file_name` does not
  match optimum's resolver even when the file is listed in the error.
- **`OSError: Could not locate onnx/config.json`** — `subfolder` is
  leaking into tokenizer/config loading. Confirm you are on a recognizer
  version that pre-loads `ORTModelForTokenClassification` explicitly; on
  older versions the `subfolder` is passed at the pipeline level and
  breaks mixed-layout repos.
- **`ImportError: cannot import name 'is_offline_mode' from
  'transformers.utils'`** — `optimum-onnx` is incompatible with
  `transformers>=5`. Pin `transformers<5`.
- **Provider not available** at runtime — usually means another ORT
  package (e.g. `onnxruntime` next to `onnxruntime-gpu`) is shadowing the
  one with the provider you want. Uninstall all and reinstall a single
  variant.
- **First TensorRT request is slow** — TRT builds an engine on first use.
  Persist `trt_engine_cache_path` so subsequent processes reuse it.
- **`TypeError: got an unexpected keyword argument 'foo'`** — a key in
  your YAML is being forwarded to the loader and isn't recognized. Stray
  kwargs are no longer silently dropped; the loud failure is intentional.
