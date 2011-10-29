# -*- encoding: utf8 -*-
import random
import sys
import os
import mimetypes


OS_FILESYSTEM_ENCODING = sys.getfilesystemencoding()


def is_multipart(data):
    for value in data.values():
        if isinstance(value, file):
            return True
    return False


def encode_multipart_data(data):
    getRandomChar = lambda: chr(random.choice(range(97, 123)))
    randomChar = [getRandomChar() for x in xrange(20)]
    boundary = "----------%s" % ("".join(randomChar))
    lines = ["--" + boundary]
    for key, value in data.iteritems():
        header = 'Content-Disposition: form-data; name="%s"' % key
        if hasattr(value, "name"):
            name = value.name
            if isinstance(name, str):
                name = name.decode(OS_FILESYSTEM_ENCODING)
            header += '; filename="%s"' % os.path.split(name.encode("utf-8"))[-1]
            lines.append(header)
            mtypes = mimetypes.guess_type(value.name)
            if mtypes:
                contentType = mtypes[0]
                header = "Content-Type: %s" % contentType
                lines.append(header)
            lines.append("Content-Transfer-Encoding: binary")
        else:
            lines.append(header)

        lines.append("")
        if hasattr(value, "read"):
            lines.append(value.read())
        elif isinstance(value, unicode):
            lines.append(value.encode("utf-8"))
        else:
            lines.append(str(value))
        lines.append("--" + boundary)
    lines[-1] += "--"

    return "\r\n".join(lines), boundary
