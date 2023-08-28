"""
This module provides a way to create, compile, view, and save graphics based
on the LaTeX package [TikZ & PGF](https://ctan.org/pkg/pgf). It makes the
creation of TikZ graphics easier when (part of) the underlying data is
computed, and makes the preview and debugging of graphics within a Jupyter
notebook seamless.

.. include:: tikz.md
   :start-line: 4
"""

import numbers
from typing import Iterable, Union

import numpy as np

from tikz.capability import WithOptionsMixin
from tikz.options import OptsLike


class cfg:
    "tikz configuration variables"

    display_dpi = 96
    """
    resolution at which the graphic is rendered for display in the notebook

    The default is 96, the standard monitor resolution.
    """

    file_dpi = 300
    """
    resolution at which the graphic is rendered for saved PNG files

    The default is 300.
    """

    latex = "xelatex"
    """
    name of the executable used to compile the LaTeX document
    """

    demo_template = "\n".join(
        [
            '<div style="background-color:#e0e0e0;margin:0">',
            "  <div>",
            '    <div style="padding:10px;float:left">'
            '      <img src="data:image/png;base64,{0}">',
            "    </div>",
            "    <pre",
            '        style="width:47%;margin:0;padding:10px;float:right;'
            + 'white-space:pre-wrap;font-size:smaller"',
            "        >{1}</pre>",
            "  </div>",
            '  <div style="clear:both"></div>',
            "</div>",
        ]
    )
    """
    HTML template used by `Picture.demo` for notebook display

    The template must contain two placeholders: `{0}` is replaced by a
    Base64-encoded PNG-format rendering of the graphic, `{1}`by the output of
    `Picture.code`.
    """


# helper functions and helper-helper functions


def _option_code(key, val):
    """
    returns TikZ code for single option

    helper function for `_options`
    """
    # replace underscores by spaces
    key = str(key).replace("_", " ")
    if val is True:
        # omit `=True`
        return key
    else:
        return f"{key}={str(val)}"


# check types
def _str(obj):
    return isinstance(obj, str)


def _tuple(obj):
    return isinstance(obj, tuple)


def _numeric(obj):
    return isinstance(obj, numbers.Real)


def _str_or_numeric(obj):
    return _str(obj) or _numeric(obj)


def _ndarray(obj):
    return isinstance(obj, np.ndarray)


def _list(obj):
    return isinstance(obj, list)  # noqa E302


def _coordinate(coord):
    """
    check and normalize coordinate
    """
    # A coordinate can be a string with enclosing parentheses, possibly
    # prefixed by `+` or `++`, or the string 'cycle'.
    if _str(coord) and (
        (coord.startswith(("(", "+(", "++(")) and coord.endswith(")"))
        or coord == "cycle"
    ):
        return coord
    # A coordinate can be a 2/3-element tuple containing strings or numbers:
    if (
        _tuple(coord)
        and len(coord) in [2, 3]
        and all(_str_or_numeric(x) for x in coord)
    ):
        # If all strings, normalize to string.
        if all(_str(x) for x in coord):
            return "(" + ",".join(coord) + ")"
        # If all numbers, normalize to ndarray.
        if all(_numeric(x) for x in coord):
            return np.array(coord)
        # If mixed, keep.
        return coord
    # A coordinate can be a 2/3-element 1d-ndarray.
    if (
        _ndarray(coord)
        and coord.ndim == 1
        and coord.size in [2, 3]
        and all(_numeric(x) for x in coord)
    ):
        return coord
    # Otherwise, report error.
    raise TypeError(f"{coord} is not a coordinate")


def _sequence(seq, accept_coordinate=True):
    """
    check and normalize sequence of coordinates

    accept_coordinate: whether to accept a single coordinate
    """
    # A sequence can be a list.
    if _list(seq):
        # Normalize contained coordinates.
        seq = [_coordinate(coord) for coord in seq]
        # If all coordinates are 1d-ndarrays, make the sequence a 2d-ndarray.
        if all(_ndarray(coord) for coord in seq) and all(
            coord.size == seq[0].size for coord in seq
        ):
            return np.array(seq)
        return seq
    # A sequence can be a numeric 2d-ndarray with 2 or 3 columns.
    if (
        _ndarray(seq)
        and seq.ndim == 2
        and seq.shape[1] in [2, 3]
        and all(_numeric(x) for x in seq.flat)
    ):
        return seq
    # Optionally accept a coordinate and turn it into a 1-element sequence.
    if accept_coordinate:
        return _sequence([seq])
    # Otherwise, report error.
    raise TypeError(f"{seq} is not a sequence of coordinates")


def _str_or_numeric_code(x):
    """
    transform element of coordinate into TikZ representation

    Leaves string elements as is, and converts numeric elements to a
    fixed-point representation with 5 decimals precision (TikZ: ±16383.99999)
    without trailing '0's or '.'
    """
    if _str(x):
        # leave string as-is
        return x
    else:
        # convert numeric elements to a fixed-point representation with 5
        # decimals precision (TikZ: ±16383.99999) without trailing '0's or '.'
        return "{:.5f}".format(x).rstrip("0").rstrip(".")


def _coordinate_code(coord, trans=None):
    "returns TikZ code for coordinate"
    # assumes the argument has already been normalized
    if _str(coord):
        # leave string as-is
        return coord
    else:
        if trans is not None:
            coord = trans(coord)
        return "(" + ",".join(map(_str_or_numeric_code, coord)) + ")"


# coordinates


# raw object


class Raw:
    """
    raw TikZ code object

    In order to support TikZ features that are not explicitly modelled, objects
    of this class encapsulate a string which is copied as-is into the TikZ
    code. `Raw` objects can be used in place of `Operation` and `Action`
    objects. Normally it is not necessary to explicily instantiate this class,
    because the respective methods accept strings and convert them into `Raw`
    objects internally.
    """

    def __init__(self, string):
        self.string = string

    def _code(self, trans=None):
        """
        returns TikZ code

        Returns the stored string.
        """
        return self.string


# path operations (§14)


class Operation(WithOptionsMixin):
    """
    path operation

    Path operations are modelled as `Operation` objects.

    Names for `Operation` subclasses are lowercase, because from a user
    perspective they act like functions; no method call or field access should
    be performed on their instances.

    This is an abstract superclass that is not to be instantiated.
    """

    def __init__(self, opt: OptsLike):
        super().__init__(opt=opt)

    def _code(self):
        "returns TikZ code"
        pass


class moveto(Operation):
    """
    one or several move-to operations

    `coords` can be a coordinate or a sequence of coordinates.

    See [§14.1](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.1)
    """

    def __init__(self, coords, opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinates
        self.coords = _sequence(coords, accept_coordinate=True)

    def _code(self, trans=None):
        # put move-to operation before each coordinate,
        # for the first one implicitly
        return " ".join(_coordinate_code(coord, trans) for coord in self.coords)


class lineto(Operation):
    """
    one or several line-to operations of the same type

    `coords` can be a coordinate or a sequence of coordinates.

    `op` can be `'--'` for straight lines (default), `'-|'` for first
    horizontal, then vertical, or `'|-'` for first vertical, then horizontal.

    see [§14.2](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.2)
    """

    def __init__(self, coords, op="--", opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinates
        self.coords = _sequence(coords, accept_coordinate=True)
        self.op = op

    def _code(self, trans=None):
        # put line-to operation before each coordinate
        return f"{self.op} " + f" {self.op} ".join(
            _coordinate_code(coord, trans) for coord in self.coords
        )


class line(Operation):
    """
    convenience version of `lineto`

    Starts with move-to instead of line-to operation.
    """

    def __init__(self, coords, op="--", opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinates
        self.coords = _sequence(coords)
        self.op = op

    def _code(self, trans=None):
        # put line-to operation between coordinates
        # (implicit move-to before first)
        return f" {self.op} ".join(
            _coordinate_code(coord, trans) for coord in self.coords
        )


class curveto(Operation):
    """
    curve-to operation

    `coord`, `control1`, and the optional `control2` must be coordinates.

    see [§14.3](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.3)
    """

    def __init__(self, coord, control1, control2=None, opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinates
        self.coord = _coordinate(coord)
        self.control1 = _coordinate(control1)
        if control2 is not None:
            self.control2 = _coordinate(control2)
        else:
            self.control2 = None

    def _code(self, trans=None):
        code = ".. controls " + _coordinate_code(self.control1, trans)
        if self.control2 is not None:
            code += " and " + _coordinate_code(self.control2, trans)
        code += " .." + " " + _coordinate_code(self.coord, trans)
        return code


class rectangle(Operation):
    """
    rectangle operation

    `coord` must be a coordinate

    see [§14.4](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.4)
    """

    def __init__(self, coord, opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinate
        self.coord = _coordinate(coord)

    def _code(self, trans=None):
        return "rectangle " + _coordinate_code(self.coord, trans)


class circle(Operation):
    """
    circle operation

    Either `radius` or `x_radius` and `y_radius` (for an ellipse) must be
    given. If all are specified, `radius` overrides the other two options. They
    can be numbers or a string containing a number and a dimension.

    The circle is centered at the current coordinate, unless another coordinate
    is given as `at`.

    see [§14.6](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.6)
    """

    def __init__(
        self, radius=None, x_radius=None, y_radius=None, at=None, opt: OptsLike = None
    ):
        super().__init__(opt=opt)
        # overriding logic
        # Information is stored as separate radii to enable scaling.
        if radius is not None:
            self.x_radius = radius
            self.y_radius = radius
        else:
            self.x_radius = x_radius
            self.y_radius = y_radius
        # normalize coordinate
        if at is not None:
            self.at = _coordinate(at)
        else:
            self.at = None

    def _code(self, trans=None):
        kwoptions = self.kwoptions
        x_radius, y_radius = self.x_radius, self.y_radius
        if trans is not None:
            x_radius, y_radius = trans(x_radius, y_radius)
        if x_radius == y_radius:
            kwoptions["radius"] = x_radius
        else:
            kwoptions["x_radius"] = x_radius
            kwoptions["y_radius"] = y_radius
        if self.at is not None:
            kwoptions["at"] = _coordinate_code(self.at, None)
        return "circle" + self.get_opt_code()


class arc(Operation):
    """
    arc operation

    Either `radius` or `x_radius` and `y_radius` (for an elliptical arc) must
    be given. If all are specified, `radius` overrides the other two options.
    They can be numbers or a string containing a number and a dimension.

    see [§14.7](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.7)
    """

    def __init__(self, radius=None, x_radius=None, y_radius=None, opt: OptsLike = None):
        super().__init__(opt=opt)
        # overriding logic
        # Information is stored as separate radii to enable scaling.
        if radius is not None:
            self.x_radius = radius
            self.y_radius = radius
        else:
            self.x_radius = x_radius
            self.y_radius = y_radius

    def _code(self, trans=None):
        kwoptions = self.kwoptions
        x_radius, y_radius = self.x_radius, self.y_radius
        if trans is not None:
            x_radius, y_radius = trans(x_radius, y_radius)
        if x_radius == y_radius:
            kwoptions["radius"] = x_radius
        else:
            kwoptions["x_radius"] = x_radius
            kwoptions["y_radius"] = y_radius
        return "arc" + self.get_opt_code()


class grid(Operation):
    """
    grid operation

    Either `step` or `xstep` and `ystep` must be given. If all are specified,
    `step` overrides the other two options. They can be numbers or a string
    containing a number and a dimension. Specifying `step` as a coordinate is
    not supported, use `xstep` and `ystep` instead.

    see [§14.8](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.8)
    """

    def __init__(self, coord, step=None, xstep=None, ystep=None, opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinate
        self.coord = _coordinate(coord)
        # overriding logic
        # Information is stored as separate radii to enable scaling.
        if step is not None:
            self.xstep = step
            self.ystep = step
        else:
            self.xstep = xstep
            self.ystep = ystep

    def _code(self, trans=None):
        kwoptions = self.kwoptions
        xstep, ystep = self.xstep, self.ystep
        if trans is not None:
            xstep, ystep = trans(xstep, ystep)
        if xstep == ystep:
            kwoptions["step"] = xstep
        else:
            kwoptions["xstep"] = xstep
            kwoptions["ystep"] = ystep
        return "grid" + self.get_opt_code() + " " + _coordinate_code(self.coord, trans)


class parabola(Operation):
    """
    parabola operation

    `coord` and the optional `bend` must be coordinates.

    see [§14.9](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.9)
    """

    def __init__(self, coord, bend=None, opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinates
        self.coord = _coordinate(coord)
        if bend is not None:
            self.bend = _coordinate(bend)
        else:
            self.bend = None

    def _code(self, trans=None):
        code = "parabola" + self.get_opt_code()
        if self.bend is not None:
            code += " bend " + _coordinate_code(self.bend, trans)
        code += " " + _coordinate_code(self.coord, trans)
        return code


class sin(Operation):
    """
    sine operation

    `coord` must be a coordinate.

    see [§14.10](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.10)
    """

    def __init__(self, coord, opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinate
        self.coord = _coordinate(coord)

    def _code(self, trans=None):
        return "sin" + self.get_opt_code() + " " + _coordinate_code(self.coord, trans)


class cos(Operation):
    """
    cosine operation

    `coord` must be a coordinate.

    see [§14.10](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.10)
    """

    def __init__(self, coord, opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinate
        self.coord = _coordinate(coord)

    def _code(self, trans=None):
        return "cos" + self.get_opt_code() + " " + _coordinate_code(self.coord, trans)


class topath(Operation):
    """
    to-path operation

    `coord` must be a coordinate.

    see [§14.13](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.14.13)
    """

    def __init__(self, coord, opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinate
        self.coord = _coordinate(coord)

    def _code(self, trans=None):
        return "to" + self.get_opt_code() + " " + _coordinate_code(self.coord, trans)


class node(Operation):
    """
    node operation

    `contents` must be a string containing the node text, and may be LaTeX
    code.

    The optional `name` must be a string, which allows later references to the
    coordinate `(`name`)` in TikZ' node coordinate system.

    The node is positioned relative to the current coordinate, unless the
    optional coordinate `at` is given.

    Animation is not supported because it does not make sense for static
    image generation. The foreach statement for nodes is not supported because
    it can be replaced by a Python loop.

    see [§17](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#section.17)
    """

    # Provides 'headless' mode for `Scope.node` and `Scope.coordinate`
    def __init__(
        self, contents, name=None, at=None, _headless=False, opt: OptsLike = None
    ):
        super().__init__(opt=opt)
        self.name = name
        self.contents = contents
        # normalize coordinate
        if at is not None:
            self.at = _coordinate(at)
        else:
            self.at = None
        self.headless = _headless

    def _code(self, trans=None):
        if not self.headless:
            code = "node"
        else:
            code = ""
        code += self.get_opt_code()
        if self.name is not None:
            code += f" ({self.name})"
        if self.at is not None:
            code += " at " + _coordinate_code(self.at, trans)
        code += " {" + self.contents + "}"
        if self.headless:
            code = code.lstrip()
        return code


class coordinate(Operation):
    """
    coordinate operation

    `name` must be a string, which allows later references to the coordinate
    `(`name`)` in TikZ' node coordinate system.

    The node is positioned relative to the current coordinate, unless the
    optional coordinate `at` is given.

    Animation is not supported because it does not make sense for static
    image generation. The foreach statement for nodes is not supported because
    it can be replaced by a Python loop.

    see
    [§17.2.1](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsubsection.17.2.1)
    """

    def __init__(self, name, at=None, _headless=False, opt: OptsLike = None):
        super().__init__(opt=opt)
        self.name = name
        # normalize coordinate
        if at is not None:
            self.at = _coordinate(at)
        else:
            self.at = None
        self.headless = _headless

    def _code(self, trans=None):
        if not self.headless:
            code = "coordinate"
        else:
            code = ""
        code += self.get_opt_code()
        code += f" ({self.name})"
        if self.at is not None:
            code += " at " + _coordinate_code(self.at, trans)
        if self.headless:
            code = code.lstrip()
        return code


class plot(Operation):
    """
    plot operation

    `coords` can be a coordinate or a sequence of coordinates.

    The optional `to` determines whether a line-to operation is included before
    the plot operation.

    The difference between `plot coordinates` and `plot file` is not exposed;
    the decision whether to specify coordinates inline in the TikZ code or
    provide them through a file is made internally. Coordinate expressions and
    gnuplot formulas are not supported.

    see [§22](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#section.22)
    """

    def __init__(self, coords, to=False, opt: OptsLike = None):
        super().__init__(opt=opt)
        # normalize coordinates
        self.coords = _sequence(coords, accept_coordinate=True)
        self.to = to

    def _code(self, trans=None):
        # TODO: Use the 'file' variant as an alternative to 'coordinates' when
        #   there are many points.
        if self.to:
            code = "--plot"
        else:
            code = "plot"
        code += self.get_opt_code()
        code += (
            " coordinates {"
            + " ".join(_coordinate_code(coord, trans) for coord in self.coords)
            + "}"
        )
        return code


# def options(opt=None, **kwoptions):
#     """
#     in-path options
#
#     Though this is not a path operation, it can be specified at an arbitrary
#     position within a path specification. It sets options for the rest of the
#     path (unless they are path-global).
#     """
#     # just a wrapper around _options_code
#     return _options_code(opt=opt, **kwoptions)


def fontsize(size, skip=None):
    """
    code for LaTeX command to change the font size

    Can be specified e.g. as the value of a `font=` option.
    """
    if skip is None:
        # 20% leading
        skip = round(1.2 * size, 2)
    return f"\\fontsize{{{size}}}{{{skip}}}\\selectfont"


# actions on paths


def _operation(op):
    """
    check and normalize path specification elements

    The elements of a path specification argument (`*spec`) can be `Operation`
    objects (left as is), (lists of) coordinates (converted to `moveto`
    objects), and strings (converted to `Raw` objects).

    helper function for `Action`
    """
    if isinstance(op, Operation):
        # leave `Operation` as is
        return op
    if _str(op):
        # convert string to `Raw` object
        return Raw(op)
    return moveto(op)


class Action(WithOptionsMixin):
    """
    action on path

    Objects of this class are used to represent path actions. It is not
    normally necessary to instantiate this class, because `Action` objects are
    created and added implicitly by environment methods like
    [<code>Picture.path()</code>](#tikz.Scope.path).

    see [§15](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#section.15)
    """

    def __init__(self, action_name, *spec, opt: OptsLike = None):
        super().__init__(opt=opt)
        self.action_name = action_name
        # normalize path specification
        self.spec = [_operation(op) for op in spec]

    def _code(self, trans=None):
        "returns TikZ code"
        return (
            "\\"
            + self.action_name
            + self.get_opt_code()
            + " "
            + " ".join(op._code(trans) for op in self.spec)
            + ";"
        )


# environments


StrOrIterableStr = Union[str, Iterable[str]]


def StrOrIterableStr_normalise(item: StrOrIterableStr):
    if isinstance(item, str):
        return item
    return ",".join(item)


class LatexError(Exception):
    """
    error in the external LaTeX process
    """

    pass
