import webapp2
import dropbox
import settings
import data


def get_session():
    return dropbox.session.DropboxSession(settings.DROPBOX_APP_KEY,
                                          settings.DROPBOX_APP_SECRET,
                                          settings.DROPBOX_ACCESS_TYPE)


class AuthHandler(webapp2.RequestHandler):
    def get(self):
        session = get_session()
        request_token = session.obtain_request_token()
        token = data.OAuthRequestToken()
        token.key = request_token.key
        token.token = str(request_token)
        token.put()
        callback_url = 'http://localhost:8080/dropbox_callback'
        authz_url = session.build_authorize_url(request_token, callback_url)
        self.response.status = 302
        self.response.headerlist = [('Location', authz_url)]


class AuthCallbackHandler(webapp2.RequestHandler):
    def get(self):
        key = self.request.GET['oauth_token']
        request_token = data.OAuthRequestToken.get(key)

        session = get_session()
        session.obtain_access_token(request_token)
        client = dropbox.client.DropboxClient(session)
        account_info = client.account_info()

        user = data.DropboxUser(uid=str(account_info['uid']),
                                email=account_info['email'],
                                display_name=account_info['display_name'],
                                access_key=session.token.key,
                                access_secret=session.token.secret)
        user.put()

        data.OAuthRequestToken.delete(key)

        self.response.status = 200
        self.response.write("Saved :)")
