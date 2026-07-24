from collections import deque
from ipaddress import ip_address
from struct import unpack
from urllib.parse import urlencode
from urllib.request import urlopen
import logging

from hiroka.bencode import decode
from hiroka.bitfield import Bitfield
from hiroka.peer import Peer
import hiroka.settings

logger = logging.getLogger(__name__)


class TrackerError(Exception):
    pass


class Tracker:
    def __init__(self, metainfo, stats):
        self.is_started = False
        self.metainfo = metainfo
        self.peers = deque()
        self.stats = stats

    def _parse_peers(self, value):
        if isinstance(value, bytes):
            for i in range(0, len(value), 6):
                ip, port = unpack("!IH", value[i : i + 6])
                self.peers.append(
                    Peer(ip_address(ip), port, Bitfield(self.metainfo.piece_count))
                )
        elif isinstance(value, list):
            for peer in value:
                ip, port = peer["ip"].decode(), peer["port"]
                self.peers.append(
                    Peer(ip_address(ip), port, Bitfield(self.metainfo.piece_count))
                )
        else:
            raise TypeError("'value' must be a bytes or list object")

    def request(self, event):
        params = urlencode(
            {
                "downloaded": self.stats.downloaded_and_verified,
                "event": event,
                "info_hash": self.metainfo.info_hash,
                "left": self.metainfo.length - self.stats.downloaded_and_verified,
                "peer_id": settings.peer_id,
                "port": settings.port,
                "uploaded": self.stats.uploaded,
            }
        )
        url = f"{self.metainfo.announce}?{params}"
        logger.info(f"Tracker request: {url}")

        with urlopen(url) as file:
            decoded = decode(file.read())

        if "failure reason" in decoded:
            raise TrackerError(decoded["failure reason"].decode())

        self.interval = decoded["interval"]
        self._parse_peers(decoded["peers"])

    def started(self):
        self.request("started")
        self.is_started = True

    def completed(self):
        self.request("completed")

    def stopped(self):
        self.request("stopped")

    def regular(self):
        self.request("")
