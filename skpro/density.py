import abc

import numpy as np
from scipy.integrate import simps
from sklearn.base import BaseEstimator
from sklearn.neighbors import KernelDensity


def ecdf(a):
    """ Returns the empirical distribution function of a sample

    Parameters
    ----------
    a: array
        Input array representing a sample

    Returns
    -------
    array xs   Empirical cdf of the input sample
    array ys
    """
    xs = np.sort(np.array(a))
    ys = np.arange(1, len(xs) + 1) / float(len(xs))

    return xs, ys


def step_function(xs, ys):
    """
    Returns a step function from x-y pair sample

    Parameters
    ----------
    xs  x values
    ys  corresponding y values

    Returns
    -------
    function A step function
    """

    def func(x):
        index = np.searchsorted(xs, x)
        index = len(ys) - 1 if index >= len(ys) else index
        return ys[index]

    return func


class DensityAdapter(BaseEstimator, metaclass=abc.ABCMeta):
    """
    Abtract base class for density adapter
    that transform an input into an
    density cdf/pdf interface
    """

    @abc.abstractmethod
    def __call__(self, inlet):
        """
        Adapter entry point

        Parameters
        ----------
        mixed inlet Input for the adapter transformation
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def pdf(self, x):
        """ Probability density function

        Parameters
        ----------
        x

        Returns
        -------
        mixed  Density function evaluated at x
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def cdf(self, x):
        """ Cumulative density function

        Parameters
        ----------
        x

        Returns
        -------
        mixed Cumulative density function evaluated at x
        """
        raise NotImplementedError()


class KernelDensityAdapter(DensityAdapter):
    """
    DensityAdapter that uses kernel density estimation
    to transform Bayesian samples
    """

    def __init__(self, estimator=KernelDensity()):
        self.estimator = estimator

    def __call__(self, sample):
        """
        Adapter entry point

        Parameters
        ----------
        np.array(M) inlet: Bayesian sample of length M
        """

        # fit kernel density estimator
        self._min_sample = min(sample)
        self._max_sample = max(sample)
        self._std_sample = np.std(sample)

        self.estimator.fit(sample[:, np.newaxis])

    def cdf(self, x):
        a = 10
        minus_inf = self._min_sample - a * self._std_sample

        step = 0.01
        grid = np.arange(minus_inf, x, step)

        pdf_estimation = np.exp(self.estimator.score_samples(grid.reshape(-1, 1)))
        integral = simps(y=pdf_estimation, dx=step)

        return integral

    def pdf(self, x):
        return np.exp(self.estimator.score_samples(x))[0]


class EmpiricalDensityAdapter(DensityAdapter):
    """
    DensityAdapter that uses empirical cdf
    to transform Bayesian samples
    """

    def __init__(self):
        self.xs_ = None
        self.ys_ = None
        self.step_function_ = None

    def __call__(self, sample):
        """
        Adapter entry point

        Parameters
        ----------
        np.array(M) inlet: Bayesian sample of length M
        """
        self.xs_, self.ys_ = ecdf(sample)
        self._hist, self._edges = np.histogram(
            sample, bins='auto', density=True
        )

        self.step_function_ = step_function(self.xs_, self.ys_)

        self._kde_estimator = KernelDensity(kernel='tophat')
        self._kde_estimator.fit(sample.reshape((-1, 1)))

    def cdf(self, x):
        x_cdf = self.step_function_(x)

        return x_cdf

    def pdf(self, x):
        return np.exp(self._kde_estimator.score_samples(x))[0]