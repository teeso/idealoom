from os.path import dirname, join, exists, abspath
from subprocess import check_output
import pkg_resources

from semantic_version import Version

__version__ = "0.1.0"

_cached_version = None


def to_semver(version):
    # convert PEP440 version to https://semver.org/ 2.0
    if '.dev' in version:
        version = '-dev.'.join(version.split('.dev'))
    return Version(version)


def version():
    # return a PEP440 version string
    global _cached_version
    if _cached_version is None:
        code_base = abspath(dirname(dirname(__file__)))
        if exists(join(code_base, '.git')):
            tag = check_output('cd %s && git describe --tags --always' % code_base, shell=True).decode('ascii')
            parts = tag.strip().lstrip('v').rsplit('-', 2)
            assert parts[0] == __version__
            if len(parts) == 1:
                # We're on the tag
                _cached_version = parts[0]
            else:
                base = Version(parts[0]).next_patch()
                _cached_version = '%s.dev%s+%s' % (base, parts[1], parts[2][1:])
        else:
            # from wheel
            _cached_version = pkg_resources.get_distribution("idealoom").version
            assert str(_cached_version) == __version__
    return _cached_version


def sem_version():
    return to_semver(version())


if __name__ == '__main__':
    print(version())
