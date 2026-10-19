# Contributing to `pybemobil`

Thanks for contributing! Bug reports, feature requests and pull requests are
all welcome. To report a bug or suggest a feature, please
[open an issue](https://github.com/BeMoBIL/pybemobil/issues). This guide
describes how to set up a development environment, how we work with branches
and pull requests, how to run the tests, and how we cut a release.

## Setup

1. Fork the repo on GitHub, then clone your fork and add the main repo as
   `upstream`:

    ```bash
    git clone https://github.com/<your-username>/pybemobil.git
    cd pybemobil
    git remote add upstream https://github.com/BeMoBIL/pybemobil.git
    ```

2. Install in editable mode with the development extras, ideally in a fresh
   environment (e.g. `conda create -n pybemobil python=3.12`):

    ```bash
    pip install -e ".[dev]"
    ```

3. Install the pre-commit hooks (formatting and linting run on every commit):

    ```bash
    pre-commit install
    ```

## Workflow

1. Create a branch from an up-to-date `main`:

    ```bash
    git fetch upstream
    git checkout -b your-git-name/short-description upstream/main
    ```

2. Make your changes and commit often with clear messages.
3. Push your branch to your fork:

    ```bash
    git push -u origin your-git-name/short-description
    ```

4. Open a pull request from your fork against `main` of BeMoBIL/pybemobil.
5. A maintainer will review your pull request before merging.

### Branch naming

| Type | Pattern | Example |
| ------ | --------- | --------- |
| Feature | `name/feature-desc` | `robin/add-ica-pipeline` |
| Fix | `name/fix-desc` | `alex/fix-montage-rotation` |
| Experiment | `name/exp-desc` | `maria/exp-zapline-threshold` |

### Pull requests

- All changes go into `main` via pull requests (PRs). Never push directly to
  `main`; keep your fork's `main` a clean mirror of `upstream/main`.
- Keep PRs focused: one logical change per PR. Two unrelated changes should
  go into separate PRs where possible.
- Give the PR a meaningful title and a short description of what changed and
  why. The title becomes the commit message on `main`.
- PRs are merged with **"Squash and merge"**, so each commit on `main` refers
  to one PR. GitHub links back to the PR, so the discussion, review and
  individual commits stay visible there, and the history on `main` stays
  clean.
- Within a PR, keep your own commits atomic and well described to make review
  easier.
- PRs are expected to pass `pytest` (without `--runslow`) in CI.

## Testing

Tests live in `tests/`. Run the suite from the repo root:

```bash
pip install -e ".[test]"   # first time only (already included in [dev])
pytest                     # fast tests only (default)
pytest --runslow           # include slow integration tests
```

Coverage runs automatically and produces an HTML report in `htmlcov/`. Open
`htmlcov/index.html` in a browser after the run.

### Test structure

`tests/conftest.py` defines shared fixtures (synthetic `tiny_raw`,
`motion_raw`, and the EEGBCI `sample_raw` used by slow tests) and registers two
custom markers.

| Marker | Meaning |
| ------ | ------- |
| `@pytest.mark.slowtest` | Integration test that downloads data or fits models. Skipped by default; run with `--runslow`. |
| `@pytest.mark.requires_data` | Test that depends on external data files. Skipped when paths are absent. |

Each test module maps to one source module:

| Test file | Source module |
| ----------- | -------------- |
| `test_alignment.py` | `io/alignment.py` |
| `test_bids_export.py` | `io/bids_export.py` |
| `test_xdf_helpers.py` | `io/xdf.py` (private helpers) |
| `test_epoching.py` | `preproc/epoching.py` |
| `test_make_report.py` | `preproc/make_report.py` |
| `test_motion.py` | `preproc/motion.py` |
| `test_preprocessing.py` | `preproc/preprocessing.py` |
| `test_utils.py` | `preproc/utils.py` |
| `test_plotting.py` | `viz/plotting.py` |

### Testing convention

Every significant change to a public function must come with at least one
test. Fast unit tests (synthetic data, no I/O) are the default. Integration
tests that touch real files or run the full pipeline are marked
`@pytest.mark.slowtest` and kept in the same test module as the unit tests for
that module.

## How to make a release

Releases are published to PyPI automatically by `.github/workflows/release.yml`
via [trusted publishing](https://docs.pypi.org/trusted-publishers/), so no API
tokens are needed.

1. Update `doc/source/whats_new.rst`: move the "Unreleased" entries under a
   heading for the new version and note any behaviour changes.
2. Optional dry run on TestPyPI: in the GitHub Actions tab, open the
   **Release** workflow and click **Run workflow** on `main`. This uploads a dev
   build (a `.devN` version) to <https://test.pypi.org/project/pybemobil/>.
   Check it installs in a fresh environment:
   `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ --pre pybemobil`
3. Make sure you have a git remote `upstream` configured to point to
   <https://github.com/BeMoBIL/pybemobil>.
4. From your (clean!) `main` branch, run:
   1. `git fetch --all --tags --prune --prune-tags`
   2. `git rebase upstream/main`
   3. `git push`
5. Tag the current version, following [semantic versioning](https://semver.org/).
   For example, for `v0.1.0`, use:
   `git tag -a -m "v0.1.0" v0.1.0 upstream/main`
   (always prepend a `v` to the version!).
6. Push the tag upstream: `git push --follow-tags upstream`.
7. Make a release on GitHub: select the pushed tag, name the release after the
   tag, and let GitHub generate the release notes automatically. Paste the
   matching section of `whats_new.rst` at the top. Publishing the release
   uploads the package to PyPI.
