# Installing Presidio

## Description

This document describes the installation of the entire
Presidio suite using `pip` (as Python packages) or using `Docker` (As containerized services).

## Using pip

!!! note "Note"

    Consider installing the Presidio python packages
    in a virtual environment like [venv](https://docs.python.org/3/tutorial/venv.html)
    or [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html).

### Supported Python Versions

Presidio is supported for the following python versions:

* 3.10
* 3.11
* 3.12
* 3.13
* 3.14

### PII anonymization on text

For PII anonymization on text, install the `presidio-analyzer` and `presidio-anonymizer` packages
with at least one NLP engine (`spaCy`, `transformers` or `stanza`):

===+ "spaCy (default)"

    ```
    pip install presidio_analyzer
    pip install presidio_anonymizer
    python -m spacy download en_core_web_lg
    ```

=== "Transformers"

    ```
    pip install "presidio_analyzer[transformers]"
    pip install presidio_anonymizer
    python -m spacy download en_core_web_sm
    ```

    !!! note "Note"
        
        When using a transformers NLP engine, Presidio would still use spaCy for other capabilities,
        therefore a small spaCy model (such as en_core_web_sm) is required. 
        Transformers models would be loaded lazily. To pre-load them, see: [Downloading a pre-trained model](./analyzer/nlp_engines/transformers.md#downloading-a-pre-trained-model)

=== "Stanza"

    ```
    pip install "presidio_analyzer[stanza]"
    pip install presidio_anonymizer
    ```


    !!! note "Note"
        
        Stanza models would be loaded lazily. To pre-load them, see: [Downloading a pre-trained model](./analyzer/nlp_engines/spacy_stanza.md#download-the-pre-trained-model).

### GPU acceleration (optional)

For GPU acceleration, install the appropriate dependencies for your hardware:

- **Linux with NVIDIA GPU**: `pip install "spacy[cuda12x]"` (or the version matching your CUDA installation)
- **macOS with Apple Silicon**: MPS is detected automatically, no additional dependencies required.

For detailed GPU setup, verification, and troubleshooting, see [GPU Acceleration](./analyzer/nlp_engines/gpu_usage.md).

### PII redaction in images

For PII redaction in images

1. Install the `presidio-image-redactor` package:

    ```sh
    pip install presidio_image_redactor
    
    # Presidio image redactor uses the presidio-analyzer
    # which requires a spaCy language model:
    python -m spacy download en_core_web_lg
    ```

2. Install an OCR engine. The default version uses the [Tesseract OCR Engine](https://github.com/tesseract-ocr/tesseract).
More information on installation can be found [here](image-redactor/index.md#installation).

## Using Docker

Presidio can expose REST endpoints for each service using Flask and Docker.
To download the Presidio Docker containers, run the following command:

!!! note "Note"

    This requires Docker to be installed. [Download Docker](https://docs.docker.com/get-docker/).

!!! important "Container registry moved to GitHub Packages"

    New Presidio container releases are published to [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) under the [Data Privacy Stack packages organization](https://github.com/orgs/data-privacy-stack/packages). The legacy Microsoft Container Registry images at `mcr.microsoft.com/presidio-*` are no longer updated. If you previously used `mcr.microsoft.com/presidio-analyzer:latest`, switch to `ghcr.io/data-privacy-stack/presidio-analyzer:latest`; for production, prefer pinning an explicit release tag from the package page.

### For PII anonymization in text

For PII detection and anonymization in text, the `presidio-analyzer`
and `presidio-anonymizer` modules are required.

```sh
# Download Docker images
docker pull ghcr.io/data-privacy-stack/presidio-analyzer
docker pull ghcr.io/data-privacy-stack/presidio-anonymizer

# Run containers with default ports
docker run -d -p 5002:3000 ghcr.io/data-privacy-stack/presidio-analyzer:latest

docker run -d -p 5001:3000 ghcr.io/data-privacy-stack/presidio-anonymizer:latest
```

### For PII redaction in images

For PII detection in images, the `presidio-image-redactor` is required.

```sh
# Download Docker image
docker pull ghcr.io/data-privacy-stack/presidio-image-redactor

# Run container with the default port
docker run -d -p 5003:3000 ghcr.io/data-privacy-stack/presidio-image-redactor:latest
```

Once the services are running, their APIs are available.
API reference and example calls can be found [here](api.md).

### Hardened distroless images

Both `presidio-analyzer` and `presidio-anonymizer` are also published as
distroless variants, built on
[Microsoft Azure Linux distroless](https://github.com/microsoft/azurelinux).
They are functionally identical to the default images, but ship no shell, no
package manager and no build tooling, which removes almost the entire operating
system attack surface.

Use them if your organization runs container vulnerability or compliance
scanning (for example Microsoft Defender for Cloud or S360) against the Presidio
images.

```sh
docker pull ghcr.io/data-privacy-stack/presidio-analyzer:latest-distroless
docker pull ghcr.io/data-privacy-stack/presidio-anonymizer:latest-distroless

docker run -d -p 5002:3000 ghcr.io/data-privacy-stack/presidio-analyzer:latest-distroless
docker run -d -p 5001:3000 ghcr.io/data-privacy-stack/presidio-anonymizer:latest-distroless
```

The distroless variants differ from the default images in three ways:

* **No shell.** The `PORT` and `WORKERS` environment variables are not used,
  because there is no shell to expand them. Gunicorn is started directly, and is
  configured through `GUNICORN_CMD_ARGS`, which defaults to
  `--workers=1 --bind=0.0.0.0:3000`:

    ```sh
    docker run -d -p 5001:3000 \
      -e GUNICORN_CMD_ARGS="--workers=4 --bind=0.0.0.0:3000 --timeout=120" \
      ghcr.io/data-privacy-stack/presidio-anonymizer:latest-distroless
    ```

    For the same reason, `docker exec ... sh` is not available. Use the default
    images if you need to run commands inside the container.

* **Python 3.12.** Azure Linux distroless publishes Python 3.12 only. This
  matches the default analyzer image; the default anonymizer image runs Python
  3.14. Both packages support Python 3.10 through 3.14, so the runtime version
  does not change behavior.

* **Runs as UID 65532**, the base image's `nonroot` user, rather than UID 1001.
  Adjust any volume permissions or Kubernetes `runAsUser` settings accordingly.

There is no distroless variant of `presidio-image-redactor`: it depends on the
Tesseract OCR system packages, which a distroless base image cannot provide.

### Keeping images patched

Images pin their base image by digest, so a published image never picks up
operating system security updates on its own. The
[Rebuild Images](https://github.com/data-privacy-stack/presidio/actions/workflows/rebuild-images.yml)
workflow rebuilds and republishes every image weekly on top of a freshly patched
base, without changing any application code. Each rebuild also publishes an
immutable `<version>-<date>` tag, for example `2.2.364-20260909-distroless`, so
you can pin an exact rebuild and roll back to it if needed.

## Install from source

To install Presidio from source, first clone the repo:

* using HTTPS

```sh
git clone https://github.com/data-privacy-stack/presidio.git
```

* Using SSH

```sh
git clone git@github.com:data-privacy-stack/presidio.git
```

Then, build the containers locally.

!!! note "Note"
    Presidio uses [docker-compose](https://docs.docker.com/compose/) to manage the different Presidio containers.

From the root folder of the repo:

```sh
docker-compose up --build
```

Alternatively, you can build and run individual services.
For example, for the `presidio-anonymizer` service:

```sh
docker build ./presidio-anonymizer -t presidio/presidio-anonymizer
```

And run:

```sh
docker run -d -p 5001:5001 presidio/presidio-anonymizer
```

---

For more information on developing locally,
refer to the [setting up a development environment](development.md) section.
