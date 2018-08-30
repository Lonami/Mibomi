_BUILTIN_CLS = {
    'vari32', 'vari64', 'uuid', 'str', 'bytes', 'angle', 'pos', 'left'
}


def generate_class(f, definition, indent=''):
    f.write(indent)
    f.write('class ')
    f.write(definition.cls)
    f.write(':\n')

    if definition.id:
        f.write(indent)
        f.write(' ID=')
        f.write(hex(definition.id))
        f.write('\n')

    f.write(indent)
    f.write(' NAME=')
    f.write(repr(definition.name))
    f.write('\n')

    f.write(indent)
    f.write(' def __init__(self,data):\n')

    f.write(indent)
    if not definition.args:
        f.write('  pass\n')
    else:
        _generate_read_method(f, indent + '  ', definition.args)

    if definition.id:
        f.write(indent)
        f.write('TYPES[')
        f.write(hex(definition.id))
        f.write(']=')
        f.write(definition.cls)
        f.write('\n')


def generate_method(f, definition, indent=''):
    f.write(indent)
    f.write('async def ')
    f.write(definition.name)
    f.write('(self')
    for arg in definition.args:
        f.write(',')
        f.write(arg.name)
    f.write('):\n')

    f.write(indent)
    f.write(' _=datarw.DataRW()\n')
    _generate_write_method(f, indent + ' ', definition.args)

    f.write(indent)
    f.write(' await self.send(')
    f.write(hex(definition.id))
    f.write(',')
    f.write('_.getvalue())\n')


def _generate_read_method(f, indent, args):
    for group in _collapse_args(args):
        f.write(indent)
        if isinstance(group, list):
            fmt = ''
            for arg in group:
                fmt += arg.builtin_fmt
                f.write('self.')
                f.write(arg.name)
                f.write(',')
            f.write('=data.readfmt(')
            f.write(repr(fmt))
            f.write(')\n')
        else:
            f.write('self.')
            f.write(group.name)
            f.write('=')
            if group.cls in _BUILTIN_CLS:
                f.write('data.read')
                f.write(group.cls)
                f.write('()\n')
            else:
                f.write(group.cls)
                f.write('(data)\n')


def _generate_write_method(f, indent, args):
    for group in _collapse_args(args):
        f.write(indent)
        if isinstance(group, list):
            f.write('_.writefmt(')
            f.write(repr(''.join(x.builtin_fmt for x in group)))
            f.write(',')
            f.write(','.join(x.name for x in  group))
            f.write(')\n')
        else:
            if group.cls in _BUILTIN_CLS:
                f.write('_.write')
                f.write(group.cls)
                f.write('(')
                f.write(group.name)
                f.write(')\n')
            else:
                raise NotImplementedError

def _collapse_args(args):
    # Try collapsing bare types into a single fmt call.
    # The builtin struct module is really good when it
    # comes down to working with more than one value at once.
    collapsed = []
    for arg in args:
        if arg.builtin_fmt:
            collapsed.append(arg)
        else:
            if collapsed:
                yield collapsed
                collapsed = []
            yield arg

    if collapsed:
        yield collapsed
