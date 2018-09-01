import generator.parser
import generator.generator
import generator.pygen


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
    with open('generator/clientbound.mbm') as fin,\
            generator.pygen.PyGen(open('mibomi/types.py', 'w')) as gen:
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
    with open('generator/serverbound.mbm') as fin, \
            generator.pygen.PyGen(open('mibomi/requester.py', 'w')) as gen:
        gen.writeln('from . import connection, datarw')
        with gen.block('class Requester(connection.Connection):'):
            for definition in generator.parser.parse_str(fin.read()):
                rep.check(definition)
                generator.generator.generate_method(gen, definition)
