from os.path import expanduser, exists
from os import getenv, fsync, unlink
from errno import ENOENT
from shutil import move

stripchars = '"\' '

_pvpath_default = getenv('PVDATA_PATH')
if not _pvpath_default:
    _pvpath_default = expanduser('~/.pvdata')

_pvpath = None
_pvdict = None
_pvdata_counter = 0
_pvdirty = 0

def _pvopen(pvpath=_pvpath_default):
    global _pvdict
    if _pvdict is not None:
        return _pvdict

    try:
        with open(pvpath) as f:
            pvdata = f.read()
    except IOError, e:
        if e.errno != ENOENT:
            m = "Cannot open pvdata file '%s'" % (pvpath,)
            raise ValueError(m, e)

        with open(pvpath, "w") as f:
            pass
        pvdata = ''

    global _pvpath
    _pvpath = pvpath

    pvdict = {}
    for line in pvdata.splitlines():
        key, sep, val = line.partition('=')
        if not key or key[0] == '#':
            continue

        key = key.strip()
        val = val.strip()

        if len(key) > 1 and key[0] == "'" and key[-1] == "'":
            key = key[1:-1]

        if len(val) > 1 and val[0] == "'" and val[-1] == "'":
            val = val[1:-1]

        pvdict[key] = val

    _pvdict = pvdict
    return pvdict


def pvsave(pvpath=None, force=0):

    if _pvdict is None or not (force or _pvdirty):
        return

    if pvpath is None:
        pvpath = _pvpath

    pvdata_list = []
    append = pvdata_list.append

    for key, val in _pvdict.items():
        if not key or '\n' in key or '\n' in val:
            continue

        if key[0] == ' ' or key[-1] == ' ':
            key = "'%s'" % (key,)

        if val[0] == ' ' or val[-1] == ' ':
            val = "'%s'" % (val,)

        append("%s = %s" % (key, val))

    pvdata = '\n'.join(pvdata_list) + '\n'

    global _pvdata_counter

    while 1:
        pvpath_old = '%s.old.%d' % (pvpath, _pvdata_counter)
        if not exists(pvpath_old):
            break

        _pvdata_counter += 1
        continue

    move(pvpath, pvpath_old)

    try:
        with open(pvpath, "w") as f:
            f.write(pvdata)
            f.flush()
            fsync(f.fileno())
    except IOError, e:
        m = "Cannot open pvdata file '%s'" % (pvpath,)
        raise ValueError(m, e)

    unlink(pvpath_old)


def getpv(key):
    pvdict = _pvopen()
    return pvdict[key] if key in pvdict else ''

def setpv(key, val):
    pvdict = _pvopen()
    global _pvdirty
    _pvdirty = 1
    pvdict[key] = val

def delpv(key):
    pvdict = _pvopen()
    del pvdict[key]

def savepv(key, val):
    setpv(key, val)
    pvsave()

