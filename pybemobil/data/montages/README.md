# Note regarding montages

Matlab and Python assume different coordinate systems for EEG electrode positions. The original `standard_MoBI_128.elc` file is in the Matlab coordinate system, which can lead to incorrect electrode placements when used in Python.

When using the montage in Python, please ensure that you use the corrected version (`standard_MoBI_128_corrected.fif`) to avoid any discrepancies in electrode placements.

The files are installed with the package. To use the corrected montage:

```python
from importlib.resources import files

from pybemobil.io import XDFLoader

montage_dir = files("pybemobil") / "data" / "montages"
loader = XDFLoader(montage=montage_dir / "standard_MoBI_128_corrected.fif")
# or: mne.channels.read_dig_fif(montage_dir / "standard_MoBI_128_corrected.fif")
```

**Dipole fitting:** the corrected montage has no fiducials (nasion, LPA,
RPA) and its coordinate frame is unknown, so MNE assumes the positions are
already in head coordinates. Its electrode centre lies about 3 cm higher than
that of MNE's template montages, so dipoles fitted against the fsaverage head
model may be shifted. pybemobil warns when dipoles are fitted on positions
without fiducials. For source-level results use digitised electrode positions
with fiducials, or check the alignment with `mne.viz.plot_alignment` first.

Whenever you work with a montage the first time, load and plot it (montage.plot()) to verify that the electrode positions are correct. If you notice any discrepancies, please correct the coordinates and save the corrected montage.
