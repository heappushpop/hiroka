from argparse import ArgumentParser
from pathlib import Path
from sys import argv, executable
import logging

from hiroka.metainfo import Metainfo
from hiroka.stats import Stats
from hiroka.tracker import Tracker
from hiroka.transfer import Transfer
import hiroka.settings


def main():
    if argv[0].endswith("__main__.py"):
        argv[0] = f"{Path(executable).name} -m hiroka"

    parser = ArgumentParser()
    parser.add_argument("-d", "--directory")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("filename")
    args = parser.parse_args()

    if args.directory is not None:
        settings.directory = Path(args.directory)

    if args.verbose:
        settings.verbose = True

    logging.basicConfig(
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s.%(msecs)d %(message)s",
        level=logging.INFO if settings.verbose else logging.WARNING,
    )

    with open(args.filename, "rb") as file:
        metainfo = Metainfo(file.read())

    stats = Stats()
    tracker = Tracker(metainfo, stats)
    transfer = Transfer(metainfo, stats, tracker)

    try:
        transfer.start()
    except KeyboardInterrupt:
        if tracker.is_started:
            transfer.stop()


main()
