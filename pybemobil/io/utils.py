"""Holds helpers for I/O operations in the PyBeMoBIL."""

# %% Imports

import json

import numpy as np

# %% Constants & Settings


# %% Classes & Functions


class NumpyEncoder(json.JSONEncoder):
    """Help encoding numpy arrays and scalars in JSON."""

    def default(self, obj):
        """Convert numpy arrays and scalars to lists and native Python types."""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):  # np.int64, np.float32, np.bool_, ...
            return obj.item()
        return super().default(obj)


# %%
