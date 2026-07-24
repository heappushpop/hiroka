from collections import deque
import logging

import hiroka.settings

logger = logging.getLogger(__name__)


class Piece:
    def __init__(self, index, metainfo):
        piece_length = metainfo.piece_length(index)
        self._downloaded = set()
        self._metainfo = metainfo
        self._subpieces = deque()
        self.data = bytearray(piece_length)
        self.index = index

        for begin in range(0, piece_length, settings.subpiece_length):
            self._subpieces.append(
                (index, begin, min(settings.subpiece_length, piece_length - begin))
            )

        self._subpiece_count = len(self._subpieces)

    def add(self, index, begin, subpiece):
        if index != self.index:
            logger.info(f"Unexpected piece {index}")
            return

        if begin in self._downloaded:
            logger.info(f"Retransmission of subpiece {begin}")
            return

        self._downloaded.add(begin)
        self.data[begin : begin + len(subpiece)] = subpiece

    def is_downloaded(self):
        if len(self._downloaded) < self._subpiece_count:
            return False

        return self._metainfo.verify(self.index, self.data)

    def is_next(self):
        return len(self._subpieces) > 0

    def next(self):
        return self._subpieces.popleft()

    def write(self):
        i = 0

        for path, start, length in self._metainfo.files(self.index):
            path.touch()

            with open(path, "r+b") as file:
                file.seek(start)
                file.write(self.data[i : i + length])
                i += length
