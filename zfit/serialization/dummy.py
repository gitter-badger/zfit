from collections import OrderedDict

from zfit.serialization.baserepr import BaseRepr, Repr, CompositeRepr
from zfit.serialization.serializable import BaseSerializable


class DummyParam(BaseSerializable):
    def __init__(self, name, init, lower=None, upper=None):
        self.name = name
        self.init = init
        self.lower = lower
        self.upper = upper

    @classmethod
    def _get_repr_init(cls):
        super_init_obj = super()._get_repr_init()
        init_obj = OrderedDict((
            ('name', Repr(repr=ZString, obj_getter=lambda self: self.name)),
            ('init', Repr(ZNumeric, lambda self: self.init)),
            ('lower', Repr(ZNumeric, lambda self: self.lower)),
            ('upper', Repr(ZNumeric, lambda self: self.upper)),
            )
            )
        super_init_obj.update(init_obj)
        # pop if created in init
        return super_init_obj


class DummyPDF1(BaseSerializable):

    def __init__(self, mu, sigma, name):
        super().__init__()
        self.mu = mu
        self.sigma = sigma
        self.name = name

    @classmethod
    def _get_repr_init(cls):
        init_obj = super()._get_repr_init()
        self_init_obj = OrderedDict((
            ('mu', Repr(ZParam, obj_getter=lambda self: self.mu)),
            ('sigma', Repr(ZParam, obj_getter=lambda self: self.sigma)),
            ('name', Repr(ZString, obj_getter=lambda self: self.name)),
            )
            )
        init_obj.update(self_init_obj)
        return init_obj


class ZNumeric(BaseRepr):

    def _get_init_wrapped_from_obj(self, obj):
        return obj

    def _dump_serial_from_dump_wrapped(self, dump_wrapped):
        return 'float ' + str(dump_wrapped)

    def _dump_wrapped_from_dump_serial(self, dump_serial):
        value = dump_serial[6:]  # starts with "float "
        return float(value)

    def _init_obj_from_init_wrapped(self, init_wrapped):
        return init_wrapped


class ZParam(CompositeRepr):
    instantiator = DummyParam


class ZPDF(CompositeRepr):
    instantiator = DummyPDF1


class ZString(BaseRepr):

    def _get_init_wrapped_from_obj(self, obj):
        return obj

    def _dump_serial_from_dump_wrapped(self, dump_wrapped):
        return str(dump_wrapped)

    def _dump_wrapped_from_dump_serial(self, dump_serial):
        return str(dump_serial)

    def _init_obj_from_init_wrapped(self, init_wrapped):
        return init_wrapped


# helpers
def params_equal(param1, param2):
    equal = True
    equal *= param1.name == param2.name
    equal *= param1.init == param2.init
    equal *= param1.lower == param2.lower
    equal *= param1.upper == param2.upper
    return bool(equal)


def pdfs_equal(pdf1, pdf2):
    equal = True
    equal *= pdf1.name == pdf2.name
    equal *= params_equal(pdf1.mu, pdf2.mu)
    equal *= params_equal(pdf1.sigma, pdf2.sigma)
    return bool(equal)


if __name__ == '__main__':
    param1 = DummyParam(name='param1', init=41, lower=4.1, upper=410)
    param2 = DummyParam(name='param2', init=42, lower=4.2, upper=420)
    pdf1 = DummyPDF1(mu=param1, sigma=param2, name='pdf1')
    dumper_param1 = ZParam(obj=param1)
    serial_param1 = dumper_param1.get_dump_serial()
    print("parameter", param1, serial_param1)
    loader_param1 = ZParam(serial=serial_param1)
    param1_new = loader_param1.get_init_obj()
    print("new parameter", param1_new)
    print("new parameter == old param", params_equal(param1, param1_new))
    dumper_pdf1 = ZPDF(obj=pdf1)
    serial_pdf1 = dumper_pdf1.get_dump_serial()
    print("pdf1", serial_pdf1)
    loader_pdf1 = ZPDF(serial=serial_pdf1)
    new_pdf1 = loader_pdf1.get_init_obj()
    print("new pdf1", new_pdf1)
    print("new pdf1 == old pdf", pdfs_equal(pdf1, new_pdf1))
    print("finished")
