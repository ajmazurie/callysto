
import operator
import unittest

import callysto
from commons import *

def dummy_renderer (content, mime_type):
    yield (callysto.mime_type.TEXT, str(content))

class RenderersRegistrationTests (unittest.TestCase):

    def test_registering_and_deregistering_renderer (self):
        # there should be no renderer for our fake mimetypes
        self.assertEqual(
            callysto.renderers.list_renderers_for_mime_type("dummy/*"), [])

        # if we add a same renderer for multiple mimetypes,
        callysto.renderers.register_renderer(dummy_renderer,
            ("dummy/vnd.a", "dummy/vnd.b"))

        # then we should see it when asking for
        # the renderer(s) of these mimetypes,
        self.assertEqual(
            callysto.renderers.list_renderers_for_mime_type("dummy/vnd.a"),
            [(dummy_renderer, "dummy/vnd.a")])

        self.assertEqual(
            callysto.renderers.list_renderers_for_mime_type("dummy/vnd.b"),
            [(dummy_renderer, "dummy/vnd.b")])

        # and the registration should be last-in first-out
        self.assertEqual(
            callysto.renderers.list_renderers_for_mime_type("dummy/*"),
            [(dummy_renderer, "dummy/vnd.b"),
             (dummy_renderer, "dummy/vnd.a")])

        self.assertEqual(
            callysto.renderers.list_mime_types_for_renderer(dummy_renderer),
            [(dummy_renderer, "dummy/vnd.b"),
             (dummy_renderer, "dummy/vnd.a")])

        # after we de-register it,
        callysto.renderers.deregister_renderer(dummy_renderer)

        # then we should not see it
        self.assertEqual(
            callysto.renderers.list_renderers_for_mime_type("dummy/*"), [])

        # we can also de-register a renderer for a specific mimetype,
        callysto.renderers.register_renderer(dummy_renderer, "dummy/vnd.a")
        callysto.renderers.register_renderer(dummy_renderer, "dummy/vnd.b")
        callysto.renderers.deregister_renderer(dummy_renderer, "dummy/vnd.a")

        # and confirm that we only de-registered the right mimetype rendering
        self.assertEqual(
            callysto.renderers.list_renderers_for_mime_type("dummy/*"),
            [(dummy_renderer, "dummy/vnd.b")])

    def test_mime_type_check (self):
        # each of the known content types should be recognized as valid
        for mime_type in callysto.MIME_TYPE:
            mime_type_ = callysto.renderers.core._validate_mime_type(mime_type)
            self.assertEqual(mime_type.value, mime_type_)

        # .. as is any string type
        mime_type_ = callysto.renderers.core._validate_mime_type("dummy")
        self.assertEqual(mime_type_, "dummy")

        # each of the known content types can be
        # converted to its mime type without error
        for mime_type in callysto.MIME_TYPE:
            callysto.renderers.core._validate_mime_type(mime_type)

if (__name__ == "__main__"):
    unittest.main()
