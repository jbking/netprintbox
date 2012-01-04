#!/usr/bin/env python
import os
import pprint
import re
import sys
import zipfile


def collect_library_files(library, exclude=None):
    collect = []
    root_path = library.__file__
    if os.path.basename(root_path).startswith('__init__'):
        # package
        root_path = os.path.dirname(root_path)
        for cwd, _, entries in os.walk(root_path):
            for entry in entries:
                # because a package can have any type resources.
                entry_path = os.path.join(cwd, entry)
                if entry_path.endswith('.pyc'):
                    entry_path = entry_path[:-4] + '.py'
                collect.append(entry_path)
    else:
        # module
        collect.append(root_path.replace('.pyc', '.py'))

    if exclude:
        collect = [path for path in collect
                   if exclude.match(path) is None]
    return collect


def fix_init_py(library):
    collect = []
    path = os.path.dirname(library.__file__)
    while True:
        collect.append(os.path.join(path, '__init__.py'))
        path = os.path.dirname(path)
        if path.endswith('site-packages'):
            break
    return collect


def archive(collected_path_list):
    SITE_PACKAGES = '/site-packages/'
    with zipfile.ZipFile('bundle.zip', 'w') as zip:
        for path in collected_path_list:
            arcname = path[path.index(SITE_PACKAGES) + len(SITE_PACKAGES):]
            try:
                zip.write(path, arcname)
            except OSError:
                zip.writestr(arcname, '')


def main():
    collect = []
    for library_name, exclude_pattern in (
            # netprint
            ('BeautifulSoup', None),
            ('httplib2', None),

            # dropbox
            ('dropbox', None),
            ('simplejson', '(.*/tests/.*|.*\.so)$'),
            ('oauth', None),

            # pyramid
            ('pyramid', '.*/(tests|scaffolds|scripts)/.*'),
            ('pkg_resources', None),
            ('webob', None),
            ('mako', None),
            ('markupsafe', '.*(tests\.py|.*\.c|.*\.so)$'),
            ('repoze.lru', '.*(tests)\.py'),
            ('venusian', '.*/(tests)/.*'),
            ('translationstring', '.*/(tests)/.*'),
            ('zope.interface', '(.*/tests/.*|.*\.c|.*\.so|.*\.txt)$'),
            ('zope.deprecation', '.*(fixture|tests)\.py'),

            # netprintbox
            ('tempita', None),
            ):
        if exclude_pattern:
            exclude = re.compile(exclude_pattern)
        else:
            exclude = None
        __import__(library_name)
        library = sys.modules[library_name]
        collect.extend(collect_library_files(library, exclude))
        if library_name.find('.') > 0:
            collect.extend(fix_init_py(library))
    archive(sorted(set(collect)))


if __name__ == '__main__':
    main()
