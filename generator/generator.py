from . import parser


_BUILTIN_CLS = {
    'vari32', 'vari64', 'uuid', 'str', 'bytes', 'angle', 'pos',
    'entmeta', 'nbt', 'slot'
}


def generate_class(gen, definition):
    with gen.block('class {}(ServerType):', definition.cls):
        if definition.id is not None:
            gen.writeln('ID = 0x{:x}', definition.id)

        gen.writeln('NAME = {!r}', definition.name)
        with gen.meth('__init__', 'data', *definition.params):
            if not definition.args:
                gen.writeln('pass')
            else:
                _generate_read_method(gen, definition)

    if definition.id is not None:
        gen.writeln('TYPES[0x{:x}] = {}', definition.id, definition.cls)


def generate_method(gen, definition):
    if definition.params:
        raise NotImplementedError

    with gen.ameth(definition.name, *(x.name for x in definition.args)):
        gen.writeln('_ = datarw.DataRW()')
        _generate_write_method(gen, definition)
        gen.writeln('await self.send(0x{:x}, _.getvalue())', definition.id)


def _generate_read_method(gen, definition):
    for group in _collapse_args(definition.args):
        if isinstance(group, list):
            fmt = ''
            for arg in group:
                fmt += arg.builtin_fmt
                gen.write('self.{}, ', arg.name)
            gen.write('= data.readfmt({!r})', fmt)
        else:
            dep_block = gen.empty()
            if group.depends:
                gen.write('if ')
                dep = group.depends
                if dep.name not in definition.params:
                    gen.write('self.')

                dep_block = gen.block('{} {} {}:', dep.name, dep.op, dep.value)
                dep_block.__enter__()

            gen.write('self.{} = ', group.name)

            if group.vec_count_cls:
                # Special case vectors of u8 as byte strings
                if group.cls == 'u8':
                    gen.write('data.read(')
                    _generate_read1(gen, group.vec_count_cls)
                    gen.writeln(')')
                    dep_block.__exit__()
                    return
                else:
                    gen.write('[')

            _generate_read1(gen, group.cls, group.args)

            if group.vec_count_cls:
                gen.write(' for _ in range(')
                _generate_read1(gen, group.vec_count_cls)
                gen.write(')]')

            dep_block.__exit__()

        gen.writeln()


def _generate_read1(gen, cls, args=()):
    if cls in parser.TYPE_TO_FMT:
        gen.write('data.readfmt({!r})[0]', parser.TYPE_TO_FMT[cls])
    elif cls in _BUILTIN_CLS:
        gen.write('data.read{}()', cls)
    else:
        gen.write('{}(data', cls)
        for arg in args:
            gen.write(', self.{}', arg)
        gen.write(')')

def _generate_write_method(gen, definition):
    for group in _collapse_args(definition.args):
        if isinstance(group, list):
            gen.writeln('_.writefmt({!r}, {})',
                        ''.join(x.builtin_fmt for x in group),
                        ','.join(x.name for x in group))
        else:
            dep_block = gen.empty()
            if group.depends:
                gen.write('if ')
                dep = group.depends
                dep_block = gen.block('{} {} {}:', dep.name, dep.op, dep.value)
                dep_block.__enter__()

            name = group.name
            vec_block = gen.empty()
            if group.vec_count_cls:
                if group.vec_count_cls not in _BUILTIN_CLS:
                    raise NotImplementedError

                gen.writeln(
                    '_.write{}(len({}))', group.vec_count_cls, group.name)

                name = '_x'
                vec_block = gen.block('for _x in {}:', group.name)
                vec_block.__enter__()

            if group.builtin_fmt:
                gen.writeln('_.writefmt({!r}, {})', group.builtin_fmt, name)
            elif group.cls in _BUILTIN_CLS:
                gen.writeln('_.write{}({})', group.cls, name)
            else:
                raise NotImplementedError

            vec_block.__exit__()
            dep_block.__exit__()

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
