import base64
import gzip
import unittest
from mibomi.datatypes import nbt
from mibomi.datatypes.nbt import (
    TagByte,
    TagShort,
    TagInt,
    TagLong,
    TagFloat,
    TagDouble,
    TagByteArray,
    TagString,
    TagList,
    TagCompound
)


class TestNBT(unittest.TestCase):
    def test_short(self):
        target = TagShort('shortTest', 32767)
        data = bytearray.fromhex('''
        02
        00 09
        73 68 6F 72 74 54 65 73 74
        7F FF
        ''')
        got = nbt.read(data)
        self.assertEqual(got, target)
        self.assertEqual(nbt.write(got), data)

    def test_normal(self):
        target = TagCompound('hello world', [TagString('name', 'Bananrama')])
        data = bytearray.fromhex('''
        0a
        00 0b
        68 65 6c 6c 6f 20 77 6f 72 6c 64
        08
        00 04
        6e 61 6d 65
        00 09
        42 61 6e 61 6e 72 61 6d 61
        00
        ''')
        got = nbt.read(data)
        self.assertEqual(got, target)
        self.assertEqual(nbt.write(got), data)

    def test_big(self):
        def f(n):
            return (n * n * 255 + n * 7) % 100

        target = TagCompound('Level', [
            TagLong('longTest', 9223372036854775807),
            TagShort('shortTest', 32767),
            TagString('stringTest', 'HELLO WORLD THIS IS A TEST STRING ÅÄÖ!'),
            TagFloat('floatTest', 0.4982314705848694),
            TagInt('intTest', 2147483647),
            TagCompound('nested compound test', [
                TagCompound('ham', [
                    TagString('name', 'Hampus'),
                    TagFloat('value', 0.75)
                ]),
                TagCompound('egg', [
                    TagString('name', 'Eggbert'),
                    TagFloat('value', 0.5)
                ])
            ]),
            TagList('listTest (long)', [
                TagLong(None, 11),
                TagLong(None, 12),
                TagLong(None, 13),
                TagLong(None, 14),
                TagLong(None, 15)
            ]),
            TagList('listTest (compound)', [
                TagCompound(None, [
                    TagString('name', 'Compound tag #0'),
                    TagLong('created-on', 1264099775885)
                ]),
                TagCompound(None, [
                    TagString('name', 'Compound tag #1'),
                    TagLong('created-on', 1264099775885)
                ])
            ]),
            TagByte('byteTest', 127),
            TagByteArray('byteArrayTest (the first 1000 values of '
                         '(n*n*255+n*7)%100, starting with n=0 (0, '
                         '62, 34, 16, 8, ...))', bytes(map(f, range(1000)))),
            TagDouble('doubleTest', 0.4931287132182315)
        ])
        data = gzip.decompress(base64.b64decode('''
H4sIAAAAAAAAAO1Uz08aQRR+wgLLloKxxBBjzKu1hKXbzUIRibGIFiyaDRrYqDGGuCvDgi67Znew
8dRLe2x66z/TI39Dz732v6DDL3tpz73wMsn35r1v5ntvJnkCBFRyTywOeMuxTY149ONwYj4Iex3H
pZMYD4JH3e6EAmK1oqrHeHZcV8uoVQ8byNYeapWGhg2tflh7j4PPg0+Db88DEG5bjj6+pThMZP0Q
6tp0piNA3GYuaeG107tz+nYLKdsL4O/oPR44W+8RCFb13l3fC0DgXrf6ZLcEAIxBTHPGCFVM0yAu
faTAyMIQs7reWAtTo+5EjkUDMLEnU4xM8ekUo1OMheHZn+Oz8kSBpXwz3di7x6p1E18oHAjXLtFZ
P68dG2AhWd/68QX+wc78nb0AvPFAyfiFQkBG/p7r6g+TOmiHYLvrMjejKAqOu/XQaWPKTtvp7Obm
Kzu9Jb5kSQk9qruU/Rh+6NIO2m8VTLFoPivhm5yEmbyEBQllWRZFAP8vKK4v8sKypC4dIHdaO7mM
yucp31FByRa1xW2hKq0sxTF/unqSjl6dX/gSBSMb0fa3d6rNlXK8nt9YXUuXrpIXuUTQgMj6Pr+z
3FTLB3Vuo7Z2WZKTqdxRUJlrzDXmGv9XIwhCy+kb1njC7P78evt9eNOE39TypPsIBgAA
        '''))
        got = nbt.read(data)
        self.assertEqual(got, target)
        self.assertEqual(nbt.write(got), data)


if __name__ == '__main__':
    unittest.main()
