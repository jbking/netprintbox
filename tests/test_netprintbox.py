from StringIO import StringIO
from unittest import TestCase
from nose.plugins.attrib import attr


class ObtainLimitTest(TestCase):
    def _getOUT(self):
        from commands.netprintbox import put_from_dropbox
        return put_from_dropbox

    @attr('unit', 'light')
    def test_under_limit(self):
        command = self._getOUT()
        DATA = ' ' * (2 * 1024 * 1024)

        class dropbox_client(object):
            @staticmethod
            def get_file(path):
                f = StringIO(DATA)
                f.length = len(DATA)
                return f

        result = []

        class netprintbox_client(object):
            @staticmethod
            def send(file_obj):
                result.append(file_obj)

        command(dropbox_client, netprintbox_client,
                {'path': '/under_limit.dat'}, None)

        self.assertEqual(len(result), 1)
        f = result[0]
        f.seek(0)
        self.assertEqual(f.name, '/under_limit.dat')
        self.assertEqual(f.read(), DATA)

    @attr('unit', 'light')
    def test_over_limit(self):
        from commands.dropbox import OverLimit
        command = self._getOUT()
        DATA = ' ' * (2 * 1024 * 1024 + 1)

        class dropbox_client(object):
            @staticmethod
            def get_file(path):
                f = StringIO(DATA)
                f.length = len(DATA)
                return f

        class netprintbox_client(object):
            pass

        self.assertRaises(OverLimit, command,
                          dropbox_client, netprintbox_client,
                          {'path': 'dummy'}, None)
