import unittest
from generator import parser
from generator.parser import parse_str

import collections
drain = collections.deque(maxlen=0).extend


class TestParser(unittest.TestCase):
    def test_redefined(self):
        with self.assertRaises(ValueError):
            drain(parse_str('type x:i32 y:i32 x:double -> Type;'))

    def test_some(self):
        next(parse_str('type -> Type;'))

    def test_none(self):
        with self.assertRaises(StopIteration):
            next(parse_str('// just a comment'))

    def test_comments(self):
        next(parse_str('''
        // comment before
        type
        // comment in between
        ->
        // comment in between
        Type;
        // coment after
        '''))

    def test_no_id(self):
        item = next(parse_str('type x:i32 -> Type;'))
        self.assertEqual(item.id, None)
        self.assertEqual(item.name, 'type')
        self.assertEqual(len(item.args), 1)
        self.assertEqual(item.cls, 'Type')
        self.assertEqual(item.params, ())
        self.assertFalse(item.has_optional)
        self.assertEqual(item.args[0].args, ())

    def test_yes_id(self):
        item = next(parse_str('type#71 -> Type;'))
        self.assertEqual(item.id, 0x71)
        self.assertEqual(item.name, 'type')
        self.assertEqual(len(item.args), 0)
        self.assertEqual(item.cls, 'Type')
        self.assertEqual(item.params, ())
        self.assertFalse(item.has_optional)

    def test_input_params(self):
        item = next(parse_str('type#13?inp -> Type;'))
        self.assertEqual(item.params, ('inp',))
        self.assertFalse(item.has_optional)

    def test_optional(self):
        item = next(parse_str('type x:i32 y:str? -> Type;'))
        self.assertTrue(item.has_optional)
        self.assertFalse(item.args[0].optional)
        self.assertTrue(item.args[1].optional)

    def test_cond_block(self):
        item = next(parse_str('type x:i32 y:str ?x?==?0 y -> Type;'))
        self.assertTrue(item.has_optional)
        self.assertFalse(item.args[0].optional)
        self.assertTrue(item.args[1].referenced)
        self.assertIsInstance(item.args[2], parser.Condition)
        self.assertIsInstance(item.args[3], parser.ArgReference)
        self.assertEqual(item.args[3].ref, item.args[1])

    def test_cond_disable(self):
        item = next(parse_str('type ? -> Type;'))
        self.assertIsInstance(item.args[0], parser.ConditionDisable)

    def test_builtin(self):
        item = next(parse_str('type a:i8 b:u8 c:i16 d:u16 e:i32 f:u32 '
                              'g:i64 h:u64 i:bool j:float k:double -> Type;'))
        self.assertTrue(all(bool(x.builtin_fmt) for x in item.args))

        item = next(parse_str('type a:str b:bytes c:angle d:Other -> Type;'))
        self.assertFalse(any(bool(x.builtin_fmt) for x in item.args))

    def test_vector(self):
        item = next(parse_str('type a:u8+str -> Type;'))
        self.assertEqual(item.args[0].name, 'a')
        self.assertEqual(item.args[0].vec_count_cls, 'u8')
        self.assertEqual(item.args[0].cls, 'str')

    def test_arg_cls_param(self):
        item = next(parse_str('type a:str b:Other@a -> Type;'))
        self.assertEqual(item.args[1].name, 'b')
        self.assertEqual(item.args[1].args, ('a',))

    def test_arg_all(self):
        item = next(parse_str('type a:str b:i16+Other@a? -> Type;'))
        self.assertEqual(item.args[1].name, 'b')
        self.assertEqual(item.args[1].vec_count_cls, 'i16')
        self.assertEqual(item.args[1].cls, 'Other')
        self.assertEqual(item.args[1].args, ('a',))


if __name__ == '__main__':
    unittest.main()
