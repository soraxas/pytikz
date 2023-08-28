from .capability import WithOptionsMixin
from .core import Raw, Action, node, coordinate
from .options import OptsLike, Opts


class Scope(WithOptionsMixin):
    """
    scope environment

    A scope can be used to group path actions and other commands together, so
    that options can be applied to them in total.

    Do not instantiate this class, but use the
    [<code>scope()</code>](#tikz.Scope.addscope) method of `Picture` or
    another environment.

    see
    [§12.3.1](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsubsection.12.3.1)
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def __init__(self, opt: OptsLike = None):
        super().__init__(opt=opt)
        self.elements = []

    def _append(self, el):
        """
        append element

        Elements of an environment object can be `Action` objects (for path
        actions), `Raw` objects (for other commands), or other environment
        objects.
        """
        self.elements.append(el)

    def scope(self, **kwargs):
        """
        create and add scope to the current environment

        A `Scope` object is created, added, and returned.
        """
        s = Scope(**kwargs)
        self._append(s)
        return s

    def _code(self, trans=None):
        """
        Returns TikZ code
        """
        code = r"\begin{scope}" + self.get_opt_code() + "\n"
        code += "\n".join(el._code(trans) for el in self.elements) + "\n"
        code += r"\end{scope}"
        return code

    # add actions on paths (§15)

    def raw(self, *args):
        """
        Add arbitrary raw code.
        """
        self._append(Raw(*args))

    def path(self, *spec, **kwargs):
        """
        path action

        The `path` path action is the prototype of all path actions. It
        represents a pure path, one that is not used for drawing, filling or
        other creation of visible elements, unless instructed to do so by
        options.

        `*spec` is one or more arguments giving the path specification,
        `**kwargs` can be used to specify options.

        see [§14](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#section.14)
        """
        self._append(Action("path", *spec, **kwargs))

    def draw(self, *spec, **kwargs):
        """
        draw action

        Abbreviation for [<code>path(…, draw=True)</code>](#tikz.Scope.path).

        see
        [§15.3](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.15.3)
        """
        self._append(Action("draw", *spec, **kwargs))

    def fill(self, *spec, **kwargs):
        """
        fill action

        Abbreviation for [<code>path(…, fill=True)</code>](#tikz.Scope.path).

        see
        [§15.5](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.15.5)
        """
        self._append(Action("fill", *spec, **kwargs))

    def filldraw(self, *spec, **kwargs):
        """
        filldraw action

        Abbreviation for
        [<code>path(…, fill=True, draw=True)</code>](#tikz.Scope.path).
        """
        self._append(Action("filldraw", *spec, **kwargs))

    def pattern(self, *spec, **kwargs):
        """
        pattern action

        Abbreviation
        for [<code>path(…, pattern=True)</code>](#tikz.Scope.path).

        see
        [§15.5.1](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsubsection.15.5.1)
        """
        self._append(Action("pattern", *spec, **kwargs))

    def shade(self, *spec, **kwargs):
        """
        shade action

        Abbreviation for [<code>path(…, shade=True)</code>](#tikz.Scope.path).

        see
        [§15.7](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.15.7)
        """
        self._append(Action("shade", *spec, **kwargs))

    def shadedraw(self, *spec, **kwargs):
        """
        shadedraw action

        Abbreviation for
        [<code>path(…, shade=True, draw=True)</code>](#tikz.Scope.path).
        """
        self._append(Action("shadedraw", *spec, **kwargs))

    def clip(self, *spec, **kwargs):
        """
        clip action

        Abbreviation for [<code>path(…, clip=True)</code>](#tikz.Scope.path).

        see
        [§15.9](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.15.9)
        """
        self._append(Action("clip", *spec, **kwargs))

    def useasboundingbox(self, *spec, **kwargs):
        """
        useasboundingbox action

        Abbreviation for
        [<code>path(…, use_as_bounding_box=True)</code>](#tikz.Scope.path).

        see
        [§15.8](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsection.15.8)
        """
        self._append(Action("useasboundingbox", *spec, **kwargs))

    def node(self, contents, name=None, at=None, **kwargs):
        """
        node action

        Abbreviation for
        [<code>path(node(…))</code>](#tikz.node).

        see
        [§17.2.1](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsubsection.17.2.1)
        """
        self._append(
            Action(
                "node",
                node(contents, name=name, at=at, _headless=True),
                **kwargs,
            )
        )

    def coordinate(self, name, at=None, **kwargs):
        """
        coordinate action

        Abbreviation for
        [<code>path(coordinate(…))</code>](#tikz.coordinate).

        see
        [§17.2.1](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsubsection.17.2.1)
        """
        "coordinate action"
        self._append(
            Action(
                "coordinate",
                coordinate(name=name, at=at, _headless=True),
                **kwargs,
            )
        )

    # other commands

    def definecolor(self, name, colormodel, colorspec):
        """
        define a new color from a color specification

        Define a new color `name` from a color model `colormodel` and a color
        specification `colorspec`. All arguments are strings.

        see
        [<code>xcolor</code>
        §2.5.2](https://mirrors.nxthost.com/ctan/macros/latex/contrib/xcolor/xcolor.pdf#subsubsection.2.5.2)
        """
        if not isinstance(colorspec, str):
            colorspec = ",".join(colorspec)
        self._append(
            Raw(
                r"\definecolor"
                + "{"
                + name
                + "}{"
                + colormodel
                + "}{"
                + colorspec
                + "}"
            )
        )

    def colorlet(self, name, colorexpr):
        """
        define a new color from a color expression

        Define a new color `name` from color expression `colorexpr`. All
        arguments are strings.

        see
        [<code>xcolor</code>
        §2.5.2](https://mirrors.nxthost.com/ctan/macros/latex/contrib/xcolor/xcolor.pdf#subsubsection.2.5.2)
        """
        self._append(Raw(r"\colorlet" + "{" + name + "}{" + colorexpr + "}"))

    def tikzset(self, opt: OptsLike):
        """
        set options that apply for the rest of the current environment

        see
        [§12.4.1](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsubsection.12.4.1)
        """
        # create options string without brackets
        opt = Opts.normalise(opt)
        # because braces are needed
        self._append(Raw(r"\tikzset{" + opt.to_code(without_bracket=True) + "}"))

    def style(self, name, opt: OptsLike):
        """
        define style

        Defines a new style `name` by the given options. In the following, this
        style can be used whereever options are accepted, and acts as if these
        options had been given directly. It can also be used to override
        TikZ' default styles like the default draw style.

        see
        [§12.4.2](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsubsection.12.4.2)
        """
        # create options string without brackets
        opt = Opts.normalise(opt)
        # because braces are needed
        self._append(
            Raw(
                r"\tikzset{"
                + name
                + "/.style={"
                + opt.to_code(without_bracket=True)
                + "}}"
            )
        )
