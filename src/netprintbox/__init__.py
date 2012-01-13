def includeme(config):
    # dropbox authz
    config.add_route('authorize', '/dropbox/authorize')
    config.add_route('authorize_callback', '/dropbox/callback')
    config.add_route('login_callback', '/dropbox/login/callback')
    config.add_route('login', '/dropbox/login')

    # task
    TASK_PREFIX = '/task'
    config.add_route('sync_all', TASK_PREFIX + '/sync')
    config.add_route('sync_for_user', TASK_PREFIX + '/check')
    config.add_route('make_report_for_user', TASK_PREFIX + '/make_report')

    # setup
    config.add_route('setup_guide', '/guide/setup')

    # feature
    config.add_route('top', '/')
    config.add_route('list_file', '/list')
    config.add_route('pin', '/pin')
    config.add_route('do_sync_for_user', '/sync')

    config.scan('netprintbox.views')
