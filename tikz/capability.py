from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tikz import options


class ToTikzCodeMixin(ABC):
    @abstractmethod
    def to_code(self) -> str:
        raise NotImplementedError()


class WithOptionsMixin(ABC):
    def __init__(self, *, opt: "options.OptsLike"):
        from tikz import options

        self._option = options.Opts.normalise(opt=opt)

    def get_opt_code(self) -> str:
        return self._option.to_code()
