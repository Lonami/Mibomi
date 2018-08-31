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

    def __str__(self):
        return '{}#{:x}\n  {} -> {}'.format(
            self.name, self.id, '\n  '.join(map(str, self.args)), self.cls)

class ArgDefinition:
    def __init__(self, name, cls, vec_count_cls, depends, args):
        self.name = name
        self.cls = cls
        self.vec_count_cls = vec_count_cls
        self.depends = depends
        self.builtin_fmt = TYPE_TO_FMT.get(self.cls)
        self.args = args  # arguments when calling self.cls()

    def __str__(self):
        result = '{}:{}'.format(self.name, self.cls)
        if self.vec_count_cls:
            result = '{}+{}'.format(self.vec_count_cls, result)

        if self.depends:
            result = '{}?{}'.format(result, self.depends)

        return result

class Dependency:
    def __init__(self, name, op, value):
        self.name = name
        self.op = op
        self.value = value

    def __str__(self):
        return '{}?{}?{}'.format(self.name, self.op, self.value)


def _parse_arg(string):
    name, cls = string.split(':')
    if '+' in cls:
        vec_count_cls, cls = cls.split('+')
    else:
        vec_count_cls = None

    if '@' in cls:
        cls, *args = cls.split('@')
    else:
        args = ()

    if '?' in cls:
        cls, depend_name, depend_op, depend_value = cls.split('?')
        depends = Dependency(depend_name, depend_op, depend_value)
    else:
        depends = None

    return ArgDefinition(name, cls, vec_count_cls, depends, args)


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
