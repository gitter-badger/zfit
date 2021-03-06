import abc

import tensorflow as tf
from typing import Optional, Union

from zfit import ztf
from .baseobject import BaseObject, BaseDependentsMixin
from .interfaces import ZfitLoss
from ..models.functions import SimpleFunc
from ..util.container import convert_to_container, is_container
from ..util.exception import IntentionNotUnambiguousError, NotExtendedPDFError
from zfit.settings import ztypes


def _unbinned_nll_tf(model, data, fit_range) -> tf.Tensor:
    """Return unbinned negative log likelihood graph for a PDF

    Args:
        fit_range ():
        model (Tensor): The probabilities
        constraints (dict): A dictionary containing the constraints for certain parameters. The key
            is the parameter while the value is a pdf with at least a `pdf(x)` method.

    Returns:
        graph: the unbinned nll

    Raises:
        ValueError: if both `probs` and `log_probs` are specified.
    """

    if is_container(model):
        nlls = [_unbinned_nll_tf(model=p, data=d, fit_range=r)
                for p, d, r in zip(model, data, fit_range)]
        nll_finished = tf.reduce_sum(nlls)
    else:  # TODO: complicated limits?
        fit_range = model.convert_sort_space(fit_range)
        limits = fit_range.limits
        assert len(limits[0]) == 1, "multiple limits not (yet) supported in nll."
        (lower,), (upper,) = limits

        # TODO(Mayou36): implement properly data cutting
        # in_limits = tf.logical_and(lower <= data, data <= upper)
        # data = tf.boolean_mask(tensor=data, mask=in_limits)
        probs = model.pdf(data, norm_range=fit_range)
        if model.is_extended:
            probs /= model.get_yield()
        log_probs = tf.log(probs)
        nll = -tf.reduce_sum(log_probs)
        nll_finished = nll
    return nll_finished


def _nll_constraints_tf(constraints):
    if not constraints:
        return ztf.constant(0.)  # adding 0 to nll
    probs = []
    for param, dist in constraints.items():
        probs.append(dist.pdf(param))
    # probs = [dist.pdf(param) for param, dist in constraints.items()]
    constraints_neg_log_prob = -tf.reduce_sum(tf.log(probs))
    return constraints_neg_log_prob


class BaseLoss(BaseObject, BaseDependentsMixin, ZfitLoss):

    def __init__(self, model, data, fit_range=None, constraints=None):
        super().__init__(name=type(self).__name__)
        model, data, fit_range = self._input_check(pdf=model, data=data, fit_range=fit_range)
        self._model = model
        self._data = data
        self._fit_range = fit_range
        if constraints is None:
            constraints = []
        self._constraints = convert_to_container(constraints, list)

    def __init_subclass__(cls, **kwargs):
        cls._name = "UnnamedSubBaseLoss"

    def _input_check(self, pdf, data, fit_range):
        if is_container(pdf) ^ is_container(data):
            raise ValueError("`pdf` and `data` either both have to be a list or not.")
        if not is_container(pdf):
            if isinstance(fit_range, list):
                raise TypeError("`pdf` and `data` are not a `list`, `fit_range` can't be a `list` then.")
        if isinstance(pdf, tuple):
            raise TypeError("`pdf` has to be a pdf or a list of pdfs, not a tuple.")

        if isinstance(data, tuple):
            raise TypeError("`data` has to be a data or a list of data, not a tuple.")

        pdf, data = (convert_to_container(obj, non_containers=[tuple]) for obj in (pdf, data))
        # TODO: data, range consistency?
        if fit_range is None:
            fit_range = []
            for p, d in zip(pdf, data):
                if not p.norm_range == d.data_range:
                    raise IntentionNotUnambiguousError("No `fit_range` is specified and `pdf` {} as "
                                                       "well as `data` {} have different ranges they"
                                                       "are defined in. Either make them (all) consistent"
                                                       "or specify the `fit_range`")
                fit_range.append(p.norm_range)
        else:
            fit_range = convert_to_container(fit_range, non_containers=[tuple])

        # simultaneous fit
        # if is_container(pdf):
        # if not is_container(fit_range) or not isinstance(fit_range[0], Space):
        #     raise ValueError(
        #         "If several pdfs are specified, the `fit_range` has to be given as a list of `Space` "
        #         "objects and not as pure tuples.")

        # else:
        #     fit_range = pdf.convert_sort_space(limits=fit_range)  # fit_range may be a tuple
        if not len(pdf) == len(data) == len(fit_range):
            raise ValueError("pdf, data and fit_range don't have the same number of components:"
                             "\npdf: {}"
                             "\ndata: {}"
                             "\nfit_range: {}".format(pdf, data, fit_range))

        # sanitize fit_range
        fit_range = [p.convert_sort_space(limits=range_) for p, range_ in zip(pdf, fit_range)]
        # TODO: sanitize pdf, data?

        return pdf, data, fit_range

    def add_constraints(self, constraints):
        return self._add_constraints(constraints)

    def _add_constraints(self, constraints):
        constraints = convert_to_container(constraints, container=list)
        self._constraints.extend(constraints)
        return constraints

    @property
    def name(self):
        return self._name

    @property
    def model(self):
        return self._model

    @property
    def data(self):
        return self._data

    @property
    def fit_range(self):
        fit_range = self._fit_range
        return fit_range

    @property
    def constraints(self):
        return self._constraints

    def _get_dependents(self):
        pdf_dependents = self._extract_dependents(self.model)
        return pdf_dependents

    @abc.abstractmethod
    def _loss_func(self, model, data, fit_range, constraints):
        raise NotImplementedError

    def value(self):
        return self._value()

    def _value(self):
        try:
            return self._loss_func(model=self.model, data=self.data, fit_range=self.fit_range,
                                   constraints=self.constraints)
        except NotImplementedError:
            raise NotImplementedError("_loss_func not properly defined!")

    def __add__(self, other):
        if not isinstance(other, BaseLoss):
            raise TypeError("Has to be a subclass of `BaseLoss` or overwrite `__add__`.")
        if not type(other) == type(self):
            raise ValueError("cannot safely add two different kind of loss.")
        model = self.model + other.model
        data = self.data + other.data
        fit_range = self.fit_range + other.fit_range
        loss = type(self)(model=model, data=data, fit_range=fit_range, constraints=self.constraints)
        loss.add_constraints(constraints=other.constraints)
        return loss


class CachedLoss(BaseLoss):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_loss = None

    @abc.abstractmethod
    def _cache_add_constraints(self, constraints):
        raise NotImplementedError

    def _value(self):
        if self._cached_loss is None:
            loss = super()._value()
            self._cached_loss = loss
        else:
            loss = self._cached_loss
        return loss

    def _add_constraints(self, constraints):
        super()._add_constraints(constraints=constraints)
        self._cache_add_constraints(constraints=constraints)


class UnbinnedNLL(CachedLoss):
    _name = "UnbinnedNLL"

    def _loss_func(self, model, data, fit_range, constraints):
        nll = _unbinned_nll_tf(model=model, data=data, fit_range=fit_range)
        if constraints:
            constraints = ztf.reduce_sum(constraints)
            nll += constraints
        return nll

    def _cache_add_constraints(self, constraints):
        if self._cached_loss is not None:
            self._cached_loss += ztf.reduce_sum(constraints)

    def errordef(self, sigma: Union[float, int]) -> Union[float, int]:
        return sigma


class ExtendedUnbinnedNLL(UnbinnedNLL):

    def _loss_func(self, model, data, fit_range, constraints):
        nll = super()._loss_func(model=model, data=data, fit_range=fit_range, constraints=constraints)
        poisson_terms = []
        for mod, dat in zip(model, data):
            if not mod.is_extended:
                raise NotExtendedPDFError("The pdf {} is not extended but has to be (for an extended fit)".format(mod))
            poisson_terms.append(-mod.get_yield() + tf.size(dat, out_type=ztypes.float) * tf.log(mod.get_yield()))
        nll -= tf.reduce_sum(poisson_terms)
        return nll


class SimpleLoss(BaseLoss):
    _name = "SimpleLoss"

    def __init__(self, func):
        self._simple_func = func

        model = SimpleFunc(func=func, obs='obs1')
        super().__init__(model=[model], data=['dummy'], fit_range=[False])

    def errordef(self, func):
        raise NotImplementedError("For this simple loss function, no error calculation is possible.")

    def _loss_func(self, model, data, fit_range, constraints=None):
        loss = self._simple_func
        return loss()
