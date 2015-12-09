
__all__ = ("CONTENT",)

import enum

import IPython.display
import html

import utils

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
    # rendering of CSV-formatted table
    if (content_type in (CONTENT.CSV, CONTENT.CSV_WITH_HEADER)):
        html_table = html.XHTML().table(style = "border: none")

        # write the header, if any
        if (content_type == CONTENT.CSV_WITH_HEADER):
            table_header = html_table.tr
            map(lambda x: table_header.th(unicode(x)), content[0])
            content = content[1:]

        # write the rows
        for row in content:
            table_row = html_table.tr
            map(lambda x: table_row\
                .td(style = "border: 1px solid #ccc")\
                .code(unicode(x)), row)

        return (CONTENT.HTML.value, unicode(html_table))

    # rendering of JavaScript code
    if (content_type == CONTENT.JS):
        if (isinstance(content, dict)):
            kwargs = {
                "data": content.get("code"),
                "lib": content.get("lib"),
                }#"css": content.get("css")}
        else:
            kwargs = {"data": str(content)}

        display_object = IPython.display.Javascript(**kwargs)
        return (CONTENT.HTML.value,
            "<script>%s</script>" % display_object._repr_javascript_())

    # rendering of JPEG or PNG pictures
    if (content_type in (CONTENT.JPG, CONTENT.PNG)):
        if (isinstance(content, dict)):
            kwargs = {
                "data": content["data"],
                "width": content.get("width"),
                "height": content.get("height")}
        else:
            kwargs = {"data": content}

        kwargs["format"]  = {
            CONTENT.JPG: "jpg",
            CONTENT.PNG: "png"
            }[content_type]

        display_object = IPython.display.Image(**kwargs)
        return (CONTENT.HTML.value, display_object._repr_html_())

    # rendering of SVG picture
    if (content_type == CONTENT.SVG):
        display_object = IPython.display.SVG(data = content)
        return (CONTENT.HTML.value, str(display_object))

    # pass-through rendering (will be handled by Jupyter itself)
    if (type(content_type) == CONTENT):
        content_type = content_type.value

    return (content_type, content)
