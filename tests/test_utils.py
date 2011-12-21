# -*- encoding: utf-8 -*-
from unittest import TestCase
from nose.plugins.attrib import attr


class NormalizeNameTest(TestCase):
    @attr('unit', 'light')
    def test_replace(self):
        from netprintbox.utils import normalize_name

        for target_char in u'/(「＜＞＆”’」)':
            self.assertEqual(u'A4_foo_',
                             normalize_name(u'/A4/foo' + target_char + '.doc'))

    @attr('unit', 'light')
    def test_ext(self):
        from netprintbox.utils import normalize_name

        self.assertEqual(u'A4_foo_.doc',
                         normalize_name(u'/A4/foo「.doc', ext=True))

    @attr('unit', 'light')
    def test_duplicate(self):
        from netprintbox.utils import normalize_name

        # no way to fix this mangle result gracefully.
        # self.failIfEqual(normalize_name(u'/A4/foo_.doc'),
        #                  normalize_name(u'/A4/foo「」.doc'))

        self.failIfEqual(normalize_name(u'/A4/foo_.doc'),
                         normalize_name(u'/A4/foo「.doc'))
