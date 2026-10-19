What's new
==========

Unreleased
----------

- AMICA's likelihood-based sample rejection is now on by default when ICA runs
  with ``jamica`` (``{"do_reject": True, "rejsig": 3.0, "numrej": 10}``),
  matching the MATLAB BeMoBIL pipeline (``AMICA_autoreject=1``, 3 SD,
  10 rounds). Previously no outlier rejection was applied during ICA, so ICA
  results will differ from 0.1.0. ``fit_params`` passed in ``jamica_kwargs``
  are merged over these defaults; use
  ``jamica_kwargs={"fit_params": {"do_reject": False}}`` for the old
  behaviour. The number of rejected samples is recorded in the provenance
  descriptor (``amica_rejected_samples``).
- The :ref:`comparison with the MATLAB pipeline <guide-bemobil>` was corrected:
  bad channel detection parameters, filtering differences, output files and a
  working minimal example.

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
