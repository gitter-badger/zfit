"""
Definition of minimizers, wrappers etc.

"""

import abc
import collections
from collections import OrderedDict
import contextlib

import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
import pep487
from typing import Dict, List, Union, Optional

import zfit
from zfit import ztf
from .fitresult import FitResult
from ..core.interfaces import ZfitLoss
from ..util import ztyping
from ..util.temporary import TemporarilySet


class ZfitMinimizer(object):
    """Define the minimizer interface."""

    @abc.abstractmethod
    def minimize(self, loss, params=None):
        raise NotImplementedError

    def _minimize(self, loss, params):
        raise NotImplementedError

    def _minimize_with_step(self, loss, params):
        raise NotImplementedError

    def step(self, loss, params=None):
        raise NotImplementedError

    def _step_tf(self, loss, params):
        raise NotImplementedError

    def _step(self, loss, params):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def tolerance(self):
        raise NotImplementedError

    def _tolerance(self):
        raise NotImplementedError


class BaseMinimizer(ZfitMinimizer, pep487.PEP487Object):
    _DEFAULT_name = "BaseMinimizer"

    def __init__(self, name=None, tolerance=None):
        super().__init__()
        if name is None:
            name = self._DEFAULT_name
        self.name = name
        self.tolerance = tolerance
        self._sess = None

    def _check_input_params(self, loss: ZfitLoss, params, only_floating=True):
        if isinstance(params, (str, tf.Variable)) or (not hasattr(params, "__len__") and params is not None):
            params = [params, ]
        if params is None or isinstance(params[0], str):
            params = loss.get_dependents(only_floating=only_floating)
        return params

    def set_sess(self, sess):
        value = sess

        def getter():
            return self._sess  # use private attribute! self.sess creates default session

        def setter(value):
            self.sess = value

        return TemporarilySet(value=value, setter=setter, getter=getter)

    @staticmethod
    def _filter_floating_params(params):
        params = [param for param in params if param.floating]
        return params

    @staticmethod
    def _extract_update_op(params):
        params_update = [param.update_op for param in params]
        return params_update

    @staticmethod
    def _extract_assign_method(params):
        params_assign = [param.assign for param in params]
        return params_assign

    @staticmethod
    def _extract_parameter_names(params):
        names = [param.name for param in params]
        return names

    def _assign_parameters(self, params, values):
        params_assign_op = [param.assign(val) for param, val in zip(params, values)]
        return self.sess.run(params_assign_op)

    def _update_parameters(self, params, values):
        feed_dict = {param.placeholder: val for param, val in zip(params, values)}
        return self.sess.run(self._extract_update_op(params), feed_dict=feed_dict)

    @property
    def sess(self):
        sess = self._sess
        if sess is None:
            sess = zfit.run.sess
        return sess

    @sess.setter
    def sess(self, sess):
        self._sess = sess

    @property
    def tolerance(self):
        return self._tolerance

    @tolerance.setter
    def tolerance(self, tolerance):
        self._tolerance = tolerance

    @staticmethod
    def _extract_start_values(params):
        """Extract the current value if defined, otherwise random.

        Arguments:
            params (Parameter):

        Return:
            list(const): the current value of parameters
        """
        values = [p for p in params]
        # TODO: implement if initial val not given
        return values

    def step(self, loss, params: ztyping.ParamsOrNameType = None):
        """Perform a single step in the minimization (if implemented).

        Args:
            params ():

        Returns:

        Raises:
            NotImplementedError: if the `step` method is not implemented in the minimizer.
        """
        params = self._check_input_params(params)
        return self._step(params=params)

    def minimize(self, loss: ZfitLoss, params: ztyping.ParamsOrNameType = None) -> "FitResult":
        """Fully minimize the `loss` with respect to `params` using `sess`.

        Args:
            params (list(str) or list(`zfit.Parameter`): The parameters with respect to which to
                minimize the `loss`.
            sess (`tf.Session`): The session to use.

        Returns:
            `FitResult`: The fit result.
        """
        params = self._check_input_params(loss=loss, params=params)
        return self._hook_minimize(loss=loss, params=params)

    def _hook_minimize(self, loss, params):
        return self._call_minimize(loss=loss, params=params)

    def _call_minimize(self, loss, params):
        try:
            return self._minimize(loss=loss, params=params)
        except NotImplementedError as error:
            try:
                return self._minimize_with_step(loss=loss, params=params)
            except NotImplementedError:
                raise error

    def _minimize_with_step(self, loss, params):  # TODO improve
        changes = collections.deque(np.ones(10))
        last_val = -10
        try:
            step = self._step_tf(loss=loss, params=params)
        except NotImplementedError:
            step_fn = self.step
        else:
            def step_fn(loss, params):
                return self.sess.run([step, loss.value()])

        while sum(sorted(changes)[-3:]) > self.tolerance:  # TODO: improve condition
            _, cur_val = step_fn(loss=loss, params=params)
            changes.popleft()
            changes.append(abs(cur_val - last_val))
            last_val = cur_val
        fmin = cur_val
        edm = -999  # TODO: get edm
        status = {}  # TODO: create status
        param_values = self.sess.run(params)
        params = OrderedDict((p, val) for p, val in zip(params, param_values))

        return FitResult(params=params, edm=edm, fmin=fmin, status=status,
                         loss=loss, minimizer=self)


if __name__ == '__main__':
    from zfit.core.parameter import Parameter
    from zfit.minimizers.minimizer_minuit import MinuitMinimizer, MinuitTFMinimizer
    from zfit.minimizers.minimizer_tfp import BFGSMinimizer

    import time

    with tf.Session() as sess:
        with tf.variable_scope("func1"):
            a = Parameter("variable_a", ztf.constant(1.5),
                          ztf.constant(-1.),
                          ztf.constant(20.),
                          step_size=ztf.constant(0.1))
            b = Parameter("variable_b", 2.)
            c = Parameter("variable_c", 3.1)
        minimizer_fn = tfp.optimizer.bfgs_minimize

        # sample = tf.constant(np.random.normal(loc=1., size=100000), dtype=tf.float64)
        # # sample = np.random.normal(loc=1., size=100000)
        # def func(par_a, par_b, par_c):
        #     high_dim_func = (par_a - sample) ** 2 + \
        #                     (par_b - sample * 4.) ** 2 + \
        #                     (par_c - sample * 8) ** 4
        #     return tf.reduce_sum(high_dim_func)
        #

        sample = tf.constant(np.random.normal(loc=1., scale=0.0003, size=10000), dtype=tf.float64)


        # sample = np.random.normal(loc=1., size=100000)
        def func():
            high_dim_func = (a - sample) ** 2 * abs(tf.sin(sample * a + b) + 2) + \
                            (b - sample * 4.) ** 2 + \
                            (c - sample * 8) ** 4 + 1.1
            return tf.reduce_sum(tf.log(high_dim_func))


        # a = tf.constant(9.0, dtype=tf.float64)
        # with tf.control_dependencies([a]):
        #     def func(a):
        #         return (a - 1.0) ** 2

        n_steps = 0

        # loss_func = func(par_a=a, par_b=b, par_c=c)
        # loss_func = func()
        loss_func = func

        # which_minimizer = 'bfgs'
        which_minimizer = 'minuit'
        # which_minimizer = 'tfminuit'
        # which_minimizer = 'scipy'

        print("Running minimizer {}".format(which_minimizer))

        if which_minimizer == 'minuit':
            minimizer = MinuitMinimizer(sess=sess)

            init = tf.global_variables_initializer()
            sess.run(init)

            # for _ in range(5):

            n_rep = 1
            start = time.time()
            for _ in range(n_rep):
                value = minimizer.minimize()  # how many times to be serialized
            end = time.time()
            print("value from calculations:", value)
            print("type:", type(value))
            print("time needed", (end - start) / n_rep)
        ##################################################################
        elif which_minimizer == 'tfminuit':
            loss = loss_func()
            minimizer = MinuitTFMinimizer(loss=loss)

            init = tf.global_variables_initializer()
            sess.run(init)

            # for _ in range(5):

            n_rep = 1
            start = time.time()
            for _ in range(n_rep):
                value = minimizer.minimize()
            end = time.time()

            print("value from calculations:", value)
            print("time needed", (end - start) / n_rep)

        #####################################################################
        elif which_minimizer == 'bfgs':
            test1 = BFGSMinimizer(sess=sess, tolerance=1e-6)

            minimum = test1.minimize(params=[a, b, c])
            last_val = 100000
            cur_val = 9999999
            loss_func = loss_func()
            # while abs(last_val - cur_val) > 0.00001:
            start = time.time()
            result = sess.run(minimum)
            end = time.time()
            print("value from calculations:", result)
            print("time needed", (end - start))
            # last_val = cur_val
            # print("running")

            # cur_val = sess.run(loss_func)
            # aval, bval, cval = sess.run([v for v in (a, b, c)])
            # aval, bval, cval = sess.run([v.read_value() for v in (a, b, c)])
            # print("a, b, c", aval, bval, cval)
            # minimizer.minimize(loss=loss_func, var_list=[a, b, c])
            cur_val = sess.run(loss_func)
            result = cur_val
            print(sess.run([v for v in (a, b, c)]))
            print(result)
        #####################################################################

        if which_minimizer == 'scipy':
            func = loss_func()
            train_step = tf.contrib.opt.ScipyOptimizerInterface(
                func,
                method='L-BFGS-B',
                options={'maxiter': 1000, 'gtol': 1e-8},
                # optimizer_kwargs={'options': {'ftol': 1e-5}},
                tol=1e-10)

            # minimizer = ScipyMinimizer(loss=func,
            #                            method='L-BFGS-B',
            #                            options={'maxiter': 100})

            # with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())

            start = time.time()
            for _ in range(1):
                # print(sess.run(func))
                train_step.minimize()
            result = sess.run(func)
            print(result)
            # value = minimizer.minimize(loss=loss_func())  # how many times to be serialized
            end = time.time()
            value = result
            print("value from calculations:", value)
            print(sess.run([v for v in (a, b, c)]))

            print("time needed", (end - start))

        print("Result from minimizer {}".format((which_minimizer)))