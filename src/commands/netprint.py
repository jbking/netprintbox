def ls(client):
    return client.list()


def delete_file(client, netprint_id):
    client.delete(netprint_id)
