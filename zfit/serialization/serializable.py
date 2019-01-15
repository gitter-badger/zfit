import abc
from collections import OrderedDict

import pep487


class ZfitSerializable(pep487.ABC):

    @abc.abstractmethod
    def get_repr_init(self, **overwrite_kwargs) -> OrderedDict:
        """Return a Dict ("representation") of the `__init__` arguments for this class.

        Returns:
            OrderedDict:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_post_init_repr(self) -> OrderedDict:
        """Collect the "post init" functions and arguments to apply after instance creation.

        """
        raise NotImplementedError


class BaseSerializable(ZfitSerializable):

    def get_post_init_repr(self) -> OrderedDict:
        return self._get_post_init_repr()

    @abc.abstractmethod
    def _get_post_init_repr(self):
        return OrderedDict()

    def get_repr_init(self, **overwrite_kwargs) -> OrderedDict:
        return self._get_repr_init(**overwrite_kwargs)

    @abc.abstractmethod
    def _get_repr_init(self, **overwrite_kwargs):
        return OrderedDict()
