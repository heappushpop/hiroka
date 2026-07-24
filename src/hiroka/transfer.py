from queue import Queue
from shutil import get_terminal_size
from threading import Thread
import logging

from hiroka.bitfield import Bitfield
from hiroka.piece import Piece
import hiroka.settings
import hiroka.workers

logger = logging.getLogger(__name__)


def scale_bytes(n):
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    i = 0
    sign = 1

    if n < 0:
        sign = -1
        n = -n

    while True:
        if n // 1024 and i + 1 < len(units):
            i += 1
        else:
            break
        n /= 1024

    return f"{sign * round(n, 1)}{units[i]}"


class Transfer:
    def __init__(self, metainfo, stats, tracker):
        self.bitfield = Bitfield(metainfo.piece_count)
        self.metainfo = metainfo
        self.pieces = Queue()
        self.stats = stats
        self.tracker = tracker

    def _check_hashes(self):
        self.metainfo.directory.mkdir(exist_ok=True)

        for piece_index in range(self.metainfo.piece_count):
            data = b""

            for path, start, length in self.metainfo.files(piece_index):
                if not path.exists():
                    break

                with open(path, "rb") as file:
                    file.seek(start)
                    data += file.read(length)

            if self.metainfo.verify(piece_index, data):
                self.bitfield.add(piece_index)
                self.stats.downloaded_and_verified += len(data)
            else:
                logger.info(f"Hash of piece {piece_index} didn't match")
                self.pieces.put(Piece(piece_index, self.metainfo))

        self.stats.downloaded = self.stats.downloaded_and_verified
        self.stats.prev_downloaded = self.stats.downloaded_and_verified

    def start(self):
        self._check_hashes()
        self.tracker.started()

        Thread(target=workers.status, daemon=True, args=(self,)).start()

        for _ in range(settings.thread_count):
            Thread(target=workers.peer, daemon=True, args=(self,)).start()

        self.pieces.join()

        with self.stats.lock:
            self.status()

        self.tracker.completed()

    def status(self):
        if settings.verbose:
            return

        width, _ = get_terminal_size()

        name = self.metainfo.name
        speed = scale_bytes(self.stats.downloaded - self.stats.prev_downloaded)
        downloaded = scale_bytes(self.stats.downloaded_and_verified)
        length = scale_bytes(self.metainfo.length)
        progress = self.stats.downloaded_and_verified / self.metainfo.length

        left = f"{name} "
        right = f"{speed}/s {downloaded}/{length} {progress:.0%}"

        print("\r" + left + right.rjust(width - len(left)), end="")

    def stop(self):
        self.tracker.stopped()
