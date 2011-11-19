def traverse(func, data):
    func(data)
    for item in data['contents']:
        if item['is_dir']:
            traverse(func, item)
        else:
            func(item)
