class PyGen:
    """
    Helper class to generate Python code.
    """
    def __init__(self, fd, indent_str='    '):
        self.fd = fd
        self._indent_next = True
        self.indent_level = 0
        self.indent_str = indent_str

    def write(self, string, *args):
        """
        Writes the given string to the stream, previously
        formatting the arguments given into it if any.

        This call will apply indentation if the cursor
        is currently on a new empty line.
        """
        if self._indent_next:
            self._indent_next = False
            self.fd.write(self.indent_str * self.indent_level)

        if args:
            self.fd.write(string.format(*args))
        else:
            self.fd.write(string)

        if string.endswith('\n'):
            self._indent_next = True

    def writeln(self, line='', *args):
        """
        Alias for ``write(string + '\n', *args)``.
        """
        self.write(line + '\n', *args)

    def block(self, line='', *args):
        """
        Calls ``writeln(string, *args)`` and returns a new block.

        The block will cause a new indent level to be used during
        its scope, useful to build ``if``, ``while``, etc..
        """
        self.writeln(line, *args)
        return _Block(self)

    def func(self, name, *args):
        """
        Creates and returns a new block defining the given function.
        """
        return self.block('def {}({}):', name, ', '.join(args))

    def afunc(self, name, *args):
        """
        Creates and returns a new block defining the given async function.
        """
        return self.block('async def {}({}):', name, ', '.join(args))

    def meth(self, name, *args):
        """
        Creates and returns a new block defining the given method.
        """
        return self.func(name, 'self', *args)

    def ameth(self, name, *args):
        """
        Creates and returns a new block defining the given async method.
        """
        return self.afunc(name, 'self', *args)

    @staticmethod
    def empty():
        """
        Creates and returns an empty block. It won't do anything.
        """
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
