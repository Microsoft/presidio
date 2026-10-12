# Setting Up a Development Environment

## Getting started

### Cloning the repo

To create a local copy of Presidio repository, follow [Github instructions](https://docs.github.com/en/github/creating-cloning-and-archiving-repositories/cloning-a-repository)
on how to clone a project using git.
The project is structured so that:

- Each Presidio service has a designated directory:
  - The service logic.
  - Tests, both unit and integration.
  - Serving it as an HTTP service (found in app.py).
  - Python Packaging setup script (setup.py).
- In the project root directory, you will find common code for using, serving and testing Presidio
    as a cluster of services, as well as CI/CD pipelines codebase and documentation.

### Setting up uv

[uv](https://docs.astral.sh/uv/) is the Python package manager used to manage dependencies and virtual
environments for Presidio services (the CI installs dependencies the same way).
Follow these steps when starting to work on a Presidio service with uv:

1. Install uv

    - Using the standalone installer (you can inspect [install.sh](https://astral.sh/uv/install.sh) before running it)

        ```sh
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```

    - Using Homebrew (in MacOS)

        ```
        brew install uv
        ```

    Additional installation instructions for uv: <https://docs.astral.sh/uv/getting-started/installation/>

2. Have uv create a virtualenv for the project and install all requirements in the pyproject.toml,
    including dev requirements.

    For example, in the `presidio-analyzer` folder, run:

    ```
    uv sync --all-extras --group dev
    ```

    Add `--locked` to install the exact locked dependency graph (matching CI behavior).

3. Run all tests:

    ```
    uv run pytest
    ```

4. To run arbitrary scripts within the virtual env, start the command with
    `uv run`. For example:
    1. `uv run ruff check`
    2. `uv run pip freeze`
    3. `uv run python -m spacy download en_core_web_lg`

    Command 3 downloads the default spacy model needed for Presidio Analyzer.

#### Alternatively, [activate the virtual environment](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment) and run the commands without the `uv run` prefix.

### Development guidelines

- A Github issue suggesting the change should be opened prior to a PR.
- All contributions should be documented, tested and linted. Please verify that all tests and lint checks pass successfully before proposing a change.
- To make the linting process easier, you can use [pre-commit hooks](#automatically-format-code-and-check-for-code-styling) to verify and automatically format code upon a git commit
- In order for a pull request to be accepted, the CI (containing unit tests, e2e tests and linting) needs to succeed, in addition to approvals from two maintainers.
- PRs should be small and solve/improve one issue at a time. If you have multiple suggestions for improvement, please open multiple PRs.

### Local build process

After modifying presidio codebase, you might want to build presidio cluster locally, and run tests to spot regressions.
The recommended way of doing so is using docker-compose (bundled with 'Docker Desktop' for Windows and Mac systems,
more information can be found [here](https://docs.docker.com/compose/install/)).
Once installed, to start presidio cluster with all of its services in HTTP mode, run from the project root:

```bash
docker-compose up --build -d
```

!!! note "Note"
    Building for the first time might take some time,
    mainly on downloading the default spacy models.

To validate that the services were built and started successfully,
and to see the designated port for each,
use docker-compose ps:

```bash
>docker-compose ps
CONTAINER ID   IMAGE                       COMMAND                  CREATED         STATUS         PORTS                    NAMES
6d5a258d19c2   presidio-anonymizer         "./entrypoint.sh"   6 minutes ago   Up 6 minutes   0.0.0.0:5001->5001/tcp   presidio_presidio-anonymizer_1
9aad2b68f93c   presidio-analyzer           "./entrypoint.sh"   2 days ago      Up 6 minutes   0.0.0.0:5002->5001/tcp   presidio_presidio-analyzer_1
1448dfb3ec2b   presidio-image-redactor     "./entrypoint.sh"   2 seconds ago   Up 2 seconds   0.0.0.0:5003->5001/tcp   presidio_presidio-image-redactor_1
```

Edit docker-compose.yml configuration file to change the default ports.

Starting part of the cluster, or one service only, can be done by stating its image name as argument for docker-compose.
For example for analyzer service:

```bash
docker-compose up --build -d presidio-analyzer
```

### Testing

We strive to have a full test coverage in Presidio, and expect every pull request to
include tests.

In each service directory, a 'test' directory can be found. In it, both unit tests,
for testing single files or classes, and integration tests, for testing integration
between the service components, or integration with external packages.

#### Basic conventions

For tests to be consistent and predictable, we use the following basic conventions:

1. Treat tests as production code. Keep the tests concise and readable, with descriptive namings.
2. Assert on one behavior at a time in each test.
3. Test names should follow a pattern of `test_when_[condition_to_test]_then_[expected_behavior]`.
   For example: `test_given_an_unknown_entity_then_anonymize_uses_defaults`.
4. Use [test doubles and mocks](https://docs.pytest.org/en/stable/monkeypatch.html)
   when writing unit tests. Make less use of them when writing integration tests.

#### Running tests

Presidio uses the [pytest](http://doc.pytest.org/) framework for testing.
See the pytest [documentation](https://docs.pytest.org/en/latest/contents.html)
for more information.

Running the tests locally can be done in two ways:

1. Using cli, from each service directory, run:

    ```sh
    uv run pytest
    ```

2. Using your IDE.
   See configuration examples for
   [JetBrains PyCharm / IntelliJ IDEA](https://www.jetbrains.com/help/pycharm/creating-run-debug-configuration-for-tests.html)
   and [Visual Studio Code](https://code.visualstudio.com/docs/python/testing)

#### End-to-end tests

Since Presidio services can function as HTTP servers, Presidio uses an additional
end-to-end (e2e) testing layer to test their REST APIs.
This e2e test framework is located under 'e2e-tests' directory.
In it, you can also find test scenarios testing the integration between
Presidio services through REST API.
These tests should be annotated with 'integration' pytest marker `@pytest.mark.integration`,
while tests calling a single service API layer should be annotated with 'api'
pytest marker `@pytest.mark.api`.

Running the e2e-tests locally can be done in two ways:

1. Using cli, from e2e-tests directory, run:

    On Mac / Linux / WSL:

    ```sh
    # Create a virtualenv named presidio-e2e (needs to be done only on the first run)
    python -m venv presidio-e2e
    # Activate the virtualenv
    source presidio-e2e/bin/activate
    # Install e2e-tests requirements using pip
    pip install -r requirements.txt
    # Run pytest
    pytest
    # Deactivate the virtualenv
    deactivate
    ```

    On Windows CMD / Powershell:

    ```shell
    # Create a virtualenv named presidio-e2e (needs to be done only on the first run)
    py -m venv presidio-e2e
    # Activate the virtualenv
    presidio-e2e\Scripts\activate
    # Install e2e-tests requirements using pip
    pip install -r requirements.txt
    # Run pytest
    pytest
    # Deactivate the virtualenv
    deactivate
    ```

2. Using your IDE

    See references in the section above.

!!! note "Note"
    The e2e tests require a Presidio cluster to be up, for example using the containerized cluster with docker-compose.

### Linting

Presidio services are PEP8 compliant and continuously enforced on style guide issues during the build process using `ruff`, in turn running `flake8` and other linters.

Running ruff locally, using `uv run ruff check`, you can check for those issues prior to committing a change.

Ruff runs linters in addition to the basic `flake8` functionality, Presidio uses linters as part as ruff such as:

- _pep8-naming_: To check that variable names are PEP8 compliant.
- _flake8-docstrings_: To check that docstrings are compliant.

### Automatically format code and check for code styling

To make the linting process easier, you can use pre-commit hooks to verify and automatically format code upon a git commit, using `ruff-format`:

1. [Install pre-commit package manager locally.](https://pre-commit.com/#install)

2. From the project's root, enable pre-commit, installing git hooks in the `.git/` directory by running: `pre-commit install`.

3. Commit non PEP8 compliant code will cause commit failure and automatically
    format your code using, as well as checking code formatting using `ruff`

```sh
[INFO] Initializing environment for https://github.com/astral-sh/ruff-pre-commit.
[INFO] Installing environment for https://github.com/astral-sh/ruff-pre-commit.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
ruff.....................................................................Passed
ruff-format..............................................................Failed
- hook id: ruff-format
- files were modified by this hook
  5 files reformatted, 4 files left unchanged
```

4. Committing again will finish successfully, with a well-formatted code.
