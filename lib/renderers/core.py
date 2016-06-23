# core mimetypes and associated renderers, renderers
# (de)registration mechanisms, and rendering methods

__all__ = (
    "MIME_TYPE",
    "register_renderer",
    "deregister_renderer",
    "list_renderers_for_mime_type",
    "list_mime_types_for_renderer")

import base64
import enum
import fnmatch
import inspect
import logging
import textwrap

import future.utils
import html
import IPython.display

from .. import utils

# base mimetypes
class MIME_TYPE (enum.Enum):
    TEXT = "text/plain"
    CSV = "text/csv"
    CSV_WITH_HEADER = "text/csv;header"
    GIF = "image/gif"
    HTML = "text/html"
    JAVASCRIPT = "application/javascript"
    JPEG = "image/jpeg"
    JPG = "image/jpeg"
    PNG = "image/png"
    SVG = "image/svg+xml"

_logger = logging.getLogger(__name__)

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

_renderers = []

def _validate_mime_type (mime_type):
    if (utils.is_string(mime_type)):
        return mime_type.lower().strip()
    # if not a string, mime_type has to be an enum
    elif (isinstance(mime_type, MIME_TYPE)):
        return mime_type.value

    raise ValueError("Invalid MIME type: %s" % mime_type)

def register_renderer (renderer, mime_type):
    global _renderers

    if (not utils.is_callable(renderer)):
        raise ValueError("Invalid renderer: not a function")

    if (not utils.is_iterable(mime_type)):
        mime_types = (mime_type,)
    else:
        mime_types = mime_type

    for mime_type in mime_types:
        mime_type = _validate_mime_type(mime_type)

        _renderers.insert(0, (renderer, mime_type))
        _logger.debug("added renderer for %s: %s" % (mime_type, renderer))

def deregister_renderer (renderer, mime_type = None):
    global _renderers

    if (mime_type is None):
        seeve = lambda x: (x[0] == renderer)
    else:
        mime_type = _validate_mime_type(mime_type)
        seeve = lambda x: (x[0] == renderer) and (x[1] == mime_type)

    previous_n_renderers = len(_renderers)
    _renderers = filter(lambda x: not seeve(x), _renderers)

    if (len(_renderers) == previous_n_renderers):
        msg = "Renderer %s not found" % renderer
        if (mime_type is not None):
            msg += " for MIME type %s" % mime_type
        raise Exception(msg)

    _logger.debug("removed renderer %s" % renderer)

def list_renderers_for_mime_type (mime_type, return_mime_type = False):
    mime_type, matching_renderers = _validate_mime_type(mime_type), []

    for (renderer, mime_type_) in _renderers:
        if (fnmatch.fnmatch(mime_type_, mime_type)):
            matching_renderers.append((renderer, mime_type_))

    if (return_mime_type):
        return (mime_type, matching_renderers)
    else:
        return matching_renderers

def list_mime_types_for_renderer (renderer):
    matching_mime_types = []

    for (renderer_, mime_type_) in _renderers:
        if (renderer_ == renderer):
            matching_mime_types.append((renderer, mime_type_))

    return matching_mime_types

def _check_frames (frames):
    if (not inspect.isgenerator(frames)):
        raise Exception("Invalid frames: not a generator")

    # ensure the frames are in a valid format; valid formats are
    # - <data>  -- will be assumed to be plain text
    # - (<mime_type>, <data>)
    # - (<mime_type>, <data>, <metadata>)
    for (n, frame) in enumerate(frames):
        if (frame is None):
            yield None

        elif (not utils.is_iterable(frame)):
            # default content type is plain text
            yield (MIME_TYPE.TEXT.value, unicode(frame), None)

        else:
            try:
                assert (utils.is_iterable(frame)), "Not an iterable"
                frame = list(frame)
                frame_length = len(frame)

                if (frame_length == 2):
                    (mime_type_, content_), metadata_ = frame, None
                elif (frame_length == 3):
                    (mime_type_, content_, metadata_) = frame
                else:
                    raise Exception("Unexpected tuple length: %d" % frame_length)

                yield (_validate_mime_type(mime_type_), content_, metadata_)

            except Exception as e:
                raise Exception("Invalid frame #%d: %s" % (n+1, e))

def _render_content (mime_type, content, metadata):
    def get_frames (mime_type, content, metadata):
        mime_type, renderers = list_renderers_for_mime_type(mime_type, True)
        metadata = {} if (metadata is None) else metadata

        # pass-through rendering (will be handled by Jupyter itself)
        if (len(renderers) == 0):
            _logger.debug("no renderer found for content type %s" % mime_type)
            return [((mime_type, content, metadata), True)]

        # delegated rendering
        try:
            renderer, _ = renderers[0]
            frames = []
            for frame in _check_frames(renderer(content, mime_type, **metadata)):
                # if we get a None value from the renderer, we interpret it
                # as asking for the last frame sent to be renderered as is
                if (frame is None):
                    if (len(frames) > 0):
                        frames[-1][1] = True
                # by default, we want to send this
                # frame to any compatible renderer
                else:
                    frames.append([frame, False])

            return frames

        except Exception as exception:
            future.utils.raise_with_traceback(Exception(
                "Error while rendering MIME type %s with renderer %s: %s" % (
                    mime_type, renderer, exception)))

    # generate frame(s) out of this content
    frames = get_frames(mime_type, content, metadata)

    # if frames are not explicitly set to 'as is' (by having a None
    # yielded right after them by the renderer) then we'll attempt to
    # feed them to any compatible renderer until they are not set so
    while True:
        subframes = {}
        for (i, (frame, as_is)) in enumerate(frames):
            if (not as_is):
                subframes[i] = get_frames(*frame)

        if (len(subframes) == 0):
            break

        frames_ = []
        for (i, frame) in enumerate(frames):
            if (i in subframes):
                frames_.extend(subframes[i])
            else:
                frames_.append(frame)

        frames = frames_

    return [frame for (frame, as_is) in frames]

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def _ensure_no_metadata (metadata):
    if (len(metadata) > 0):
        raise Exception("Unknown metadata %s: %s" % (
            utils.plural("field", len(metadata)),
            ', '.join(sorted(metadata))))

def base_text_renderer (content, mime_type, **metadata):
    if ("encoding" in metadata):
        content = unicode(content, metadata["encoding"])

    yield (MIME_TYPE.TEXT, content)
    yield None

register_renderer(base_text_renderer, MIME_TYPE.TEXT)

# CSV-formatted table renderer
def _base_csv_renderer (content, with_header):
    html_table = html.XHTML().table(style = "border: none")

    # write the header, if any
    if (with_header):
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

    return (MIME_TYPE.HTML, unicode(html_table))

def default_csv_without_header_renderer (content, mime_type, **metadata):
    _ensure_no_metadata(metadata)
    yield _base_csv_renderer(content, with_header = False)
    yield None

register_renderer(
    default_csv_without_header_renderer, MIME_TYPE.CSV)

def default_csv_with_header_renderer (content, mime_type, **metadata):
    _ensure_no_metadata(metadata)
    yield _base_csv_renderer(content, with_header = True)
    yield None

register_renderer(
    default_csv_with_header_renderer, MIME_TYPE.CSV_WITH_HEADER)

# JPG and PNG image renderer
def default_image_renderer (content, mime_type, **metadata):
    for key in metadata:
        if (not key in ("width", "height")):
            raise Exception("Unknown metadata field: %s" % key)
        try:
            float(metadata[key])
        except:
            raise Exception("Invalid value for metadata field '%s': %s" % (
                key, metadata[key]))

    yield (mime_type, base64.b64encode(content), metadata)
    yield None

register_renderer(default_image_renderer, MIME_TYPE.GIF)
register_renderer(default_image_renderer, MIME_TYPE.JPEG)
register_renderer(default_image_renderer, MIME_TYPE.JPG)
register_renderer(default_image_renderer, MIME_TYPE.PNG)

# SVG canvas renderer
def default_svg_renderer (content, mime_type, **metadata):
    _ensure_no_metadata(metadata)

    # we use the IPython.display.SVG class as it does some
    # handy manipulation of the XML structure, when needed
    display_object = IPython.display.SVG(data = content)

    yield (mime_type, display_object._repr_svg_())
    yield None

register_renderer(default_svg_renderer, MIME_TYPE.SVG)

# JavaScript code renderer
def default_javascript_renderer (content, mime_type, **metadata):
    for key in metadata:
        if (key != "modules"):
            raise Exception("Unknown metadata field: %s" % key)

    modules = metadata.get(key, [])
    if (not isinstance(modules, dict)):
        raise Exception(
            "Invalid value for metadata field 'modules': %s" % modules)

    wrapper = "<script type=\"application/javascript\">\n%s\n</script>"
    code = textwrap.dedent(content).strip()

    if (len(modules) > 0):
        paths = [{"prefix": k, "path": v} for (k, v) in modules.iteritems()]

        module_prefixes = "\"%s"

        wrapper = wrapper % """\
            require.config({
                paths: {
                    %(paths)s
                },
                shim: {%(dependencies)s}
            });

            require([%(module_quoted_prefixes)s], function(%(module_prefixes)s) {
                %%s
            });
            """

    yield (MIME_TYPE.HTML, wrapper % code)
    yield None

register_renderer(default_javascript_renderer, MIME_TYPE.JAVASCRIPT)
