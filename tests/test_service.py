from unittest import TestCase
from nose.plugins.attrib import attr

from test_utils import create_user, create_file_info, create_netprint_item


class ServiceTestBase(TestCase):
    def setUp(self):
        from google.appengine.ext.testbed import Testbed

        self.testbed = Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()


class NetprintboxServiceTest(ServiceTestBase):
    def _getOUT(self, user):
        from netprintbox.service import NetprintboxService
        return NetprintboxService(user)

    @attr('unit', 'light')
    def test_construct_data_to_make_report(self):
        from netprintbox.data import FileState
        from netprintbox.utils import normalize_name as normalize

        user = create_user()
        create_file_info(user,
                         path='/need_netprint_id.data',
                         netprint_name=normalize('/need_netprint_id.data'),
                         state=FileState.NEED_NETPRINT_ID)
        create_file_info(user,
                         path='/latest.data',
                         netprint_id='latest',
                         netprint_name=normalize('/latest.data'),
                         state=FileState.LATEST)

        class netprint(object):
            @staticmethod
            def list():
                return [
                        create_netprint_item(
                            id='need_xxxx',
                            name=normalize('/need_netprint_id.data')),
                        create_netprint_item(
                            id='uncontrolled',
                            name='uncontrolled.jpg'),
                        create_netprint_item(
                            id='latest',
                            name=normalize('/latest.data')),
                       ]

        service = self._getOUT(user)
        service.netprint = netprint

        (need_report, result) = service._make_report()
        self.assertTrue(need_report)
        self.assertItemsEqual(
            [(item['id'], item['name'], item['controlled'])
             for item in result],
            [('need_xxxx', normalize('/need_netprint_id.data'), True),
             ('uncontrolled', 'uncontrolled.jpg', False),
             ('latest', normalize('/latest.data'), True),
            ])

    @attr('unit', 'light')
    def test_donot_make_report_if_no_change(self):
        from netprintbox.data import FileState
        from netprintbox.utils import normalize_name as normalize

        user = create_user()
        create_file_info(user,
                         path='/latest.data',
                         netprint_id='latest',
                         netprint_name=normalize('/latest.data'),
                         state=FileState.LATEST)

        class netprint(object):
            @staticmethod
            def list():
                return [
                        create_netprint_item(
                            id='latest',
                            name=normalize('/latest.data')),
                       ]

        service = self._getOUT(user.key())
        service.netprint = netprint

        (need_report, _result) = service._make_report()
        self.assertFalse(need_report)
