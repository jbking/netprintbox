ENCODING = 'utf8'


def ensure_binary_string(s):
    if isinstance(s, unicode):
        return s.encode(ENCODING)
    else:
        return s


def traverse(func, data):
    func(data)
    for item in data['contents']:
        if item['is_dir']:
            traverse(func, item)
        else:
            func(item)
