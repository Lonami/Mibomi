class PyGen:
    def __init__(self, fd, indent_str='    '):
        self.fd = fd
        self._indent_next = True
        self.indent_level = 0
        self.indent_str = indent_str

    def write(self, line, *args):
        if self._indent_next:
            self._indent_next = False
            self.fd.write(self.indent_str * self.indent_level)

        if args:
            self.fd.write(line.format(*args))
        else:
            self.fd.write(line)

        if line.endswith('\n'):
            self._indent_next = True

    def writeln(self, line='', *args):
        self.write(line + '\n', *args)

    def block(self, line='', *args):
        self.writeln(line, *args)
        return _Block(self)

    def func(self, name, *args):
        return self.block('def {}({}):', name, ', '.join(args))

    def afunc(self, name, *args):
        return self.block('async def {}({}):', name, ', '.join(args))

    def meth(self, name, *args):
        return self.func(name, 'self', *args)

    def ameth(self, name, *args):
        return self.afunc(name, 'self', *args)

    @staticmethod
    def empty():
        return _Empty()

    def __enter__(self):
        self.fd.__enter__()
        return self

    def __exit__(self, *args):
        self.fd.__exit__(*args)


class _Block:
    def __init__(self, gen):
        self._gen = gen

    def __enter__(self):
        self._gen.indent_level += 1
        return self

    def __exit__(self, *args):
        self._gen.indent_level -= 1


class _Empty:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
