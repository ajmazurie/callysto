
__all__ = ("CONTENT",)

import base64
import enum
import logging
import textwrap

import html
import IPython.display

import utils

# base mimetypes that can be processed either
# here or through the IPython.display module
class CONTENT (enum.Enum):
    CSV = "text/csv"
    CSV_WITH_HEADER = "text/csv"
    HTML = "text/html"
    JPEG = "image/jpeg"
    JPG = "image/jpeg"
    JAVASCRIPT = "application/javascript"
    JS = "application/javascript"
#   PDF = "application/pdf"
    PNG = "image/png"
    SVG = "image/svg+xml"

_logger = logging.getLogger(__file__)

def _format_content (content_type, content):
    # formatting of CSV-formatted table
    if (content_type in (CONTENT.CSV, CONTENT.CSV_WITH_HEADER)):
        html_table = html.XHTML().table(style = "border: none")

        # write the header, if any
        if (content_type == CONTENT.CSV_WITH_HEADER):
            table_header = html_table.tr(style = "border: none")
            map(lambda x: table_header\
                .th(unicode(x), style = "border: none"), content[0])
            content = content[1:]

        # write the rows
        for row in content:
            table_row = html_table.tr
            map(lambda x: table_row\
                .td(style = "border: 1px solid #ccc")\
                .code(unicode(x)), row)

        return (CONTENT.HTML.value, unicode(html_table), None)

    # formatting of JavaScript code
    if (content_type in (CONTENT.JS, CONTENT.JAVASCRIPT)):
        code = \
            "<script type=\"%s\">\n" % CONTENT.JAVASCRIPT.value + \
            textwrap.dedent(content).strip() + \
            "\n</script>"

        return (CONTENT.HTML.value, code, None)

    # formatting of JPEG or PNG pictures
    if (content_type in (CONTENT.JPG, CONTENT.PNG)):
        if (isinstance(content, dict)):
            data, metadata = content["data"], {
                "width": content.get("width"),
                "height": content.get("height")}
        else:
            data, metadata = content, None

        return (content_type.value, base64.b64encode(data), metadata)

    # formatting of SVG picture
    if (content_type == CONTENT.SVG):
        # the IPython.display.SVG class does some useful
        # manipulation of the SVG XML structure when needed
        display_object = IPython.display.SVG(data = content)

        return (CONTENT.SVG.value, display_object._repr_svg_(), None)

    # pass-through formatting (will be handled by Jupyter itself)
    if (type(content_type) == CONTENT):
        content_type = content_type.value

    return (content_type, content, None)
