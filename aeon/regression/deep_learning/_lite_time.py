"""LITETime and LITE regressors."""

from __future__ import annotations

__author__ = ["aadya940", "hadifawaz1999"]
__all__ = ["IndividualLITERegressor", "LITETimeRegressor"]

import gc
import os
import time
from copy import deepcopy
from typing import TYPE_CHECKING, Any

import numpy as np
from sklearn.utils import check_random_state

from aeon.networks import LITENetwork
from aeon.regression.deep_learning.base import BaseDeepRegressor, BaseRegressor

if TYPE_CHECKING:
    import tensorflow as tf
    from tensorflow.keras.callbacks import Callback


class LITETimeRegressor(BaseRegressor):
    """LITETime or LITEMVTime ensemble Regressor.

    Ensemble of IndividualLITETimeRegressor objects, as described in [1]_
    and [2]_. For using LITEMV, simply set the `use_litemv`
    bool parameter to True.

    Parameters
    ----------
    n_regressors : int, default = 5,
        the number of LITE or LITEMV models used for the
        Ensemble in order to create
        LITETime or LITEMVTime.
    use_litemv : bool, default = False
        The boolean value to control which version of the
        network to use. If set to `False`, then LITE is used,
        if set to `True` then LITEMV is used. LITEMV is the
        same architecture as LITE but specifically designed
        to better handle multivariate time series.
    n_filters : int, default = 32
        The number of filters used in one lite layer.
    kernel_size : int, default = 40
        The head kernel size used for each lite layer.
    strides : int or list of int, default = 1
        The strides of kernels in convolution layers for each lite layer,
        if not a list, the same is used in all lite layers.
    activation : str or list of str, default = 'relu'
        The activation function used in each lite layer, if not a list,
        the same is used in all lite layers.
    output_activation   : str, default = "linear",
        the output activation for the regressor.
    batch_size : int, default = 64
        the number of samples per gradient update.
    use_mini_batch_size : bool, default = False
        condition on using the mini batch size
        formula Wang et al.
    n_epochs : int, default = 1500
        the number of epochs to train the model.
    callbacks : keras callback or list of callbacks,
        default = None
        The default list of callbacks are set to
        ModelCheckpoint and ReduceLROnPlateau.
    file_path : str, default = "./"
        file_path when saving model_Checkpoint callback
    save_best_model : bool, default = False
        Whether or not to save the best model, if the
        model checkpoint callback is used by default,
        this condition, if True, will prevent the
        automatic deletion of the best saved model from
        file and the user can choose the file name
    save_last_model : bool, default = False
        Whether or not to save the last model, last
        epoch trained, using the base class method
        save_last_model_to_file
    save_init_model : bool, default = False
        Whether to save the initialization of the  model.
    best_file_name : str, default = "best_model"
        The name of the file of the best model, if
        save_best_model is set to False, this parameter
        is discarded
    last_file_name : str, default = "last_model"
        The name of the file of the last model, if
        save_last_model is set to False, this parameter
        is discarded
    init_file_name : str, default = "init_model"
        The name of the file of the init model, if save_init_model is set to False,
        this parameter is discarded.
    random_state : int, RandomState instance or None, default=None
        If `int`, random_state is the seed used by the random number generator;
        If `RandomState` instance, random_state is the random number generator;
        If `None`, the random number generator is the `RandomState` instance used
        by `np.random`.
        Seeded random number generation can only be guaranteed on CPU processing,
        GPU processing will be non-deterministic.
    verbose : boolean, default = False
        whether to output extra information
    loss : str, default = "mean_squared_error"
        The name of the keras training loss.
    metrics : str or list[str], default="mean_squared_error"
        The evaluation metrics to use during training. If
        a single string metric is provided, it will be
        used as the only metric. If a list of metrics are
        provided, all will be used for evaluation.
    optimizer : keras.optimizer, default = tf.keras.optimizers.Adam()
        The keras optimizer used for training.

    Notes
    -----
    Adapted from the implementation from Ismail-Fawaz et. al
    https://github.com/MSD-IRIMAS/LITE
    by the code owner.

    References
    ----------
    ..[1] Ismail-Fawaz et al. LITE: Light Inception with boosTing
    tEchniques for Time Series Classification, IEEE International
    Conference on Data Science and Advanced Analytics, 2023.
    ..[2] Ismail-Fawaz, Ali, et al. "Look Into the LITE
    in Deep Learning for Time Series Classification."
    arXiv preprint arXiv:2409.02869 (2024).

    Examples
    --------
    >>> from aeon.regression.deep_learning import LITETimeRegressor
    >>> from aeon.datasets import load_unit_test
    >>> X_train, y_train = load_unit_test(split="train")
    >>> X_test, y_test = load_unit_test(split="test")
    >>> ltime = LITETimeRegressor(n_epochs=20,batch_size=4)  # doctest: +SKIP
    >>> ltime.fit(X_train, y_train)  # doctest: +SKIP
    LITETimeRegressor(...)
    """

    _tags = {
        "python_dependencies": "tensorflow",
        "capability:multivariate": True,
        "non_deterministic": True,
        "cant_pickle": True,
        "algorithm_type": "deeplearning",
    }

    def __init__(
        self,
        n_regressors: int = 5,
        use_litemv: bool = False,
        n_filters: int = 32,
        kernel_size: int = 40,
        strides: int | list[int] = 1,
        activation: str | list[str] = "relu",
        output_activation: str = "linear",
        file_path: str = "./",
        save_last_model: bool = False,
        save_best_model: bool = False,
        save_init_model: bool = False,
        best_file_name: str = "best_model",
        last_file_name: str = "last_model",
        init_file_name: str = "init_model",
        batch_size: int = 64,
        use_mini_batch_size: bool = False,
        n_epochs: int = 1500,
        callbacks: Callback | list[Callback] | None = None,
        random_state: int | np.random.RandomState | None = None,
        verbose: bool = False,
        loss: str = "mean_squared_error",
        metrics: str | list[str] = "mean_squared_error",
        optimizer: tf.keras.optimizers.Optimizer | None = None,
    ):
        self.n_regressors = n_regressors

        self.use_litemv = use_litemv

        self.strides = strides
        self.activation = activation
        self.output_activation = output_activation
        self.n_filters = n_filters

        self.kernel_size = kernel_size
        self.batch_size = batch_size
        self.n_epochs = n_epochs

        self.file_path = file_path

        self.save_last_model = save_last_model
        self.save_best_model = save_best_model
        self.save_init_model = save_init_model
        self.best_file_name = best_file_name
        self.last_file_name = last_file_name
        self.init_file_name = init_file_name

        self.callbacks = callbacks
        self.random_state = random_state
        self.verbose = verbose
        self.use_mini_batch_size = use_mini_batch_size
        self.loss = loss
        self.metrics = metrics
        self.optimizer = optimizer

        self.regressors_: list[IndividualLITERegressor] = []

        super().__init__()

    def _fit(self, X: np.ndarray, y: np.ndarray) -> LITETimeRegressor:
        """Fit the ensemble of IndividualLITERegressor models.

        Parameters
        ----------
        X : np.ndarray of shape = (n_instances (n), n_channels (c), n_timepoints (m))
            The training input samples.
        y : np.ndarray of shape n
            The training data target values.

        Returns
        -------
        self : object
        """
        rng = check_random_state(self.random_state)

        for n in range(0, self.n_regressors):
            rgs = IndividualLITERegressor(
                use_litemv=self.use_litemv,
                n_filters=self.n_filters,
                kernel_size=self.kernel_size,
                output_activation=self.output_activation,
                file_path=self.file_path,
                save_best_model=self.save_best_model,
                save_last_model=self.save_last_model,
                save_init_model=self.save_init_model,
                best_file_name=self.best_file_name + str(n),
                last_file_name=self.last_file_name + str(n),
                init_file_name=self.init_file_name + str(n),
                batch_size=self.batch_size,
                use_mini_batch_size=self.use_mini_batch_size,
                n_epochs=self.n_epochs,
                callbacks=self.callbacks,
                loss=self.loss,
                metrics=self.metrics,
                optimizer=self.optimizer,
                random_state=rng.randint(0, np.iinfo(np.int32).max),
                verbose=self.verbose,
            )
            rgs.fit(X, y)
            self.regressors_.append(rgs)
            gc.collect()

        return self

    def _predict(self, X: np.ndarray) -> np.ndarray:
        """Predict the values of the test set using LITETime.

        Parameters
        ----------
        X : np.ndarray of shape = (n_instances (n), n_channels (c), n_timepoints (m))
            The testing input samples.

        Returns
        -------
        Y : np.ndarray of shape = (n_instances (n)), the predicted target values

        """
        vals = np.zeros(X.shape[0])

        for rgs in self.regressors_:
            vals += rgs._predict(X)

        vals = vals / self.n_regressors

        return vals

    @classmethod
    def _get_test_params(cls, parameter_set: str = "default") -> dict | list[dict]:
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return `"default"` set.
            For Regressors, a "default" set of parameters should be provided for
            general testing, and a "results_comparison" set for comparing against
            previously recorded results if the general set does not produce suitable
            probabilities to compare against.

        Returns
        -------
        params : dict or list of dict, default={}
            Parameters to create testing instances of the class.
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.
        """
        param1 = {
            "n_regressors": 1,
            "n_epochs": 2,
            "batch_size": 4,
            "kernel_size": 4,
        }
        param2 = {
            "n_regressors": 1,
            "use_litemv": True,
            "n_epochs": 2,
            "batch_size": 4,
            "kernel_size": 4,
            "metrics": ["mean_squared_error"],
            "verbose": True,
            "use_mini_batch_size": True,
        }

        return [param1, param2]


class IndividualLITERegressor(BaseDeepRegressor):
    """Single LITE or LITEMV Regressor.

    One LITE or LITEMV deep model, as described in [1]_
    and [2]_. For using LITEMV, simply set the `use_litemv`
    bool parameter to True.

    Parameters
    ----------
    use_litemv : bool, default = False
        The boolean value to control which version of the
        network to use. If set to `False`, then LITE is used,
        if set to `True` then LITEMV is used. LITEMV is the
        same architecture as LITE but specifically designed
        to better handle multivariate time series.
    n_filters : int, default = 32
        The number of filters used in one lite layer.
    kernel_size : int, default = 40
        The head kernel size used for each lite layer.
    strides : int or list of int, default = 1
        The strides of kernels in convolution layers for each lite layer,
        if not a list, the same is used in all lite layers.
    activation : str or list of str, default = 'relu'
        The activation function used in each lite layer, if not a list,
        the same is used in all lite layers.
    output_activation : str, default = 'linear'
        The activation function used in the output layer
    batch_size : int, default = 64
        the number of samples per gradient update.
    use_mini_batch_size : bool, default = False
        condition on using the mini batch size
        formula Wang et al.
    n_epochs : int, default = 1500
        the number of epochs to train the model.
    callbacks : keras callback or list of callbacks,
        default = None
        The default list of callbacks are set to
        ModelCheckpoint and ReduceLROnPlateau.
    file_path : str, default = "./"
        file_path when saving model_Checkpoint callback
    save_best_model : bool, default = False
        Whether or not to save the best model, if the
        model checkpoint callback is used by default,
        this condition, if True, will prevent the
        automatic deletion of the best saved model from
        file and the user can choose the file name
    save_last_model     : bool, default = False
        Whether or not to save the last model, last
        epoch trained, using the base class method
        save_last_model_to_file
    save_init_model : bool, default = False
        Whether to save the initialization of the  model.
    best_file_name      : str, default = "best_model"
        The name of the file of the best model, if
        save_best_model is set to False, this parameter
        is discarded
    last_file_name      : str, default = "last_model"
        The name of the file of the last model, if
        save_last_model is set to False, this parameter
        is discarded
    init_file_name : str, default = "init_model"
        The name of the file of the init model, if save_init_model is set to False,
        this parameter is discarded.
    random_state : int, RandomState instance or None, default=None
        If `int`, random_state is the seed used by the random number generator;
        If `RandomState` instance, random_state is the random number generator;
        If `None`, the random number generator is the `RandomState` instance used
        by `np.random`.
        Seeded random number generation can only be guaranteed on CPU processing,
        GPU processing will be non-deterministic.
    verbose : boolean, default = False
        whether to output extra information
    loss : str, default = "mean_squared_error"
        The name of the keras training loss.
    metrics : str or list[str], default="mean_squared_error"
        The evaluation metrics to use during training. If
        a single string metric is provided, it will be
        used as the only metric. If a list of metrics are
        provided, all will be used for evaluation.
    optimizer : keras.optimizer, default = tf.keras.optimizers.Adam()
        The keras optimizer used for training.

    Notes
    -----
    Adapted from the implementation from Ismail-Fawaz et. al
    https://github.com/MSD-IRIMAS/LITE
    by the code owner.

    References
    ----------
    ..[1] Ismail-Fawaz et al. LITE: Light Inception with boosTing
    tEchniques for Time Series Classification, IEEE International
    Conference on Data Science and Advanced Analytics, 2023.
    ..[2] Ismail-Fawaz, Ali, et al. "Look Into the LITE
    in Deep Learning for Time Series Classification."
    arXiv preprint arXiv:2409.02869 (2024).

    Examples
    --------
    >>> from aeon.regression.deep_learning import IndividualLITERegressor
    >>> from aeon.datasets import load_unit_test
    >>> X_train, y_train = load_unit_test(split="train")
    >>> X_test, y_test = load_unit_test(split="test")
    >>> lite = IndividualLITERegressor(n_epochs=20,batch_size=4)  # doctest: +SKIP
    >>> lite.fit(X_train, y_train)  # doctest: +SKIP
    IndividualLITERegressor(...)
    """

    def __init__(
        self,
        use_litemv: bool = False,
        n_filters: int = 32,
        kernel_size: int = 40,
        strides: int | list[int] = 1,
        activation: str | list[str] = "relu",
        output_activation: str = "linear",
        file_path: str = "./",
        save_best_model: bool = False,
        save_last_model: bool = False,
        save_init_model: bool = False,
        best_file_name: str = "best_model",
        last_file_name: str = "last_model",
        init_file_name: str = "init_model",
        batch_size: int = 64,
        use_mini_batch_size: bool = False,
        n_epochs: int = 1500,
        callbacks: Callback | list[Callback] | None = None,
        random_state: int | np.random.RandomState | None = None,
        verbose: bool = False,
        loss: str = "mean_squared_error",
        metrics: str | list[str] = "mean_squared_error",
        optimizer: tf.keras.optimizers.Optimizer | None = None,
    ):
        self.use_litemv = use_litemv
        self.n_filters = n_filters
        self.strides = strides
        self.activation = activation
        self.output_activation = output_activation

        self.kernel_size = kernel_size
        self.n_epochs = n_epochs

        self.file_path = file_path

        self.save_best_model = save_best_model
        self.save_last_model = save_last_model
        self.save_init_model = save_init_model
        self.best_file_name = best_file_name
        self.init_file_name = init_file_name

        self.callbacks = callbacks
        self.random_state = random_state
        self.verbose = verbose
        self.use_mini_batch_size = use_mini_batch_size
        self.loss = loss
        self.metrics = metrics
        self.optimizer = optimizer

        super().__init__(
            batch_size=batch_size,
            last_file_name=last_file_name,
        )

        self._network = LITENetwork(
            use_litemv=self.use_litemv,
            n_filters=self.n_filters,
            kernel_size=self.kernel_size,
            strides=self.strides,
            activation=self.activation,
        )

    def build_model(
        self, input_shape: tuple[int, ...], **kwargs: Any
    ) -> tf.keras.Model:
        """
        Construct a compiled, un-trained, keras model that is ready for training.

        Parameters
        ----------
        input_shape : tuple
            The shape of the data fed into the input layer

        Returns
        -------
        output : a compiled Keras Model
        """
        import tensorflow as tf

        rng = check_random_state(self.random_state)
        self.random_state_ = rng.randint(0, np.iinfo(np.int32).max)
        tf.keras.utils.set_random_seed(self.random_state_)
        input_layer, output_layer = self._network.build_network(input_shape, **kwargs)

        output_layer = tf.keras.layers.Dense(1, activation=self.output_activation)(
            output_layer
        )

        model = tf.keras.models.Model(inputs=input_layer, outputs=output_layer)

        self.optimizer_ = (
            tf.keras.optimizers.Adam() if self.optimizer is None else self.optimizer
        )

        model.compile(
            loss=self.loss,
            optimizer=self.optimizer_,
            metrics=self._metrics,
        )

        return model

    def _fit(self, X: np.ndarray, y: np.ndarray) -> IndividualLITERegressor:
        """
        Fit the Regressor on the training set (X, y).

        Parameters
        ----------
        X : array-like of shape = (n_instances, n_channels, n_timepoints)
            The training input samples. If a 2D array-like is passed,
            n_channels is assumed to be 1.
        y : array-like, shape = (n_instances)
            The training data target values.

        Returns
        -------
        self : object
        """
        import tensorflow as tf

        # Transpose to conform to Keras input style.
        X = X.transpose(0, 2, 1)

        if isinstance(self.metrics, list):
            self._metrics = self.metrics
        elif isinstance(self.metrics, str):
            self._metrics = [self.metrics]

        # ignore the number of instances, X.shape[0],
        # just want the shape of each instance
        self.input_shape = X.shape[1:]

        if self.use_mini_batch_size:
            mini_batch_size = int(min(X.shape[0] // 10, self.batch_size))
        else:
            mini_batch_size = self.batch_size
        self.training_model_ = self.build_model(self.input_shape)

        if self.save_init_model:
            self.training_model_.save(self.file_path + self.init_file_name + ".keras")

        if self.verbose:
            self.training_model_.summary()

        self.file_name_ = (
            self.best_file_name if self.save_best_model else str(time.time_ns())
        )

        if self.callbacks is None:
            self.callbacks_ = [
                tf.keras.callbacks.ReduceLROnPlateau(
                    monitor="loss", factor=0.5, patience=50, min_lr=0.0001
                ),
                tf.keras.callbacks.ModelCheckpoint(
                    filepath=self.file_path + self.file_name_ + ".keras",
                    monitor="loss",
                    save_best_only=True,
                ),
            ]
        else:
            self.callbacks_ = self._get_model_checkpoint_callback(
                callbacks=self.callbacks,
                file_path=self.file_path,
                file_name=self.file_name_,
            )

        self.history = self.training_model_.fit(
            X,
            y,
            batch_size=mini_batch_size,
            epochs=self.n_epochs,
            verbose=self.verbose,
            callbacks=self.callbacks_,
        )

        try:
            self.model_ = tf.keras.models.load_model(
                self.file_path + self.file_name_ + ".keras", compile=False
            )
            if not self.save_best_model:
                os.remove(self.file_path + self.file_name_ + ".keras")
        except FileNotFoundError:
            self.model_ = deepcopy(self.training_model_)

        if self.save_last_model:
            self.save_last_model_to_file(file_path=self.file_path)

        gc.collect()
        return self

    @classmethod
    def _get_test_params(cls, parameter_set: str = "default") -> dict | list[dict]:
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return `"default"` set.
            For Regressors, a "default" set of parameters should be provided for
            general testing, and a "results_comparison" set for comparing against
            previously recorded results if the general set does not produce suitable
            values to compare against.

        Returns
        -------
        params : dict or list of dict, default={}
            Parameters to create testing instances of the class.
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.
        """
        param1 = {
            "n_epochs": 2,
            "batch_size": 4,
            "kernel_size": 4,
        }
        param2 = {
            "use_litemv": True,
            "n_epochs": 2,
            "batch_size": 4,
            "kernel_size": 4,
            "metrics": ["mean_squared_error"],
            "verbose": True,
            "use_mini_batch_size": True,
        }

        return [param1, param2]
