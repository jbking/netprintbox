import json
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


@view_config(route_name='pin', request_method='POST')
def pin(request):
    from netprintbox.data import DropboxUser, DropboxFileInfo

    data = json.loads(request.body)
    report_token = data['report_token']
    q = DropboxUser.all().filter('report_token = ', report_token)
    if q.count() == 1:
        user = q.get()
    else:
        raise exc.HTTPUnauthorized("The report_token is not found.")
    file_info = DropboxFileInfo.get(data['file_key'])
    if file_info.parent().uid != user.uid:
        raise exc.HTTPUnauthorized("The file_key is not found.")
    if data['pin'] == 'on':
        file_info.pin = True
    elif data['pin'] == 'off':
        file_info.pin = False
    else:
        raise ValueError
    file_info.put()

    response = request.response
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Type'] = 'application/json'
    response.body = json.dumps({'pin': data['pin']})
    return response
