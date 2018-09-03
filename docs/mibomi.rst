======
Mibomi
======

Mibomi is *Lonami's Bot for Minecraft*. It's a Python 3 client
implementation for the protocol 340 use by Minecraft computer
edition (1.12.2), which means you can create client bots with it.

It works in offline and online mode (although it needs an account
for that!). If it doesn't, please file a bug report or try to create
a pull request to address the issue.


utils/
------

This package contains a small amount of utilities that are good to
have across the rest of the library to reduce code duplication or
ease some designs.


mojang/
-------

This package is responsible for interacting with Mojang's website,
primarily for authentication if ``online-mode`` is enabled.


datatypes/
----------

This package contains generated code with server ``types`` definitions,
as well as some other fundamental types (NBT tags, a World class, etc.).

In addition, it contains the necessary ``DataRW`` class responsible for
serializing and deserializing binary data the way the Minecraft protocol
expects.


network/
--------

This package contains generated code with methods that can be called
to interact with the server, as well as the obvious classes necessary
to connect at all with a Minecraft server and higher-level abstractions
for methods that cannot be easily generated otherwise.

Generally, you will use the ``Client`` from here and subclass it for
your own bots.
