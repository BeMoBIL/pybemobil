What's new
==========

Unreleased
----------

Nothing yet.

0.2.0
-----

A release that fixes the problems found in a full review of 0.1.0. Many of
them changed results silently, so **results differ from 0.1.0**, in
particular sampling rates and event times of XDF recordings with dropouts,
bad channels, ICA and the selected components. Re-run analyses made with
0.1.0.

Behaviour changes
~~~~~~~~~~~~~~~~~

- **XDF timing.** :class:`~pybemobil.io.XDFLoader` uses the EEG stream's
  nominal sampling rate. Dropouts are filled with interpolated samples and
  annotated ``BAD_eeg_missing``, and markers are placed by sample index, so
  events stay on the right samples after a dropout or with clock drift.
  Before, a single dropout lowered the sampling rate (a 2 s gap in a 10 s,
  500 Hz recording gave 400 Hz). The new
  ``MultimodalRecording.eeg_timestamps`` maps Tier-2 and event timestamps
  onto Raw times. Voltage units of auxiliary streams are now converted to
  volts too (a microvolt ECG was stored 1e6 too large).
- **AMICA sample rejection** is on by default when ICA runs with ``jamica``
  (``{"do_reject": True, "rejsig": 3.0, "numrej": 10}``), as in the MATLAB
  pipeline. Use ``jamica_kwargs={"fit_params": {"do_reject": False}}`` for
  the old behaviour. The number of rejected samples is recorded in the
  provenance (``amica_rejected_samples``).
- **Bad channels.** :func:`~pybemobil.preproc.get_bad_chs` works on a copy
  high-passed at 1 Hz (new ``highpass`` parameter), finds flat channels
  before the average reference and runs the line-noise criterion before the
  notch filter. It warns when more than ``max_bad_fraction`` (default 0.2) of
  the EEG channels is flagged.
- **Final reference.** :class:`~pybemobil.preproc.EEGPreprocessor`
  interpolates bad channels first and then average-references all EEG
  channels, as in BeMoBIL, so the cleaned EEG sums to zero at every sample.
- **ICLabel selection.** In probability-threshold mode (``0 <= thresh <= 1``)
  an IC is removed only when its winning class is one to remove *and* its
  probability reaches ``thresh``; uncertain ICs are kept. Before, every IC
  below the threshold was removed. :func:`~pybemobil.preproc.compute_ica`
  now uses the pipeline's defaults: popularity vote, keep all classes except
  ``"eye blink"``, and a 1.75 Hz high-pass. Unknown class names raise.
- **Epoching.** :class:`~pybemobil.preproc.EpochPreparer` no longer shifts
  events by 60 ms by default (``tshift=0``); set the delay of your own setup.
- **Motion.** :func:`~pybemobil.preproc.process_rigid_body` uses BeMoBIL's
  low-pass defaults (6 Hz, and 18 Hz after differentiation), bridges motion
  capture dropouts before filtering, takes ``angle_unit="deg"`` for Euler
  angles in degrees, and computes acceleration without velocity.
- **Dipoles.** ``trans="fit"`` fits a rigid transform (it estimated a head
  scale that was then ignored). A warning is shown when electrode positions
  have no fiducials.
- **Reproducibility.** Without ``rng_seed``, each run draws a seed and records
  it in the provenance, together with the ICA method actually used, its
  parameters and the epochs FASTER dropped.
- Optional dependencies no longer fail silently: missing ``jamica`` gives a
  visible warning, and missing ``mne-denoise`` or ``meegkit`` raises.
- ``overwrite=True`` removes all derivatives of an earlier run first, and
  ``overwrite=False`` fails before processing instead of after it. Report
  figures are saved in a ``*_figures/`` folder.

Removed and renamed
~~~~~~~~~~~~~~~~~~~

- ``XDFLoader(on_mismatch="crop")`` was removed: with many streams and
  frequent dropouts, cropping to the overlap of all streams discards usable
  EEG. ``"pad"`` is the only option.
- ``plot_ERSP`` was removed; use :func:`~pybemobil.viz.plot_TFR`.
- The misspelled ``EpochPreparer(epoch_tlimes=...)`` is now ``epoch_tlims``.
- ``pybemobil.viz.utils`` and the private names in ``pybemobil.preproc``'s
  ``__all__`` were removed. The environment variable for the report's
  parallel jobs is now ``PYBEMOBIL_REPORT_N_JOBS`` (was
  ``BPN_REPORT_N_JOBS``).

Bug fixes
~~~~~~~~~

- Text from the data (marker names, channel names, labels) is escaped in the
  HTML report.
- :func:`~pybemobil.viz.plot_various_ERPs` works with a subtraction event
  and other events; :func:`~pybemobil.viz.plot_PSD` shows confidence bands
  across epochs for a single object and accepts ``Spectrum`` baselines;
  :func:`~pybemobil.viz.plot_ERP` draws baseline and ROI spans on every
  axis; :func:`~pybemobil.viz.plot_TFR` works on ICA sources without picks.
- :func:`~pybemobil.preproc.get_bad_chs` works at sampling rates of about
  100 Hz and names channels with NaN values.
- :func:`~pybemobil.io.make_bids_dataset_description` leaves unset fields
  out, and :func:`~pybemobil.io.batch_export_to_bids` warns about failed
  runs (``on_error="raise"`` stops at the first one).
- ``NumpyEncoder`` handles numpy integers and bools; the report's 3-D
  co-registration plot is no longer skipped on macOS; fsaverage is only
  downloaded when needed, and ``SUBJECTS_DIR`` is no longer set.
- XDFLoader options are validated, so typos raise instead of silently
  falling back to defaults.

Other changes
~~~~~~~~~~~~~

- Lower memory use. A pipeline run with the report needed up to 12 times
  the size of the recording in memory; now it needs about 10 times
  (measured on a 10 min recording), and the saving grows with the length of
  the recording. Bad-channel detection copies only the EEG channels, and
  the ICA section of the report is built from at most 300 one-second epochs
  spread over the recording instead of all of it, so its plots show a
  sample of the data.
- Dependencies: ``scipy`` and ``Pillow`` are declared, ``mne-denoise>=0.0.3``
  is required, and ``seaborn`` is the optional ``report`` extra (``pandas``
  is no longer required).
- The :ref:`comparison with the MATLAB pipeline <guide-bemobil>` was
  corrected (bad-channel parameters, filtering, output files and a working
  minimal example).
- Documentation that disagreed with the code was corrected, the Zenodo DOI
  is in ``CITATION.cff`` and the README, and the examples write their output
  to the working directory.
- CI tests on macOS too, and releases are only published when the tests
  pass.

0.1.0
-----

First public release of pybemobil, a Python implementation of the MATLAB
`BeMoBIL pipeline <https://github.com/BeMoBIL/bemobil-pipeline>`_ built on
MNE-Python.

Highlights
~~~~~~~~~~

- :class:`~pybemobil.io.XDFLoader` loads multimodal XDF recordings and aligns
  auxiliary streams (ECG, gaze, EMG, EDA, motion) to a common time grid.
- :class:`~pybemobil.preproc.EEGPreprocessor` runs the full EEG pipeline
  (ZapLine-plus, bad channel detection, filtering, optional ASR, ICA with
  ICLabel, dipole fitting) with provenance tracking and an HTML report.
- :func:`~pybemobil.io.export_to_bids` exports datasets to BIDS.
- Rigid body motion processing, epoching helpers and plotting utilities.
- The MoBI 128-channel montage ships with the package in
  ``pybemobil/data/montages``.

Changes for users of development versions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you used a pre-release snapshot (previously named ``bemobil-mne``), note:

- The package is renamed: ``pip install pybemobil`` and
  ``import pybemobil`` replace ``bemobil-mne`` / ``bemobil_mne``.
  Derivatives are now written to ``derivatives/pybemobil/``.
- ``EEGPreprocessor.run()`` keeps the montage set by the loader instead of
  always applying the 10-05 template.
- ``get_bad_chs(notch_lines=None)`` now skips notch filtering. The default is
  still ``"europe"``.
- ``metadata["raw_source"]`` is the caller's own object.
- PSD plots use density normalization (``normalization="length"``), so
  values are scaled by the sampling frequency compared to before.
- Euler angles from rigid body processing are unwrapped by default
  (``unwrap=True``).
- Montage files moved to ``pybemobil/data/montages`` and are now included
  in the wheel.
- The default 10-05 template is ``colin27_1005`` on MNE versions where
  ``standard_1005`` was removed.
- Requires Python 3.11 or newer and MNE-Python 1.13 or newer.
