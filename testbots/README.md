# Mibomi's test bots

The files here can be ran in order to test `mibomi`. First, you
must make sure that you have generated all the required code.

Run the following command on the root folder of the project:

```sh
python generator.py
```

After that, `mibomi` must be in your Python path. You can install
the package, or modify `PYTHONPATH` to include the root directory.

When that's done, you can run a `testbot` of your choice, e.g. `pinger`:

```sh
# Linux
PYTHONPATH=.:$PYTHONPATH python testbots/pinger.py

# Windows
set PYTHONPATH=.;%PYTHONPATH%
python testbots/pinger.py
```
