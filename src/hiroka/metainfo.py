from datetime import datetime
from hashlib import sha1
from pathlib import Path

from hiroka.bencode import decode, encode
import hiroka.settings


def hash(data):
    hash = sha1()
    hash.update(data)

    return hash.digest()


class MetainfoError(Exception):
    pass


class Metainfo:
    def __init__(self, data):
        decoded = decode(data)

        self.announce = decoded["announce"].decode()
        self.comment = decoded["comment"].decode() if "comment" in decoded else None
        self.created_by = (
            decoded["created by"].decode() if "created by" in decoded else None
        )
        self.creation_date = (
            datetime.fromtimestamp(decoded["creation date"])
            if "creation date" in decoded
            else None
        )

        info = decoded["info"]

        self.name = info["name"].decode()
        self._piece_length = info["piece length"]
        self._pieces = info["pieces"]

        if (
            "length" in info
            and "files" in info
            or "length" not in info
            and "files" not in info
        ):
            raise MetainfoError('Exactly one of "length" or "files" is required')

        self.directory = settings.directory

        if "files" in info:
            files = info["files"]
            self.directory /= self.name
        else:
            files = [
                {
                    "length": info["length"],
                    "path": [info["name"]],
                }
            ]

        self._files = []
        self.length = 0

        for file in files:
            path = map(lambda component: component.decode(), file["path"])
            self._files.append(
                {
                    "length": file["length"],
                    "path": self.directory / Path(*path),
                }
            )
            self.length += file["length"]

        self.info_hash = hash(encode(info))
        self.piece_count = len(self._pieces) // 20

    def files(self, piece_index):
        piece_length = self.piece_length(0)
        total_start = piece_index * piece_length
        total_end = total_start + piece_length
        start = 0
        end = 0
        files = []

        for file in self._files:
            end += file["length"]

            if total_start < start and end <= total_end - 1:
                files.append((file["path"], start, end - start))
            elif start <= total_start < end and start <= total_end - 1 < end:
                files.append(
                    (file["path"], total_start - start, total_end - total_start)
                )
                break
            elif start <= total_start < end:
                files.append((file["path"], total_start - start, end - total_start))
            elif start <= total_end - 1 < end:
                files.append((file["path"], 0, total_end - start))
                break

            start += file["length"]

        return files

    def piece_length(self, piece_index):
        if piece_index < self.piece_count - 1:
            return self._piece_length

        return self.length - (self.piece_count - 1) * self._piece_length

    def verify(self, piece_index, data):
        if len(data) != self.piece_length(piece_index):
            return False

        return hash(data) == self._pieces[20 * piece_index : 20 * piece_index + 20]
