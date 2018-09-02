================
Generator Module
================

The generator module contains the code necessary to turn ``.mbm`` definitions
into Python code, but first we need to talk about what these are.

``.mbm`` definitions
--------------------

*MBM* stands for *"Mibomi"*, which in turn stands for *"LonaMI's BOt
for MInecraft"*. *MBM* definitions are a short way of specifying the
network packets used by Minecraft.


Specification
^^^^^^^^^^^^^

Comments start with ``//`` and these and following characters
should be ignored until a newline character is found.

Character Classes:

.. code-block:: text

    lc-letter  ::= a | b | … | z
    uc-letter  ::= A | B | … | Z
    letter     ::= lc-letter | uc-letter
    digit      ::= 0 | 1 | … | 9
    hex-digit  ::= digit | a | b | c | d | e | f
    underscore ::= _
    id-sep     ::= #
    condition  ::= ?
    colon      ::= :
    vector     ::= +
    param      ::= @
    end        ::= ;
    cls-def    ::= ->
    ident-char ::= letter | underscore
    any        ::= letter | digit | ! | = | ' | "

Identifiers:

.. code-block:: text

    ident      ::= letter { ident-char }
    full-ident ::= ident [ id-sep hex-digit * ] [ condition ident ]
    arg-ident  ::= ident colon [ ident vector ] ident [ param ident ] [ condition ]
    cond-ident ::= condition ident condition any condition any | condition

Definition:

.. code-block::

    full-ident { arg-ident } [ { cond-ident ident * } ] cls-def ident end

Thus some examples:

.. code-block::

    // valid ident
    name

    // valid full-ident
    name
    name#12ab
    name?
    name#12ab?

    // valid arg-ident
    name:str
    name:str?
    name:i32+str
    name:Type@x
    name:i32+Type@x?

    // valid cond ident
    ?name?==?'literal'

A complete definition could be:

.. code-block::

    type_name#1?extended
        name:str
        age:u8
        cars:i32+str?
        last_name:str
        ?extended?==?True last_name
        -> TypeName;


This defines a type called ``type_name``, with ``0x1`` as its ID.
When used as a type for another definition, it should receive the
``extended`` value.

It defines several arguments, as string, unsigned bytes, optional
vector with an integer length, and the last name only if extended
is a certain value.

Finally, the class name should be ``TypeName``.

If you can improve this, please submit a pull request. I by no means
am an expert writing formal specifications for custom-made languages.

The specification currently does not allow documenting the definitions.

Parser
^^^^^^

The parser is responsible for accepting strings that contain
semicolon-separated *MBM* definitions and yielding the parsed
definitions, with their arguments, and some extra convenience
attributes such as whether a definition has conditionals or
not, etc. Tests for the parser are available under ``tests/``.

Generator
^^^^^^^^^

Responsible for accepting the instances that the parser previously
created, and converting them into Python code. Currently, it must
convert definitions into either client-bound classes (since the
server may send these at any time and the client needs to be able
to interact with the data), or server-bound methods (since these
are only sent to the server).

Compound, complex types are hardcoded and shared for both the client
and server types, since these often differ from the rest and need
special treatment, or would otherwise overcomplicated the *MBM*
specification. Some examples are NBT tags, chunk data, etc.

PyGen
^^^^^

There exists a Python Generator helper module that eases generating
Python code from within Python code itself. There are several methods
to create blocks through ``with``, which causes the indent to match
the one from the generated code. Empty blocks are also available,
allowing to always-exit once done in some cases where a ``with`` block
is not enough due to other control flow operators such as ``if``.
