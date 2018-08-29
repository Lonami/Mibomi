import re
import sys


_TYPE_TO_FMT = {
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
    def __init__(self, name, id, args, cls):
        self.name = name
        self.id = id
        self.args = args
        self.cls = cls

    def __str__(self):
        return '{}#{:x}\n  {} -> {}'.format(
            self.name, self.id, '\n  '.join(map(str, self.args)), self.cls)

class ArgDefinition:
    def __init__(self, name, cls):
        self.name = name
        self.cls = cls
        self.builtin_fmt = _TYPE_TO_FMT.get(self.cls)

    def __str__(self):
        return '{}:{}'.format(self.name, self.cls)

def _parse_arg(string):
    return ArgDefinition(*string.split(':'))

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
        if '#' in left:
            name, id = left.split('#')
            id = int(id, 16)
        else:
            name, id = left, None

        yield Definition(
            name.strip(), id, [_parse_arg(x) for x in args], cls.strip())
