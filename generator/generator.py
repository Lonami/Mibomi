from . import parser


_BUILTIN_CLS = {
    'vari32', 'vari64', 'uuid', 'str', 'bytes', 'angle', 'pos',
    'entmeta', 'nbt'
}


def generate_class(f, definition, indent=''):
    f.write(indent)
    f.write('class ')
    f.write(definition.cls)
    f.write('(ServerType):\n')

    if definition.id is not None:
        f.write(indent)
        f.write(' ID=')
        f.write(hex(definition.id))
        f.write('\n')

    f.write(indent)
    f.write(' NAME=')
    f.write(repr(definition.name))
    f.write('\n')

    f.write(indent)
    f.write(' def __init__(self,data')
    for param in definition.params:
        f.write(',')
        f.write(param)
    f.write('):\n')

    f.write(indent)
    if not definition.args:
        f.write('  pass\n')
    else:
        _generate_read_method(
            f, indent + '  ', definition.args, definition.params)

    if definition.id is not None:
        f.write(indent)
        f.write('TYPES[')
        f.write(hex(definition.id))
        f.write(']=')
        f.write(definition.cls)
        f.write('\n')


def generate_method(f, definition, indent=''):
    if definition.params:
        raise NotImplementedError

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


def _generate_read_method(f, indent, args, params):
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
            f.write(')')
        else:
            if group.depends:
                f.write('if ')
                if group.depends.name not in params:
                    f.write('self.')
                f.write(group.depends.name)
                f.write(' ')
                f.write(group.depends.op)
                f.write(' ')
                f.write(group.depends.value)
                f.write(':\n')
                indent += ' '
                f.write(indent)

            f.write('self.')
            f.write(group.name)
            f.write('=')

            if group.vec_count_cls:
                # Special case vectors of u8 as byte strings
                if group.cls == 'u8':
                    f.write('data.read(')
                    _generate_read1(f, group.vec_count_cls)
                    f.write(')\n')
                    # TODO This is getting messy
                    if group.depends:
                        indent = indent[:-1]
                    continue

                f.write('[')

            _generate_read1(f, group.cls, group.args)

            if group.vec_count_cls:
                f.write(' for _ in range(')
                _generate_read1(f, group.vec_count_cls)
                f.write(')]')

            if group.depends:
                indent = indent[:-1]

        f.write('\n')


def _generate_read1(f, cls, args=()):
    if cls in parser.TYPE_TO_FMT:
        f.write('data.readfmt(')
        f.write(repr(parser.TYPE_TO_FMT[cls]))
        f.write(')[0]')
    elif cls in _BUILTIN_CLS:
        f.write('data.read')
        f.write(cls)
        f.write('()')
    else:
        f.write(cls)
        f.write('(data')
        for arg in args:
            f.write(',self.')
            f.write(arg)
        f.write(')')

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
            if group.depends:
                f.write('if ')
                f.write(group.depends.name)
                f.write(' ')
                f.write(group.depends.op)
                f.write(' ')
                f.write(group.depends.value)
                f.write(':\n')
                indent += ' '
                f.write(indent)

            name = group.name
            if group.vec_count_cls:
                if group.vec_count_cls not in _BUILTIN_CLS:
                    raise NotImplementedError

                f.write('_.write')
                f.write(group.vec_count_cls)
                f.write('(len(')
                f.write(group.name)
                f.write('))\n')

                f.write(indent)
                f.write('for _x in ')
                f.write(group.name)
                f.write(':\n')
                indent += ' '
                f.write(indent)
                name = '_x'

            if group.builtin_fmt:
                raise NotImplementedError
            elif group.cls in _BUILTIN_CLS:
                f.write('_.write')
                f.write(group.cls)
                f.write('(')
                f.write(name)
                f.write(')\n')
            else:
                raise NotImplementedError

            if group.vec_count_cls:
                indent = indent[:-1]

            if group.depends:
                indent = indent[:-1]

def _collapse_args(args):
    # Try collapsing bare types into a single fmt call.
    # The builtin struct module is really good when it
    # comes down to working with more than one value at once.
    collapsed = []
    for arg in args:
        if arg.builtin_fmt and not (arg.vec_count_cls or arg.depends):
            collapsed.append(arg)
        else:
            if collapsed:
                yield collapsed
                collapsed = []
            yield arg

    if collapsed:
        yield collapsed
