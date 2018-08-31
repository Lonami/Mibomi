import unittest
from mibomi.datarw import DataRW


class TestDataRW(unittest.TestCase):
    def test_vari(self):
        lft = [0, 1, 2, 127, 128, 255, 2147483647, -1, -2147483648]
        rgt = [b'\x00', b'\x01', b'\x02', b'\x7f', b'\x80\x01', b'\xff\x01',
               b'\xff\xff\xff\xff\x07', b'\xff\xff\xff\xff\x0f',
               b'\x80\x80\x80\x80\x08']

        for l, r in zip(lft, rgt):
            datar = DataRW(r)
            self.assertEqual(l, datar.readvari32())
            dataw = DataRW()
            dataw.writevari32(l)
            self.assertEqual(r, dataw.getvalue())

    def test_pos(self):
        dataw = DataRW()
        dataw.writevari32(340)
        dataw.writepos((97, 98, 99))
        dataw.writepos((-1, -2, 99))
        dataw.writepos((98, 99, -1))
        datar = DataRW(dataw.getvalue())
        self.assertEqual(datar.readvari32(), 340)
        self.assertEqual(datar.readpos(), (97, 98, 99))
        self.assertEqual(datar.readpos(), (-1, -2, 99))
        self.assertEqual(datar.readpos(), (98, 99, -1))


if __name__ == '__main__':
    unittest.main()
