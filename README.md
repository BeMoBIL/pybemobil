# pybemobil

MoBI data loading, preprocessing, and visualization built on MNE-Python.

## Structure

```md
pybemobil/
├── io/                          # Data I/O
│   ├── xdf.py                   # XDFLoader: multimodal XDF loading, stream alignment
│   ├── alignment.py             # align_stream_to_timestamps (timestamp-aware interpolation)
│   ├── bids_export.py           # BIDS export wrappers around mne_bids
│   └── utils.py                 # I/O helpers
├── preproc/                     # Preprocessing
│   ├── preprocessing.py         # EEGPreprocessor: ZapLine -> bad ch -> filter -> ASR -> ICA pipeline
│   ├── epoching.py              # EpochPreparer, stimulus renaming helpers
│   ├── motion.py                # Rigid body kinematics (find, process, split)
│   └── utils.py                 # ASR, ZapLine, ICA, dipole fitting, provenance, misc
├── viz/                         # Visualization
│   ├── plotting.py              # ERP, PSD, and component plots
│   └── utils.py                 # Plot helpers
├── examples/                    # Runnable example scripts
│   ├── preprocessing.py         # Full EEG preprocessing walkthrough
│   ├── plotting.py               # Visualization walkthrough (run preprocessing.py first)
│   ├── xdf_loading.py           # XDF multimodal loading
│   ├── motion_processing.py     # Rigid body kinematics
│   └── bids_export_example.py   # BIDS export
└── data/
    └── montages/                # EEG electrode montage files (.elc, .fif)
```

## Modules

**`io`** - Load XDF multimodal recordings into MNE Raw objects, align auxiliary streams (ECG, gaze, EMG, EDA) to a common time grid, and export datasets to BIDS.

**`preproc`** - Full EEG preprocessing pipeline (bandpass, bad channel detection, ASR, ICA, dipole fitting), epoch preparation, and rigid body motion capture kinematics.

**`viz`** - ERP and PSD plotting utilities built on MNE and matplotlib.

**`examples`** - Self-contained scripts demonstrating major features. Run directly or open as notebooks (percent-format cells).

## Installation

Install the latest release from PyPI:

```bash
pip install pybemobil
```

To also install the JAX-accelerated AMICA backend (the default ICA method, which falls back to Picard when this is missing):

```bash
pip install "pybemobil[jamica]"
```

Alternatively:

- **Latest development version** from GitHub:

    ```bash
    pip install git+https://github.com/BeMoBIL/pybemobil.git
    ```

- **From source**, in editable mode (for development):

    ```bash
    git clone https://github.com/BeMoBIL/pybemobil.git
    cd pybemobil
    pip install -e ".[dev]"
    ```

We recommend installing into a fresh environment, e.g. `conda create -n pybemobil python=3.12`.

## Quick start

```python
from pybemobil.io import XDFLoader
from pybemobil.preproc import EEGPreprocessor

# Load a multimodal XDF recording
loader = XDFLoader(montage="easycap-M1")  # or a path to your .elc/.fif
recording = loader.load("sub-01_task-walk_run-01.xdf")

# Run the full preprocessing pipeline; outputs are named after fname_out
preprocessor = EEGPreprocessor(loader=loader)
raw_clean, report, metadata = preprocessor.run_raw(
    recording.raw,
    fname_out="derivatives/pybemobil/sub-01/eeg/sub-01_task-walk_run-01_eeg.fif",
)
```

See `pybemobil/examples/` for complete worked examples:

| Feature | Example script |
| --------- | --------------- |
| XDF multimodal loading | `pybemobil/examples/xdf_loading.py` |
| EEG preprocessing pipeline | `pybemobil/examples/preprocessing.py` |
| Visualization (run preprocessing.py first) | `pybemobil/examples/plotting.py` |
| Rigid body kinematics | `pybemobil/examples/motion_processing.py` |
| BIDS export | `pybemobil/examples/bids_export_example.py` |

## Citing

If you use pybemobil in your work, please cite it. The "Cite this repository" button on GitHub (generated from [`CITATION.cff`](https://github.com/BeMoBIL/pybemobil/blob/main/CITATION.cff)) gives the reference in APA and BibTeX format.

pybemobil is a Python implementation of the BeMoBIL pipeline, so please consider also citing:

> Klug, M., Jeung, S., Wunderlich, A., Gehrke, L., Protzak, J., Djebbara, Z., Argubi-Wollesen, A., Wollesen, B., & Gramann, K. (2022). The BeMoBIL Pipeline for automated analyses of multimodal mobile brain and body imaging data. *bioRxiv*. https://doi.org/10.1101/2022.09.29.510051

## License

pybemobil is released under the [BSD 3-Clause License](https://github.com/BeMoBIL/pybemobil/blob/main/LICENSE).

## Contributing

Contributions are welcome! To report a bug or suggest a feature, please [open an issue](https://github.com/BeMoBIL/pybemobil/issues). For development setup, the pull request workflow, testing and releases, see [CONTRIBUTING.md](https://github.com/BeMoBIL/pybemobil/blob/main/.github/CONTRIBUTING.md).
