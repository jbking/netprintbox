TASK_PREFIX = '/task'


def includeme(config):
    config.add_route('authorize', '/dropbox/authorize')
    config.add_route('authorize_callback', '/dropbox/callback')
    config.add_route('sync_all', TASK_PREFIX + '/sync')
    config.add_route('check_for_user', TASK_PREFIX + '/check')
    config.add_route('make_report_for_user', TASK_PREFIX + '/make_report')
    config.add_route('setup_guide', '/guide/setup')
    config.add_route('top', '/')
    config.add_route('pin', '/pin')
    config.scan('netprintbox.views')
