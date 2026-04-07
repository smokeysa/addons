"""
Sampler which takes a sample of the backtrace at a given frequency, and counts
how often we find ourselves in each place.

Usage:
   usample <start_bbcount> <end_bbcount> <bbcount_interval>
   E.g. 1 1000 1
    means sample every basic block from 1 to 1000.

Contributors: Isa Smith, Toby Lloyd Davies
Copyright (C) 2019 Undo Ltd
"""

import sys
from collections import defaultdict

import gdb
from undo.debugger_extensions import debugger_utils, udb


class SampleFunctions(gdb.Command):
    """
    Advance through the debuggee, sampling the function we are currently in.
    """

    def __init__(self):
        super().__init__("usample", gdb.COMMAND_USER)

    @staticmethod
    def invoke(arg, from_tty):
        """
        arg is:
        <start_bbcount> <end_bbcount> <bbcount_interval> [<filename>]
        E.g. 0 1000 1
        means sample every basic block from 1 to 1000.
        """
        with udb.time.auto_reverting():
            functions = defaultdict(int)

            args = gdb.string_to_argv(arg)

            if len(args) not in (3, 4):
                raise gdb.GdbError(
                    "Usage: usample <start_bbcount> <end_bbcount> <bbcount_interval> [<filename>]"
                )

            try:
                start_bbcount = int(args[0])
                end_bbcount = int(args[1])
                interval = int(args[2])
            except ValueError as e:
                raise gdb.GdbError(
                    "start_bbcount, end_bbcount, and bbcount_interval must be integers"
                ) from e

            if len(args) > 3:
                output = open(args[3], "wt")  # pylint: disable=consider-using-with
            else:
                output = sys.stdout

            sample_range = range(start_bbcount, end_bbcount + 1, interval)
            num_samples = len(sample_range)
            print(f"Taking {num_samples} samples.")
            save_interval = max(1, num_samples // 10)

            with debugger_utils.temporary_parameter("pagination", False):
                for i, current_bbcount in enumerate(sample_range):
                    udb.time.goto(current_bbcount)
                    frame = gdb.newest_frame()
                    # Create list of functions in the backtrace
                    trace_functions = []
                    while frame is not None:
                        if frame.name() is not None:
                            trace_functions.append(frame.name())
                        else:
                            # If no symbol for function use pc
                            trace_functions.append(hex(frame.pc()))
                        frame = frame.older()
                    # Concatenate functions in backtrace to create key
                    key = ";".join(reversed(trace_functions))
                    functions[key] += 1

                    if output is not sys.stdout and (i + 1) % save_interval == 0:
                        output.seek(0)
                        output.truncate()
                        for function, count in functions.items():
                            output.write(f"{function} {count}\n")
                        output.flush()

        # Now print what we've found...
        for function in functions:
            output.write(f"{function} {functions[function]}\n")


SampleFunctions()
