.. _guide-bemobil:

Comparison with the BeMoBIL pipeline
=====================================

The `BeMoBIL pipeline <https://github.com/BeMoBIL/bemobil-pipeline>`_ (Klug et al., 2022)
is a widely-used MATLAB toolbox for automated MoBI data analysis.  PyBeMoBIL is its
Python/MNE counterpart, designed to produce equivalent results while integrating with the
broader scientific Python ecosystem.

This page describes what the two pipelines share, where they differ and why, and shows a
side-by-side minimal example.

----

Overview
--------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * -
     - MATLAB BeMoBIL pipeline
     - PyBeMoBIL
   * - Language
     - MATLAB
     - Python
   * - EEG framework
     - EEGLAB
     - MNE-Python
   * - ICA
     - AMICA (native MATLAB)
     - AMICA via ``jamica`` (falls back to picard)
   * - IC classification
     - ICLabel (EEGLAB plugin)
     - ``mne-icalabel``
   * - Line-noise removal
     - ZapLine-Plus (auto-detect)
     - ZapLine-Plus via ``mne-denoise`` (``line_noise_method="adaptive"``)
   * - Bad channel detection
     - ``clean_rawdata`` (ASR-based correlation)
     - PyPREP + FASTER + optional line-noise criterion
   * - Outlier rejection for ICA
     - AMICA sample rejection (``AMICA_autoreject=1``)
     - AMICA sample rejection via ``jamica`` (on by default); ASR optional
   * - BIDS support
     - Manual / separate toolbox
     - Built-in via ``mne-bids``
   * - Provenance
     - ``EEG.etc`` struct fields
     - JSON descriptor in ``raw.info["description"]``
   * - Output format
     - ``.set`` / ``.fdt`` (EEGLAB)
     - FIF (``.fif``, or ``.fif.gz``) as BIDS derivatives

----

Shared defaults
---------------

The following preprocessing parameters are set to match the original MATLAB implementation's published defaults
(``bemobil_check_config.m``):

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Setting
     - MATLAB BeMoBIL
     - PyBeMoBIL
   * - Resample for ICA
     - 250 Hz
     - ``downsample_ica=250.0``
   * - ICA high-pass filter
     - 1.75 Hz
     - ``filter_bands_ica=(1.75, None)``
   * - AMICA sample rejection
     - on, 3 SD, 10 rounds (``AMICA_autoreject=1``,
       ``AMICA_reject_sigma_threshold=3``, ``AMICA_n_rej=10``)
     - ``jamica_kwargs={"fit_params": {"do_reject": True, "rejsig": 3.0, "numrej": 10}}``
   * - ZapLine mode
     - auto-detect (``noisefreqs=[]``)
     - ``line_noise_method="adaptive"``
   * - ICLabel decision rule
     - popularity vote (``iclabel_threshold=-1``)
     - ``thresh=-1``
   * - ICs kept
     - all except Eye (classes 1,2,4,5,6,7)
     - ``include_labels`` = all except ``"eye blink"``
   * - Line-noise bad-ch criterion
     - off
     - ``line_noise_crit=None``
   * - Dipole RV threshold
     - 100 % (no threshold)
     - ``rv_thresh=None``
   * - Remove outside-head dipoles
     - off
     - ``remove_outside_head=False``

----

Intentional differences
------------------------

**Bad channel detection method**
   The original MATLAB implementation detects bad channels with ``clean_rawdata``'s channel
   criteria on average-referenced data: a channel is flagged if it correlates below
   ``chancorr_crit=0.8`` with its robust estimate from the other channels for more than
   ``chan_max_broken_time=0.5`` of the recording (flatline and line-noise criteria are off).
   Because this estimate is randomized, detection is repeated ``chan_detect_num_iter=20``
   times and a channel is rejected if it was flagged in at least
   ``chan_detected_fraction_threshold=0.5`` of the runs. ``num_chan_rej_max_target=1/5``
   is a soft target: if more than a fifth of the channels pass that threshold, the
   threshold is raised so that roughly a fifth are rejected (ties can still add more).

   PyBeMoBIL uses PyPREP (NaN/flat, deviation, high-frequency noise, correlation and, when
   a montage is set, RANSAC) combined with FASTER's channel correlation and variance
   criteria, plus an optional line-noise criterion (see
   :func:`~pybemobil.preproc.get_bad_chs`), on a 1 Hz high-passed, average-referenced copy
   of the data (flat channels are found before referencing). It runs once and has no
   iteration. Instead of raising the threshold like ``num_chan_rej_max_target``, it warns
   when more than a fifth of the channels is flagged (``max_bad_fraction=0.2``). Both
   approaches flag channels that stop correlating with their neighbours, but the exact
   channels detected can differ.

**ASR**
   The original MATLAB implementation does not apply ASR; it relies on AMICA's built-in
   sample rejection (``AMICA_autoreject=1``, 3 SD, 10 rejection rounds). PyBeMoBIL does the
   same: ASR is off by default (``asr=False``), and when ICA runs with ``jamica`` (the
   default), AMICA's sample rejection is on with the same settings. Pass
   ``jamica_kwargs={"fit_params": {"do_reject": False}}`` to turn it off. ASR is available
   as an opt-in (``asr=True`` or ``asr={"cutoff": 20}``), e.g. when ICA falls back to
   picard, which has no sample rejection.

**Filtering**
   The original MATLAB implementation does not filter the continuous data before ICA. Only
   the copy used to fit AMICA is high-passed at 1.75 Hz (FIR, order 1650), and after the
   ICA solution is copied back, a final 0.2 Hz high-pass is applied
   (``final_filter_lower_edge=0.2``).

   PyBeMoBIL band-passes the continuous data at 0.1-100 Hz after bad channel detection and
   before ICA (``filter_bands=(0.1, 100.0)``), and this filter stays in the cleaned output.
   The ICA copy is high-passed at 1.75 Hz as in MATLAB (``filter_bands_ica=(1.75, None)``),
   but with MNE's default FIR design, whose filter length is chosen automatically rather
   than fixed at order 1650. There is no final high-pass after ICA. To get closer to the
   MATLAB behaviour, skip the main bandpass and add the final filter yourself:

   .. code-block:: python

      preprocessor = EEGPreprocessor(loader=loader, filter_bands=(None, None))
      raw_clean, report, metadata = preprocessor.run(fname_in, fname_out=fname_out)
      raw_clean.filter(l_freq=0.2, h_freq=None)

**Output format**
   The original MATLAB implementation saves ``.set`` / ``.fdt`` (EEGLAB) files. PyBeMoBIL
   saves MNE's FIF format and organizes outputs as BIDS. ``fname_out`` must be a BIDS-style
   path inside a ``derivatives`` folder (e.g.
   ``bids/derivatives/pybemobil/sub-01/eeg/sub-01_task-walk_eeg.fif``); its entities name
   every output. The FIF files use the extension of ``fname_out``: ``.fif`` by default, or
   ``.fif.gz`` if ``fname_out`` ends in it. Written next to ``fname_out`` (see
   :func:`~pybemobil.preproc.get_derivative_paths`):

   - ``*_desc-clean_eeg.fif``: the cleaned recording
   - ``*_desc-preica_eeg.fif``: the data ICA was applied to (for re-applying ICA)
   - ``*_ica.fif``, ``*_iclabels.json``, ``*_badchannels.json``
   - ``*_dipoles/`` (one ``.bdip`` file per IC) and ``*_trans.fif``, when fitting dipoles
   - ``*_report.html``

   By default (``save_bids_raw=True``) the untouched input is also written once to the raw
   part of the BIDS dataset with :func:`mne_bids.write_raw_bids`. The BIDS root is taken
   from the folder above ``derivatives`` unless ``bids_root`` is given.

**Bilateral dipole fitting (not yet available)**
   The original MATLAB implementation supports ``number_of_dipoles=2``, fitting a symmetric
   bilateral dipole pair per IC.  This is **not currently implemented** in PyBeMoBIL:
   :func:`~pybemobil.preproc.fit_dipoles_on_ica`'s ``n_dipoles`` parameter only supports
   ``1`` (a single equivalent current dipole via :func:`mne.fit_dipole`); passing ``n_dipoles=2``
   raises :class:`NotImplementedError` rather than silently returning a single-dipole result.
   MNE has no built-in constrained two-dipole fit, so bilateral fitting would require a custom
   optimization - unlike the other differences on this page, this is a genuine feature gap
   rather than a deliberate design choice, and is open for future contribution.

----

Minimal example
---------------

The following script replicates the core BeMoBIL EEG preprocessing steps using PyBeMoBIL.

.. code-block:: python

   from pybemobil.io import XDFLoader
   from pybemobil.preproc import EEGPreprocessor

   # --- Equivalent to bemobil_process_all_EEG_preprocessing ---

   loader = XDFLoader(
       montage="easycap-M1",          # channel_locations_filename
       target_sfreq=250.0,            # resample_freq = 250
       old_reference="FCz",           # example; MATLAB's default ref_channel = [] keeps
                                      # the recording reference as is
   )

   preprocessor = EEGPreprocessor(
       loader=loader,
       line_noise_freq="europe",      # 50 Hz; use "usa" for 60 Hz
       line_noise_method="adaptive",  # zaplineConfig.noisefreqs = []
       filter_bands=(0.1, 100.0),     # PyBeMoBIL only; MATLAB does not filter here
       filter_bands_ica=(1.75, None), # filter_lowCutoffFreqAMICA = 1.75
       downsample_ica=250.0,          # resample_freq = 250
       ica_method="jamica",           # AMICA (via jamica), sample rejection on
                                      # (AMICA_autoreject = 1, 3 SD, 10 rounds)
       thresh=-1,                     # iclabel_threshold = -1
       # include_labels default = all except eye blink (iclabel_classes = [1 2 4 5 6 7])
       fit_dipoles=True,              # dipole fitting on
       rv_thresh=None,                # residualVariance_threshold = 100 (no threshold)
       remove_outside_head=False,     # do_remove_outside_head = 'off'
   )

   # fname_out is a BIDS-style path inside derivatives/; the BIDS root is "bids"
   raw_clean, report, metadata = preprocessor.run(
       "sub-01_task-walk_run-01.xdf",
       fname_out="bids/derivatives/pybemobil/sub-01/eeg/sub-01_task-walk_run-01_eeg.fif",
       overwrite=True,
   )

   # Access pipeline outputs
   ica         = metadata["ica"]
   ic_labels   = metadata["ic_labels"]
   dipoles     = metadata["dipoles"]
   bad_ch_dict = metadata["bad_ch_dict"]

----

Reference
---------

Klug, M., Jeung, S., Wunderlich, A., Gehrke, L., Protzak, J., Djebbara, Z.,
Argubi-Wollesen, A., Wollesen, B., & Gramann, K. (2022).
*The BeMoBIL Pipeline for automated analyses of multimodal mobile brain and body
imaging data.* bioRxiv. https://doi.org/10.1101/2022.09.29.510051
