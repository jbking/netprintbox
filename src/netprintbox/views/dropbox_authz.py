from webob import exc
from pyramid.view import view_config


@view_config(route_name='authorize', request_method='GET')
def authorize(request):
    from netprintbox.service import DropboxService

    callback_url = request.route_url('authorize_callback')
    authz_url = DropboxService.build_authorize_url(callback_url)
    return exc.HTTPFound(location=authz_url)


@view_config(route_name='authorize_callback', request_method='GET')
def authorize_callback(request):
    from netprintbox.service import DropboxService

    request_key = request.GET['oauth_token']
    user = DropboxService.setup_user(request_key)
    setup_url = request.route_path('setup_guide',
            _query=(('key', user.access_key),))
    return exc.HTTPFound(location=setup_url)
