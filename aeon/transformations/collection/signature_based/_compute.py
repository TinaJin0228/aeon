"""Class for signature computation over windows."""

import numpy as np

from aeon.transformations.collection import BaseCollectionTransformer
from aeon.transformations.collection.signature_based._rescaling import (
    _rescale_path,
    _rescale_signature,
)
from aeon.transformations.collection.signature_based._window import _window_getter


class _WindowSignatureTransform(BaseCollectionTransformer):
    """Perform the signature transform over given windows.

    Given data of shape [N, L, C] and specification of a window method from the
    signatures window module, this class will compute the signatures over
    each window (for the given signature options) and concatenate the results
    into a tensor of shape [N, num_sig_features * num_windows].

    Parameters
    ----------
    num_intervals: int, dimension of the transformed data (default 8)
    """

    _tags = {
        "fit_is_empty": True,
        "output_data_type": "Tabular",
        "capability:multivariate": True,
        "python_dependencies": "esig",
    }

    def __init__(
        self,
        window_name=None,
        window_depth=None,
        window_length=None,
        window_step=None,
        sig_tfm=None,
        sig_depth=None,
        rescaling=None,
    ):
        super().__init__()
        self.window_name = window_name
        self.window_depth = window_depth
        self.window_length = window_length
        self.window_step = window_step
        self.sig_tfm = sig_tfm
        self.sig_depth = sig_depth
        self.rescaling = rescaling

        self.window = _window_getter(
            self.window_name, self.window_depth, self.window_length, self.window_step
        )

    def _transform(self, X, y=None):
        import esig

        depth = self.sig_depth
        data = np.swapaxes(X, 1, 2)

        # Path rescaling
        if self.rescaling == "pre":
            data = _rescale_path(data, depth)

        # Prepare for signature computation
        if self.sig_tfm == "signature":

            def transform(x):
                return esig.stream2sig(x, depth)[1:].reshape(-1, 1)

        else:

            def transform(x):
                return esig.stream2logsig(x, depth).reshape(1, -1)

        length = data.shape[1]

        # Compute signatures in each window returning the grouped structure
        signatures = []
        for window_group in self.window(length):
            signature_group = []
            for window in window_group:
                # Signature computation step
                signature = np.stack(
                    [transform(x[window.start : window.end]) for x in data]
                ).reshape(data.shape[0], -1)
                # Rescale if specified
                if self.rescaling == "post":
                    signature = _rescale_signature(signature, data.shape[2], depth)

                signature_group.append(signature)
            signatures.append(signature_group)

        # We are currently not considering deep models and so return all the
        # features concatenated together
        signatures = np.concatenate([x for lst in signatures for x in lst], axis=1)

        return signatures
