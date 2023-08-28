import atexit
import base64
import hashlib
import html
import os
import shutil
import subprocess
import tempfile
from typing import Optional

import IPython.display
import fitz

from tikz import StrOrIterableStr, StrOrIterableStr_normalise, cfg, LatexError
from tikz.scope import Scope


class Picture(Scope):
    """
    tikzpicture environment

    This is the central class of the module. A picture is created by
    instantiating `Picture` and calling its methods. The object represents both
    the whole LaTeX document and its single `tikzpicture` environment.

    Set `tempdir` to use a specific directory for temporary files instead of an
    automatically created one. Set `cache` to `False` if the picture should be
    generated even though the TikZ code has not changed.

    see
    [§12.2.1](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#subsubsection.12.2.1)
    """

    def __init__(
        self,
        *,
        usetikzlibrary: Optional[StrOrIterableStr] = None,
        tikzset: Optional[StrOrIterableStr] = None,
        tempdir: Optional[str] = None,
        cache: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        # additional preamble entries
        self.preamble = []
        self.document_codes = []
        # should the created PDF be cached?
        self.cache = cache
        # create temporary directory for pdflatex etc.
        if tempdir is None:
            self.tempdir = tempfile.mkdtemp(prefix="tikz-")
            # make sure it gets deleted
            atexit.register(shutil.rmtree, self.tempdir, ignore_errors=True)
        else:
            self.tempdir = tempdir

        if usetikzlibrary is not None:
            self.usetikzlibrary(StrOrIterableStr_normalise(usetikzlibrary))

        if tikzset is not None:
            self.tikzset(StrOrIterableStr_normalise(tikzset))

    def add_preamble(self, code):
        """
        add code to preamble

        Adds arbitrary LaTeX code to the document preamble. Since the code will
        typically contain backslash characters, use of a Python 'raw' string is
        recommended.

        If the method is called multiple times with the same arguments, the
        code is only added once.
        """
        if code not in self.preamble:
            self.preamble.append(code)

    def usetikzlibrary(self, name):
        """
        use TikZ library

        Makes the functionality of the TikZ library `name` available.

        This adds a `\\usetikzlibrary` command to the preamble of the LaTeX
        document. If the method is called multiple times with the same
        arguments, only one such command is added.

        see
        [Part V](https://pgf-tikz.github.io/pgf/pgfmanual.pdf#part.5)
        """
        self.add_preamble(r"\usetikzlibrary{" + name + "}")

    def usepackage(self, name, options=None):
        """
        use LaTeX package

        Makes the functionality of the LaTeX package `name` available. If
        specified, package <code>options</code> are set.

        This adds a `\\usepackage` command to the preamble of the LaTeX
        document. If the method is called multiple times with the same
        arguments, only one such command is added.
        """
        code = r"\usepackage"
        if options is not None:
            code += "[" + options + "]"
        code += "{" + name + "}"
        self.add_preamble(code)

    def add_document_code(self, code):
        self.document_codes.append(code)

    def fira(self):
        """
        set font to Fira, also for math

        Warning: Fira Math works only with xelatex and lualatex!
        """
        self.usepackage("FiraSans", "sfdefault")
        self.usepackage("unicode-math", "mathrm=sym")
        self.add_preamble(
            r"\setmathfont{Fira Math}[math-style=ISO,"
            "bold-style=ISO,nabla=upright,partial=upright]"
        )

    # code / pdf creation: private
    # private functions assume that code / pdf has already been created

    def _update(self, build=True):
        "ensure that up-to-date code & PDF file exists"

        sep = os.path.sep

        # create tikzpicture code
        code = (
            r"\begin{tikzpicture}"
            + self.get_opt_code()
            + "\n"
            + "\n".join(el._code() for el in self.elements)
            + "\n"
            + r"\end{tikzpicture}"
        )
        self._code = code

        # create document code
        # standard preamble
        codelines = [
            r"\documentclass{article}",
            r"\usepackage{tikz}",
            r"\usetikzlibrary{external}",
            r"\tikzexternalize",
        ]
        # user-added preamble
        codelines += self.preamble
        # document body
        codelines += [
            r"\begin{document}",
            "\n".join(self.document_codes),
            self._code,
            r"\end{document}",
        ]
        code = "\n".join(codelines)
        self._document_code = code
        if not build:
            return

        # We don't want a PDF file of the whole LaTeX document, but only of the
        # contents of the `tikzpicture` environment. This is achieved using
        # TikZ' `external` library, which makes TikZ write out pictures as
        # individual PDF files. To do so, in a normal pdflatex run TikZ calls
        # pdflatex again with special arguments. We use these special
        # arguments directly. See section 53 of the PGF/TikZ manual.

        # does the PDF file have to be created?
        #  This check is implemented by using the SHA1 digest of the LaTeX code
        # in the PDF filename, and to skip creation if that file exists.
        hash = hashlib.sha1(code.encode()).hexdigest()
        self.temp_pdf = self.tempdir + sep + "tikz-" + hash + ".pdf"
        if self.cache and os.path.isfile(self.temp_pdf):
            return

        # create LaTeX file
        temp_tex = self.tempdir + sep + "tikz.tex"
        with open(temp_tex, "w") as f:
            f.write(code + "\n")

        # process LaTeX file into PDF
        completed = subprocess.run(
            [
                cfg.latex,
                "-jobname",
                "tikz-figure0",
                r"\def\tikzexternalrealjob{tikz}\input{tikz}",
            ],
            cwd=self.tempdir,
            capture_output=True,
            text=True,
        )
        self.latex_completed = completed
        if completed.returncode != 0:
            raise LatexError("LaTeX has failed\n" + completed.stdout)

        # rename created PDF file
        os.rename(self.tempdir + sep + "tikz-figure0.pdf", self.temp_pdf)

    def _get_SVG(self):
        "return SVG data of `Picture`"
        # convert PDF to SVG using PyMuPDF
        doc = fitz.open(self.temp_pdf)
        page = doc.load_page(0)
        svg = page.get_svg_image()
        return svg

    def _get_PNG(self, dpi=None):
        "return PNG data of `Picture`"
        if dpi is None:
            dpi = cfg.display_dpi
        # convert PDF to PNG using PyMuPDF
        zoom = dpi / 72
        doc = fitz.open(self.temp_pdf)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes()

    # code / pdf creation: public
    # public functions make sure that code / pdf is created via `_update`

    def code(self):
        "returns TikZ code"
        self._update(build=False)
        return self._code

    def document_code(self):
        "returns LaTeX/TikZ code for a complete compilable document"
        self._update(build=False)
        return self._document_code

    def write_image(self, filename, dpi=None):
        """
        write picture to image file

        The file type is determined from the file extension, and can be PDF,
        PNG, or SVG. For PDF, the file created by LaTeX is copied to
        `filename`. For PNG, the PDF is rendered to a bitmap. If the
        resolution `dpi` is not specified, `cfg.file_dpi` is used. For
        SVG, the PDF is converted to SVG.

        Rendering and conversion are performed by the
        [MuPDF library](https://mupdf.com/) through the Python binding
        [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/).
        """
        if dpi is None:
            dpi = cfg.file_dpi
        self._update()
        # determine extension
        _, ext = os.path.splitext(filename)
        # if a PDF is requested,
        if ext.lower() == ".pdf":
            # just copy the file
            shutil.copyfile(self.temp_pdf, filename)
        elif ext.lower() == ".png":
            # render PDF as PNG using PyMuPDF
            zoom = dpi / 72
            doc = fitz.open(self.temp_pdf)
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True)
            pix.save(filename)
        elif ext.lower() == ".svg":
            # convert PDF to SVG using PyMuPDF
            svg = self._get_SVG()
            with open(filename, "w") as f:
                f.write(svg)
        else:
            raise ValueError(f"format {ext[1:]} is not supported")

    def _repr_mimebundle_(self, include, exclude, **kwargs):
        "display image in notebook"
        # For the "plot viewer" of vscode-python to be activated, apparently it
        # is necessary to provide both a PNG and an SVG.
        # Note that SVG rendering in the "plot viewer" is not entirely
        # accurate, see https://github.com/microsoft/vscode-python/issues/13080
        self._update()
        data = {"image/png": self._get_PNG(), "image/svg+xml": self._get_SVG()}
        return data

    def safe_get_png(self, dpi):
        """
        This function either returns an encoded PNG string, or None. It will not throw.
        """
        try:
            return self._get_PNG(dpi=dpi)
        except LatexError as le:
            message = le.args[0]
            tikz_error = message.find("! ")
            if tikz_error != -1:
                message = message[tikz_error:]
            print("LatexError: LaTeX has failed")
            print(message)
        return None

    def show(self, dpi=None):
        self._update()
        return IPython.display.Image(self.safe_get_png(dpi=dpi))

    def demo(self, dpi: int = None):
        """
        show picture and code in the notebook

        This is a convenience function meant to aid development and debugging
        of a picture in a Jupyter notebook. It creates an output cell that (by
        default) contains the rendered picture on the left and the
        corresponding TikZ code on the right. This layout can be modified via
        `cfg.demo_template`. The optional argument `dpi` can be used to
        override the default `cfg.display_dpi`.
        """
        self._update()
        _png_data = self.safe_get_png(dpi=dpi)
        if _png_data is None:
            png_base64 = ""
        else:
            png_base64 = base64.b64encode(_png_data).decode("ascii")
        code_escaped = html.escape(self._code)
        IPython.display.display(
            IPython.display.HTML(cfg.demo_template.format(png_base64, code_escaped))
        )
