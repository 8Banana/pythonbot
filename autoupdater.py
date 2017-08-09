#!/usr/bin/env python3
import inspect
import os
import subprocess
import sys
import threading
import time

# ~1-2h is good IMO. depends on how often you update.
INTERVAL = int(1 * 60 * 60 * 1.5)  # seconds


def _get_output(args):
    process = subprocess.run(args,
                             stdout=subprocess.PIPE)
    assert process.returncode == 0
    return process.stdout.decode("ascii").strip()


def _worker(filepath):
    remote = "origin"
    branch = _get_output(["git", "symbolic-ref", "--short", "HEAD"])
    commit_hash = _get_output(["git", "rev-parse", "HEAD"])
    # print(f"Working on {remote}/{branch}@{commit_hash}")

    while True:
        command = subprocess.run(["git", "pull", remote, branch],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)

        if command.returncode == 0:
            new_commit_hash = _get_output(["git", "rev-parse", "HEAD"])
            # print("Got commit", new_commit_hash)

            if new_commit_hash != commit_hash:
                # print("Restarting..")
                os.execlp(sys.executable, sys.executable, filepath)

        time.sleep(INTERVAL)


def initialize():
    # Initialize the auto-updater. Must be called in the main script.
    parent_globals = inspect.currentframe().f_back.f_globals
    assert parent_globals["__name__"] == "__main__"
    filepath = parent_globals["__file__"]
    threading.Thread(target=_worker, args=(filepath,)).start()
