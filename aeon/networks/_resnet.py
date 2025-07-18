"""Residual Network (ResNetNetwork)."""

__maintainer__ = ["hadifawaz1999"]


from aeon.networks.base import BaseDeepLearningNetwork


class ResNetNetwork(BaseDeepLearningNetwork):
    """
    Establish the network structure for a ResNet.

    Adapted from the implementations used in [1]_.

    Parameters
    ----------
    n_residual_blocks : int, default = 3
        The number of residual blocks of ResNet's model.
    n_conv_per_residual_block : int, default = 3
        The number of convolution blocks in each residual block.
    n_filters : int or list of int, default = [128, 64, 64]
        The number of convolution filters for all the convolution layers in the same
        residual block, if not a list, the same number of filters is used in all
        convolutions of all residual blocks.
    kernel_size : int or list of int, default = [8, 5, 3]
        The kernel size of all the convolution layers in one residual block, if not a
        list, the same kernel size is used in all convolution layers.
    strides : int or list of int, default = 1
        The strides of convolution kernels in each of the convolution layers in one
        residual block, if not a list, the same kernel size is used in all
        convolution layers.
    dilation_rate : int or list of int, default = 1
        The dilation rate of the convolution layers in one residual block, if not a
        list, the same kernel size is used in all convolution layers.
    padding : str or list of str, default = 'padding'
        The type of padding used in the convolution layers in one residual block, if not
        a list, the same kernel size is used in all convolution layers.
    activation : str or list of str, default = 'relu'
        Keras activation used in the convolution layers in one residual block, if not
        a list, the same kernel size is used in all convolution layers.
    use_bias : bool or list of bool, default = True
        Condition on whether or not to use bias values in the convolution layers in
        one residual block, if not a list, the same kernel size is used in all
        convolution layers.

    Notes
    -----
    Adapted from the implementation source code
    https://github.com/hfawaz/dl-4-tsc/blob/master/classifiers/resnet.py

    References
    ----------
    .. [1] H. Fawaz, G. B. Lanckriet, F. Petitjean, and L. Idoumghar,

    Network originally defined in:

    @inproceedings{wang2017time, title={Time series classification from
    scratch with deep neural networks: A strong baseline}, author={Wang,
    Zhiguang and Yan, Weizhong and Oates, Tim}, booktitle={2017
    International joint conference on neural networks (IJCNN)}, pages={
    1578--1585}, year={2017}, organization={IEEE} }

    """

    _config = {
        "python_dependencies": ["tensorflow"],
        "python_version": "<3.13",
        "structure": "encoder",
    }

    def __init__(
        self,
        n_residual_blocks=3,
        n_conv_per_residual_block=3,
        n_filters=None,
        kernel_size=None,
        strides=1,
        dilation_rate=1,
        padding="same",
        activation="relu",
        use_bias=True,
    ):
        self.n_filters = n_filters
        self.kernel_size = kernel_size
        self.activation = activation
        self.padding = padding
        self.strides = strides
        self.dilation_rate = dilation_rate
        self.use_bias = use_bias
        self.n_residual_blocks = n_residual_blocks
        self.n_conv_per_residual_block = n_conv_per_residual_block

        super().__init__()

    def _shortcut_layer(
        self, input_tensor, output_tensor, padding="same", use_bias=True
    ):
        import tensorflow as tf

        n_out_filters = int(output_tensor.shape[-1])

        shortcut_layer = tf.keras.layers.Conv1D(
            filters=n_out_filters, kernel_size=1, padding=padding, use_bias=use_bias
        )(input_tensor)
        shortcut_layer = tf.keras.layers.BatchNormalization()(shortcut_layer)

        return tf.keras.layers.Add()([output_tensor, shortcut_layer])

    def build_network(self, input_shape, **kwargs):
        """
        Construct a network and return its input and output layers.

        Parameters
        ----------
        input_shape : tuple of shape = (n_timepoints (m), n_channels (d))
            The shape of the data fed into the input layer.

        Returns
        -------
        input_layer : keras.layers.Input
            The input layer of the network.
        output_layer : keras.layers.Layer
            The output layer of the network.
        """
        import tensorflow as tf

        self._n_filters_ = [64, 128, 128] if self.n_filters is None else self.n_filters
        self._kernel_size_ = [8, 5, 3] if self.kernel_size is None else self.kernel_size

        if isinstance(self._n_filters_, list):
            if len(self._n_filters_) != self.n_residual_blocks:
                raise ValueError(
                    f"Number of filters {len(self._n_filters_)} should be"
                    f" the same as number of residual blocks but is"
                    f" not: {self.n_residual_blocks}"
                )
            self._n_filters = self._n_filters_
        else:
            self._n_filters = [self._n_filters_] * self.n_residual_blocks

        if isinstance(self._kernel_size_, list):
            if len(self._kernel_size_) != self.n_conv_per_residual_block:
                raise ValueError(
                    f"Number of kernels {len(self._kernel_size_)} should be"
                    f" the same as number of convolution layers per residual"
                    f" block but is not: {self.n_conv_per_residual_block}"
                )
            self._kernel_size = self._kernel_size_
        else:
            self._kernel_size = [self._kernel_size_] * self.n_conv_per_residual_block

        if isinstance(self.strides, list):
            if len(self.strides) != self.n_conv_per_residual_block:
                raise ValueError(
                    f"Number of strides {len(self.strides)} should be"
                    f" the same as number of convolution layers per residual"
                    f" block but is not: {self.n_conv_per_residual_block}"
                )
            self._strides = self.strides
        else:
            self._strides = [self.strides] * self.n_conv_per_residual_block

        if isinstance(self.dilation_rate, list):
            if len(self.dilation_rate) != self.n_conv_per_residual_block:
                raise ValueError(
                    f"Number of dilation rates {len(self.dilation_rate)} should be"
                    f" the same as number of convolution layers per residual"
                    f" block but is not: {self.n_conv_per_residual_block}"
                )
            self._dilation_rate = self.dilation_rate
        else:
            self._dilation_rate = [self.dilation_rate] * self.n_conv_per_residual_block

        if isinstance(self.padding, list):
            if len(self.padding) != self.n_conv_per_residual_block:
                raise ValueError(
                    f"Number of paddings {len(self.padding)} should be"
                    f" the same as number of convolution layers per residual"
                    f" block but is not: {self.n_conv_per_residual_block}"
                )
            self._padding = self.padding
        else:
            self._padding = [self.padding] * self.n_conv_per_residual_block

        if isinstance(self.activation, list):
            if len(self.activation) != self.n_conv_per_residual_block:
                raise ValueError(
                    f"Number of activations {len(self.activation)} should be"
                    f" the same as number of convolution layers per residual"
                    f" block but is not: {self.n_conv_per_residual_block}"
                )
            self._activation = self.activation
        else:
            self._activation = [self.activation] * self.n_conv_per_residual_block

        if isinstance(self.use_bias, list):
            if len(self.use_bias) != self.n_conv_per_residual_block:
                raise ValueError(
                    f"Number of biases {len(self.use_bias)} should be"
                    f" the same as number of convolution layers per residual"
                    f" block but is not: {self.n_conv_per_residual_block}"
                )
            self._use_bias = self.use_bias
        else:
            self._use_bias = [self.use_bias] * self.n_conv_per_residual_block

        input_layer = tf.keras.layers.Input(input_shape)

        x = input_layer

        for d in range(self.n_residual_blocks):
            input_block_tensor = x

            for c in range(self.n_conv_per_residual_block):
                conv = tf.keras.layers.Conv1D(
                    filters=self._n_filters[d],
                    kernel_size=self._kernel_size[c],
                    strides=self._strides[c],
                    padding=self._padding[c],
                    dilation_rate=self._dilation_rate[c],
                )(x)
                conv = tf.keras.layers.BatchNormalization()(conv)

                if c == self.n_conv_per_residual_block - 1:
                    conv = self._shortcut_layer(
                        input_tensor=input_block_tensor, output_tensor=conv
                    )

                conv = tf.keras.layers.Activation(activation=self._activation[c])(conv)

                x = conv

        gap_layer = tf.keras.layers.GlobalAveragePooling1D()(conv)

        return input_layer, gap_layer
