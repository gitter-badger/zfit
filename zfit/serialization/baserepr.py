import abc
from collections import OrderedDict
from typing import List


class BaseRepr:

    def __init__(self, obj_getter=None, obj_serial=None):
        self._param_name = None
        self.obj = None
        self.obj_getter = obj_getter
        self.obj_serial = obj_serial
        self.daughters = OrderedDict()

    @abc.abstractmethod
    def _obj_from_repr(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def _key_order(self) -> List[str]:
        return []

    def _sort_objects(self, obj: OrderedDict) -> OrderedDict:
        new_obj = OrderedDict()
        for sort_key in self._key_order:
            v = obj.pop(sort_key)
            new_obj[sort_key] = v
        new_obj.update(obj)
        return new_obj

    def load(self, sort=True):
        obj = OrderedDict(((self.arg_name, self._obj_from_repr()),))
        daughter_obj = self._obj_from_daugthers()
        obj.update(daughter_obj)

        if sort:
            obj = self._sort_objects(obj=obj)
        return obj

    def dump(self, sort=True):
        repr = OrderedDict(((self.arg_name, self._repr_from_obj()),))

        if sort:
            repr = self._sort_objects(obj=repr)
        return repr

    @abc.abstractmethod
    def _repr_from_obj(self) -> OrderedDict:
        raise NotImplementedError

    @property
    def param_name(self) -> str:
        """Name of the object received as parameter (in signature).

        Returns:
            str:
        """
        return self._param_name

    @property
    def arg_name(self) -> str:
        """Name of the object when given as argument to the `super` init.

        Returns:
            str:
        """
        return self._arg_name

    def _obj_from_daugthers(self) -> OrderedDict:
        repr = OrderedDict()
        for daughter in self.daughters:
            repr.update(daughter.load())
