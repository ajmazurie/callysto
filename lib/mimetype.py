
__all__ = ("CONTENT",)

import IPython.display
import html

import enum

# base mimetypes that can be processed either
# here or through the IPython.display module
class CONTENT (enum.Enum):
    CSV = "text/csv"
    CSV_WITH_HEADER = "text/csv"
    HTML = "text/html"
    JPG = "image/jpeg"
    JS = "application/javascript"
#   PDF = "application/pdf"
    PNG = "image/png"
    SVG = "image/svg+xml"

def _process_content (content_type, content):
    if (content_type in (CONTENT.JPG, CONTENT.PNG)):
        display_object = IPython.display.Image(
            data = content,
            format = {
                CONTENT.JPG: "jpg",
                CONTENT.PNG: "png"
                }[content_type])

        return (CONTENT.HTML.value, display_object._repr_html_())

    if (content_type == CONTENT.JS):
        display_object = IPython.display.Javascript(data = content)
        return (CONTENT.HTML.value, display_object._repr_javascript_())

    if (content_type == CONTENT.SVG):
        display_object = IPython.display.SVG(data = content)
        return (CONTENT.HTML.value, display_object._data)

    if (content_type in (CONTENT.CSV, CONTENT.CSV_WITH_HEADER)):
        html_table = html.XHTML().table()

        # write the header, if any
        if (content_type == CONTENT.CSV_WITH_HEADER):
            table_header = html_table.tr
            map(lambda x: table_header.th(unicode(x)), content[0])
            content = content[1:]

        # write the rows
        for row in content:
            table_row = html_table.tr
            map(lambda x: table_row.td(unicode(x)), row)

        return (CONTENT.HTML.value, unicode(html_table))

    if (type(content_type) == CONTENT):
        content_type = content_type.value

    return (content_type, content)
