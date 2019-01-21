import abc
from collections import OrderedDict
from typing import List, Tuple

import pep487


class Repr:

    def __init__(self, repr, obj_getter, setter='init'):
        self.repr = repr
        self.obj_getter = obj_getter
        self.setter = setter


class BaseRepr(pep487.PEP487Object):
    # class_init_repr = OrderedDict()
    instantiator = None

    def __init__(self, obj=None, serial=None, overwrite_kwargs=None):
        self.obj = obj
        self.serial = serial
        self._init_wrapped = None

    # def __init_subclass__(cls, **kwargs):
    #     cls.instantiator = None

    @abc.abstractmethod
    def _get_init_wrapped_from_obj(self, obj):
        raise NotImplementedError

    @property
    def init_wrapped(self):
        if self._init_wrapped is None:
            if self.obj is not None:
                init_wrapped = self._get_init_wrapped_from_obj(obj=self.obj)
            elif self.serial is not None:
                init_wrapped = self._get_init_wrapped_from_serial(serial=self.serial)
            else:
                assert False, "This should not happen, bug. Please report on github."
            init_wrapped = self._sort_by_keys(init_wrapped)
            self._init_wrapped = init_wrapped
        return self._init_wrapped

    def _dump_wrapped_from_init_wrapped(self, init_wrapped):
        return init_wrapped

    @abc.abstractmethod
    def _dump_serial_from_dump_wrapped(self, dump_wrapped):
        raise NotImplementedError

    #
    # def set_init_wrapped(self):
    #     if self.obj is not None:
    #         self._init_wrapped = self._get_init_wrapped_from_obj(obj=self.obj)
    #     elif self.serial is not None:
    #         self._init_wrapped = self._get_init_wrapped_from_serial(serial=self.serial)
    #     else:
    #         assert False, "Bug, this case should not happen. Please fill an issue and report."
    #
    # def get_init_wrapped(self):
    #     return self._init_wrapped
    #
    def get_dump_serial(self):
        serial = self.serial
        if serial is not None:
            return serial
        else:
            init_wrapped = self.init_wrapped
            dump_wrapped = self._dump_wrapped_from_init_wrapped(init_wrapped=init_wrapped)
            dump_serial = self._dump_serial_from_dump_wrapped(dump_wrapped=dump_wrapped)
            self.serial = dump_serial
            return dump_serial

    #
    def get_init_obj(self):
        obj = self.obj
        if obj is not None:
            return obj
        else:
            init_wrapped = self.init_wrapped
            init_obj = self._init_obj_from_init_wrapped(init_wrapped=init_wrapped)
            self.obj = init_obj
            return init_obj

    def _get_init_wrapped_from_serial(self, serial):
        dump_wrapped = self._dump_wrapped_from_dump_serial(dump_serial=serial)
        init_wrapped = self._init_wrapped_from_dump_wrapped(dump_wrapped=dump_wrapped)
        return init_wrapped

    @abc.abstractmethod
    def _dump_wrapped_from_dump_serial(self, dump_serial):
        raise NotImplementedError

    def _init_wrapped_from_dump_wrapped(self, dump_wrapped):
        return dump_wrapped

    @abc.abstractmethod
    def _init_obj_from_init_wrapped(self, init_wrapped):
        raise NotImplementedError

    @property
    def _key_order(self) -> List[str]:
        return []

    def _sort_by_keys(self, obj: OrderedDict) -> OrderedDict:
        if not isinstance(obj, dict):
            return obj
        new_obj = OrderedDict()
        obj = obj.copy()
        for sort_key in self._key_order:
            v = obj.pop(sort_key)
            new_obj[sort_key] = v
        new_obj.update(obj)
        return new_obj
    #
    # def load(self, sort=True):
    #     obj = OrderedDict(((self.arg_name, self._obj_from_repr()),))
    #     daughter_obj = self._obj_from_daugthers()
    #     obj.update(daughter_obj)
    #
    #     if sort:
    #         obj = self._sort_by_keys(obj=obj)
    #     return obj
    #
    # def dump(self, sort=True):
    #     repr = OrderedDict(((self.arg_name, self._repr_from_obj()),))
    #
    #     if sort:
    #         repr = self._sort_by_keys(obj=repr)
    #     return repr
    #
    # @property
    # def param_name(self) -> str:
    #     """Name of the object received as parameter (in signature).
    #
    #     Returns:
    #         str:
    #     """
    #     return self._param_name
    #
    # @property
    # def arg_name(self) -> str:
    #     """Name of the object when given as argument to the `super` init.
    #
    #     Returns:
    #         str:
    #     """
    #     return self._arg_name
    #
    # def _obj_from_daugthers(self) -> OrderedDict:
    #     repr = OrderedDict()
    #     for daughter in self.daughters:
    #         repr.update(daughter.load())


class CompositeRepr(BaseRepr):

    def __init__(self, obj=None, serial=None, overwrite_kwargs=None):
        super().__init__(obj, serial, overwrite_kwargs)

        init_repr, post_init = self._input_repr_init_split(self.instantiator.get_repr_init())
        self.init_repr = init_repr
        self.post_init = post_init
        self._input_overwrite_init(overwrite_kwargs=overwrite_kwargs)

    def _input_repr_init_split(self, repr_init) -> Tuple[OrderedDict, OrderedDict]:
        new_repr_init = OrderedDict()
        post_init = OrderedDict()
        for key, repr in repr_init.items():
            if repr.setter == 'init':
                new_repr_init[key] = repr
            elif callable(repr.setter):
                post_init[key] = repr
            else:
                raise ValueError()

        return new_repr_init, post_init

    def _input_overwrite_init(self, overwrite_kwargs):
        if overwrite_kwargs is None:
            overwrite_kwargs = {}

        for key, value in overwrite_kwargs.items():
            repr = self.init_repr[key]
            repr.obj_getter = lambda self: value
            self.init_repr[key] = repr

    def _get_init_wrapped_from_obj(self, obj):
        init_wrapped = OrderedDict()
        for key, repr in self.init_repr.items():
            init_wrapped[key] = repr.repr(obj=repr.obj_getter(obj))  # TODO: add more logic for copy etc.
        return init_wrapped

    def _dump_wrapped_from_dump_serial(self, dump_serial):
        dump_wrapped = OrderedDict()
        for key, serial in dump_serial.items():
            dump_wrapped[key] = self.init_repr[key].repr(serial=serial)  # TODO: add more logic for copy etc.
        return dump_wrapped

    def _dump_serial_from_dump_wrapped(self, dump_wrapped):
        dump_serial = OrderedDict()
        for key, value in dump_wrapped.items():
            if isinstance(value, BaseRepr):
                value = value.get_dump_serial()
            dump_serial[key] = value
        return dump_serial

    def _init_obj_from_init_wrapped(self, init_wrapped):
        init_obj = OrderedDict()
        for key, value in init_wrapped.items():
            if isinstance(value, BaseRepr):
                value = value.get_init_obj()
            init_obj[key] = value
        new_instance = self.instantiator(**init_obj)
        new_instance = self._apply_post_init(new_instance)
        return new_instance

    # def _apply_post_init(self, new_instance):
    #     for key, repr in self.post_init:
