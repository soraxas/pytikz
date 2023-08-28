from functools import lru_cache
from typing import Iterable, Union, Dict

from .capability import ToTikzCodeMixin


class Opts(ToTikzCodeMixin):
    def __init__(
        self,
        *option: Iterable[str],
        underscore_to_space: bool = True,
        **kw_option,
    ):
        assert isinstance(option, (list, tuple))
        self.options = option
        self.kw_option = kw_option
        self.underscore_to_space = underscore_to_space

    def _normalise_key_val(self, key: str, val: Union[str, bool]) -> str:
        if self.underscore_to_space:
            key = str(key).replace("_", " ")
        key_value_pair = [key]
        if val is not True:
            # tikz can omit value that is mapped to True value
            # omit `=True`
            key_value_pair.append(val)
        return "=".join(map(str, key_value_pair))

    @classmethod
    def _nested_str_list_to_str(cls, obj):
        if obj is None:
            return ""
        if isinstance(obj, (list, tuple)):
            return ",".join(map(str, (cls._nested_str_list_to_str(o) for o in obj)))
        return str(obj)

    # noinspection PyTypeChecker
    @lru_cache()
    def to_code(self, without_bracket: bool = False) -> str:
        out = self._nested_str_list_to_str(self.options)
        out += ",".join(
            map(lambda x: self._normalise_key_val(*x), self.kw_option.items()),
        )
        if not without_bracket and len(out) > 0:
            out = f"[{out}]"
        return out

    @classmethod
    def normalise(cls, opt: "OptsLike") -> "Opts":
        if isinstance(opt, Opts):
            return opt
        if isinstance(opt, dict):
            return Opts(**opt)
        if isinstance(opt, str):
            return Opts([opt])
        return Opts(opt)

    def __repr__(self):
        return self.to_code()


OptsLike = Union[Opts, str, Iterable[str], Dict]
