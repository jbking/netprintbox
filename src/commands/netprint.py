def ls(client):
    return client.list()


def delete_file(client, name):
    client.delete(name)
