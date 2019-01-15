from collections import OrderedDict

from zfit.serialization.baserepr import BaseRepr
from zfit.serialization.serializable import BaseSerializable


class DummyParam(BaseSerializable):
    def __init__(self, name, init, lower=None, upper=None):
        self.name = name
        self.init = init
        self.lower = lower
        self.upper = upper

    def _get_repr_init(self, **overwrite_kwargs):
        return OrderedDict(
            ('name', ZString())

            )


class ZParam(BaseRepr):
    pass


class ZString(BaseRepr):

    def _obj_from_repr(self):
        return str(self.repr)

    def _repr_from_obj(self) -> OrderedDict:
        return str(self.obj)


class A(BaseSerializable):

    def __init__(self, a, b, name=None):
        self.a = a
        self.b = 5 * b
        self.name = "John Doe" if name is None else name

    def _get_repr_init(self, **overwrite_kwargs):
        return OrderedDict(
            ('a', ZParam()),
            ('b', {'type': ZParam, 'value': self.b}),
            ('name', {'type': ZString, 'value': self.name}),

            )
