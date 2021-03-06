import re


# MBM types that can be directly translated to struct fmt types
TYPE_TO_FMT = {
    'i8': 'b',
    'u8': 'B',
    'i16': 'h',
    'u16': 'H',
    'i32': 'i',
    'u32': 'I',
    'i64': 'q',
    'u64': 'Q',
    'bool': '?',
    'float': 'f',
    'double': 'd'
}

INTEGERS = {
    'i8', 'u8', 'i16', 'u16', 'i32', 'u32', 'i64', 'u64', 'vari32', 'vari64'
}


class Definition:
    """
    The entire definition for a line in a MBM file.
    """
    def __init__(self, name, id, args, cls, params):
        self.name = name
        self.id = id
        self.args = tuple(args)
        self.cls = cls
        self.params = tuple(params)
        self.has_optional = False
        self.validate_args()

    def validate_args(self):
        known_args = {}
        self.has_optional = False
        found_conditional = False
        for arg in self.args:
            if found_conditional:
                if isinstance(arg, ArgDefinition):
                    raise ValueError('Arg definition after conditional '
                                     '{} in {}'.format(arg, self))
                elif isinstance(arg, ArgReference):
                    if arg.name in known_args:
                        arg.ref = known_args[arg.name]
                        arg.ref.referenced = True
                    else:
                        raise ValueError('Reference to undefined arg '
                                         '{} in {}'.format(arg, self))
            else:
                if isinstance(arg, (Condition, ConditionDisable)):
                    self.has_optional = True
                    found_conditional = True
                elif isinstance(arg, ArgDefinition):
                    if arg.name not in known_args:
                        known_args[arg.name] = arg
                    else:
                        raise ValueError(
                            'Redefined argument {} with {} in {}'
                            .format(known_args[arg.name], arg, self)
                        )

                    arg.referenced = False
                    if arg.optional:
                        self.has_optional = True
                else:
                    raise ValueError('Non-argument definition before '
                                     'conditional {} in {}'.format(arg, self))

    def __str__(self):
        result = self.name
        if self.id is not None:
            result += '#{:x}'.format(self.id)
        result += '\n  {} -> {}'.format(
            '\n  '.join(map(str, self.args)), self.cls)

        return result


class ArgDefinition:
    """
    The definition for a single argument.
    """
    def __init__(self, name, cls, vec_count_cls, optional, args):
        self.name = name
        self.cls = cls
        self.vec_count_cls = vec_count_cls
        self.optional = optional
        self.builtin_fmt = TYPE_TO_FMT.get(self.cls)
        self.args = tuple(args)  # arguments when calling self.cls()
        self.referenced = False

    def __str__(self):
        result = '{}:{}'.format(self.name, self.cls)
        if self.vec_count_cls:
            result = '{}+{}'.format(self.vec_count_cls, result)

        if self.optional:
            result += '?'

        return result

    def typing(self):
        result = self.cls
        if result in INTEGERS:
            result = 'int'
        elif result == 'double':
            result = 'float'
        elif result == 'uuid':
            result = 'UUID'
        elif result == 'pos':
            result = 'Position'
        elif result == 'slot':
            result = 'Slot'
        elif result == 'nbt':
            result = 'BaseTag'
        elif result == 'entmeta':
            result = 'typing.List[tuple]'

        if self.vec_count_cls:
            result = 'typing.List[{}]'.format(result)

        if self.optional:
            result = 'typing.Optional[{}]'.format(result)

        return result


class Condition:
    """
    A non-empty condition present in a definition's list of arguments.
    """
    def __init__(self, name, op, value):
        self.name = name
        self.op = op
        self.value = value

    def __str__(self):
        return '?{}?{}?{}'.format(self.name, self.op, self.value)


class ConditionDisable:
    """
    An empty condition present in a definition's list of arguments.
    """
    def __str__(self):
        return '?'


class ArgReference:
    """
    A reference to a previously defined argument.
    """
    def __init__(self, name):
        self.name = name
        self.ref = None

    def __str__(self):
        return self.name


def _parse_arg(string):
    """
    Parses the argument present in the current string.
    """
    if string.startswith('?'):
        if string == '?':
            return ConditionDisable()
        return Condition(*string.split('?')[1:])

    if ':' not in string:
        return ArgReference(string)

    name, cls = string.split(':')
    if '+' in cls:
        vec_count_cls, cls = cls.split('+')
    else:
        vec_count_cls = None

    if cls.endswith('?'):
        optional = True
        cls = cls[:-1]
    else:
        optional = False

    if '@' in cls:
        cls, *args = cls.split('@')
    else:
        args = ()

    return ArgDefinition(name, cls, vec_count_cls, optional, args)


def parse_str(string: str):
    """
    Parses an entire string containing zero or more MBM definitions,
    and yields the built objects. Invalid definitions will raise.
    """
    string = re.sub(r'//[^\n]*', '', string)
    defs = [x.strip() for x in string.split(';') if x and not x.isspace()]
    for definition in defs:
        if definition.count('->') != 1:
            raise ValueError('Wrong amount of -> for {}'.format(definition))

        left, cls = definition.split('->')
        left, *args = left.split()
        if '?' in left:
            left, *params = left.split('?')
        else:
            params = ()

        if '#' in left:
            name, id = left.split('#')
            id = int(id, 16)
        else:
            name, id = left, None

        yield Definition(
            name.strip(), id, list(map(_parse_arg, args)), cls.strip(), params)
