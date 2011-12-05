# -*- encoding: utf8 -*-
import os

import tempita
import settings


def load_template(path):
    return tempita.HTMLTemplate(
            open(os.path.join(settings.TEMPLATE_PATH, path)).read())


def normalize_name(path):
    return os.path.basename(path).split(os.path.extsep)[0]


def is_generated_file(path):
    return path in (settings.ACCOUNT_INFO_PATH, settings.REPORT_PATH)
