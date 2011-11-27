import data


def create_user(**kwargs):
    default = {
            'uid': 'uid',
            'email': 'email',
            'display_name': 'display_name',
            'access_key': 'access_key',
            'access_secret': 'access_secret',
        }
    params = dict(default)
    params.update(kwargs)
    user = data.DropboxUser(**params)
    user.put()
    return user


def create_file_info(user, **kwargs):
    default = {
            'path': '/path',
            'size': 1,
            'rev': 'rev',
            'netprint_name': 'path',
        }
    params = dict(default)
    params['parent'] = user
    params.update(kwargs)
    file_info = data.DropboxFileInfo(**params)
    file_info.put()
    return file_info
