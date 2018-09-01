import re
import sys


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


class Definition:
    def __init__(self, name, id, args, cls, params):
        self.name = name
        self.id = id
        self.args = args
        self.cls = cls
        self.params = params
        self.validate_args()

    def validate_args(self):
        known_args = set()
        found_conditional = False
        for arg in self.args:
            if found_conditional:
                if isinstance(arg, ArgDefinition):
                    raise ValueError('Arg definition after conditional '
                                     '{} in {}'.format(arg, self))
                elif isinstance(arg, ArgReference):
                    if arg.name not in known_args:
                        raise ValueError('Reference to undefined arg '
                                         '{} in {}'.format(arg, self))
            else:
                if isinstance(arg, (Condition, ConditionDisable)):
                    found_conditional = True
                elif isinstance(arg, ArgDefinition):
                    known_args.add(arg.name)
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
    def __init__(self, name, cls, vec_count_cls, optional, args):
        self.name = name
        self.cls = cls
        self.vec_count_cls = vec_count_cls
        self.optional = optional
        self.builtin_fmt = TYPE_TO_FMT.get(self.cls)
        self.args = args  # arguments when calling self.cls()

    def __str__(self):
        result = '{}:{}'.format(self.name, self.cls)
        if self.vec_count_cls:
            result = '{}+{}'.format(self.vec_count_cls, result)

        if self.optional:
            result += '?'

        return result


class Condition:
    def __init__(self, name, op, value):
        self.name = name
        self.op = op
        self.value = value

    def __str__(self):
        return '?{}?{}?{}'.format(self.name, self.op, self.value)

class ConditionDisable:
    def __str__(self):
        return '?'

class ArgReference:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


def _parse_arg(string):
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
    string = re.sub(r'//[^\n]*', '', string)
    defs = [x.strip() for x in string.split(';') if x and not x.isspace()]
    for definition in defs:
        if definition.count('->') != 1:
            print('Wrong amount of ->:', file=sys.stderr)
            print(definition, file=sys.stderr)
            continue

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
