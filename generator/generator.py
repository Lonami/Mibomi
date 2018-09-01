from . import parser


_BUILTIN_CLS = {
    'vari32', 'vari64', 'uuid', 'str', 'bytes', 'pos',
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

    args = []
    for arg in definition.args:
        if not isinstance(arg, parser.ArgDefinition):
            break
        else:
            args.append(arg.name)
            if arg.optional or arg.referenced:
                args[-1] += '=None'

    with gen.ameth(definition.name, *args):
        gen.writeln('_ = datarw.DataRW()')
        _generate_write_method(gen, definition)
        gen.writeln('await self.send(0x{:x}, _.getvalue())', definition.id)


def _generate_read_method(gen, definition):
    if definition.has_optional:
        for arg in definition.args:
            if not isinstance(arg, parser.ArgDefinition):
                break
            if arg.optional or arg.referenced:
                gen.write('self.{} = ', arg.name)
        gen.writeln('None')

    condition = gen.empty().__enter__()
    for group in _collapse_args(definition.args):
        if isinstance(group, parser.ConditionDisable):
            condition.__exit__()
            condition = gen.empty().__enter__()
        elif isinstance(group, parser.Condition):
            condition.__exit__()
            gen.write('if ')
            if group.name not in definition.params:
                gen.write('self.')

            condition = gen.block(
                '{} {} {}:', group.name, group.op, group.value).__enter__()
        elif isinstance(group, list):
            fmt = ''
            for arg in group:
                fmt += arg.builtin_fmt
                gen.write('self.{}, ', arg.name)
            gen.writeln('= data.readfmt({!r})', fmt)
        else:
            group: parser.ArgDefinition = group
            optional = gen.empty().__enter__()
            if group.optional:
                optional = gen.block("if data.readfmt('?')[0]:").__enter__()

            gen.write('self.{} = ', group.name)

            if group.vec_count_cls:
                # Special case vectors of u8 as byte strings
                if group.cls == 'u8':
                    gen.write('data.read(')
                    _generate_read1(gen, group.vec_count_cls)
                    gen.writeln(')')
                    optional.__exit__()
                    continue
                else:
                    gen.write('[')

            _generate_read1(gen, group.cls, group.args)

            if group.vec_count_cls:
                gen.write(' for _ in range(')
                _generate_read1(gen, group.vec_count_cls)
                gen.write(')]')

            gen.writeln()
            optional.__exit__()
    condition.__exit__()


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
    condition = gen.empty().__enter__()
    for group in _collapse_args(definition.args):
        if isinstance(group, parser.ConditionDisable):
            condition.__exit__()
            condition = gen.empty().__enter__()
        elif isinstance(group, parser.Condition):
            condition.__exit__()
            gen.write('if ')
            condition = gen.block(
                '{} {} {}:', group.name, group.op, group.value).__enter__()
        elif isinstance(group, list):
            gen.writeln('_.writefmt({!r}, {})',
                        ''.join(x.builtin_fmt for x in group),
                        ','.join(x.name for x in group))
        else:
            group: parser.ArgDefinition = group
            name = group.name
            optional = gen.empty().__enter__()
            if group.optional:
                with gen.block('if {} is None:', name):
                    gen.writeln("_.writefmt('?', False)")
                optional = gen.block('else:').__enter__()
                gen.writeln("_.writefmt('?', True)")

            vector = gen.empty().__enter__()
            if group.vec_count_cls:
                if group.vec_count_cls not in _BUILTIN_CLS:
                    raise NotImplementedError

                gen.writeln('_.write{}(len({}))', group.vec_count_cls, name)
                vector = gen.block('for _x in {}:', group.name).__enter__()
                name = '_x'

            if group.builtin_fmt:
                gen.writeln('_.writefmt({!r}, {})', group.builtin_fmt, name)
            elif group.cls in _BUILTIN_CLS:
                gen.writeln('_.write{}({})', group.cls, name)
            else:
                raise NotImplementedError

            vector.__exit__()
            optional.__exit__()
    condition.__exit__()


def _collapse_args(args):
    # Try collapsing bare types into a single fmt call.
    # The builtin struct module is really good when it
    # comes down to working with more than one value at once.
    collapsed = []
    for arg in args:
        # Referenced arguments should be used from their references
        if isinstance(arg, parser.ArgDefinition) and arg.referenced:
            continue

        # Treat references as normal arguments since they have a cls
        if isinstance(arg, parser.ArgReference):
            arg = arg.ref

        # As long as it's an argument definition with builtin_fmt
        # and not optional or inside a vector it can be collapsed
        if (isinstance(arg, parser.ArgDefinition)
            and arg.builtin_fmt
            and not arg.optional
                and not arg.vec_count_cls):
            collapsed.append(arg)
        else:
            if collapsed:
                yield collapsed
                collapsed = []
            yield arg

    if collapsed:
        yield collapsed
