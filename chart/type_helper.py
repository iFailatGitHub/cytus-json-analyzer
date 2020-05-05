from enum import Enum
from typing import Any, Callable, List, TypeVar, Type, Union, cast

T = TypeVar("T")
EnumT = TypeVar("EnumT", bound=Enum)

def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool), f"{x} is not an integer."
    return x


def to_enum(c: Type[EnumT], x: Any) -> EnumT:
    assert isinstance(x, c), f"{x} is not an instance of {c}."
    return x.value


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list), f"{x} is not a list of {f}."
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c), f"{x} is not an instance of {c}"
    return cast(Any, x).to_dict()


def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool), \
        f"{x} is not a float."
    return float(x)


def from_bool(x: Any) -> bool:
    assert isinstance(x, bool), f"{x} is not a boolean."
    return x


def to_float(x: Any) -> float:
    assert isinstance(x, float), f"{x} is not a float."
    return x

def from_str(x: Any) -> str:
    assert isinstance(x, str), f"{x} is not a string."
    return x

def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False, f"{x} is not the ff. classes: {fs}"

def from_none(x: Any) -> Any:
    assert x is None, f"{x} is not None."
    return x
