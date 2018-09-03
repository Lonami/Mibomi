import generator.parser
import generator.generator
import generator.pygen


CLIENT_MBM = 'generator/clientbound.mbm'
SERVER_TYPES = 'mibomi/datatypes/types.py'

SERVER_MBM = 'generator/serverbound.mbm'
CLIENT_METHODS = 'mibomi/network/requester.py'


class RepetitionChecker:
    def __init__(self):
        self.cls = set()
        self.names = set()

    def check(self, definition):
        if definition.cls in self.cls:
            raise ValueError('Class %s already exists' % definition.cls)
        self.cls.add(definition.cls)
        if definition.name in self.names:
            raise ValueError('Name %s already exists' % definition.name)
        self.names.add(definition.name)

    def clear(self):
        self.cls.clear()
        self.names.clear()


if __name__ == '__main__':
    rep = RepetitionChecker()
    with open(CLIENT_MBM) as fin,\
            generator.pygen.PyGen(open(SERVER_TYPES, 'w')) as gen:
        gen.writeln('import io')
        gen.writeln('import pprint')
        gen.writeln('TYPES = {}')
        with gen.block('class ServerType:'):
            with gen.meth('__repr__'):
                gen.writeln('x = io.StringIO()')
                gen.writeln('pprint.pprint(self.__dict__, stream=x)')
                gen.writeln('return x.getvalue().rstrip()')

        for definition in generator.parser.parse_str(fin.read()):
            rep.check(definition)
            generator.generator.generate_class(gen, definition)

    rep.clear()
    with open(SERVER_MBM) as fin, \
            generator.pygen.PyGen(open(CLIENT_METHODS, 'w')) as gen:
        gen.writeln('from . import connection')
        gen.writeln('from ..datatypes import DataRW')
        gen.writeln('import typing')
        gen.writeln('from uuid import UUID')
        gen.writeln('from ..datatypes import Position, Slot, DataRW')

        with gen.block('class Requester(connection.Connection):'):
            for definition in generator.parser.parse_str(fin.read()):
                rep.check(definition)
                generator.generator.generate_method(gen, definition)
