import generator.parser
import generator.generator
import generator.pygen


if __name__ == '__main__':
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
            generator.generator.generate_class(gen, definition)

    with open('generator/serverbound.mbm') as fin, \
            generator.pygen.PyGen(open('mibomi/requester.py', 'w')) as gen:
        gen.writeln('from . import connection, datarw')
        with gen.block('class Requester(connection.Connection):'):
            for definition in generator.parser.parse_str(fin.read()):
                generator.generator.generate_method(gen, definition)
