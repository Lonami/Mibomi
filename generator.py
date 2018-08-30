import generator.parser
import generator.generator


if __name__ == '__main__':
    with open('generator/clientbound.mbm') as fin,\
            open('mibomi/types.py', 'w') as fout:
        fout.write('''
import io
import pprint
TYPES={}
class ServerType:
 def __str__(self):
  x = io.StringIO()
  pprint.pprint(self.__dict__, stream=x)
  return x.getvalue()
'''.lstrip())
        for definition in generator.parser.parse_str(fin.read()):
            generator.generator.generate_class(fout, definition)

    with open('generator/serverbound.mbm') as fin,\
            open('mibomi/requester.py', 'w') as fout:
        fout.write('from . import connection, datarw\n')
        fout.write('class Requester(connection.Connection):\n')
        for definition in generator.parser.parse_str(fin.read()):
            generator.generator.generate_method(fout, definition, indent=' ')
