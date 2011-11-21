def create_user(**kwargs):
    import data

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
