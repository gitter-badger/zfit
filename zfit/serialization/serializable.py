import abc
from collections import OrderedDict

import pep487


class ZfitSerializable(pep487.ABC):

    @classmethod
    @abc.abstractmethod
    def get_repr_init(cls, **overwrite_kwargs) -> OrderedDict:
        """Return a Dict ("representation") of the `__init__` arguments for this class.

        Returns:
            OrderedDict:
        """
        raise NotImplementedError


class BaseSerializable(ZfitSerializable):

    @classmethod
    def get_repr_init(cls, **overwrite_kwargs) -> OrderedDict:
        repr_init = cls._get_repr_init()
        return repr_init

    @classmethod
    @abc.abstractmethod
    def _get_repr_init(cls, **overwrite_kwargs):
        return OrderedDict()
