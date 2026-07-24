from socket import AF_INET, SOCK_STREAM, socket
from struct import pack, unpack
import logging

from hiroka.bitfield import Bitfield
import hiroka.settings

logger = logging.getLogger(__name__)

MESSAGE_TYPE = {
    "choke": 0,
    "unchoke": 1,
    "interested": 2,
    "not_interested": 3,
    "have": 4,
    "bitfield": 5,
    "request": 6,
    "subpiece": 7,
    "cancel": 8,
}

PROTOCOL = b"BitTorrent protocol"


class PeerError(Exception):
    pass


class Peer:
    def __init__(self, ip, port, bitfield):
        self._am_i_choking = True
        self._am_i_interested = False
        self._bitfield = bitfield
        self._data = b""
        self._is_choking = True
        self._is_interested = False
        self._request_count = 0
        self.ip = ip
        self.port = port
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.settimeout(settings.timeout)

    def __str__(self):
        return f"{self.ip}:{self.port}"

    def _receive_at_least(self, n):
        while len(self._data) < n:
            data = self.socket.recv(4096)

            if not data:
                raise PeerError("Client disconnected")

            self._data += data

    def _consume(self, n):
        self._data = self._data[n:]

    def handshake(self, info_hash):
        logger.info("Sending handshake")
        self.socket.sendall(
            pack("!B", len(PROTOCOL))
            + PROTOCOL
            + settings.reserved
            + info_hash
            + settings.peer_id
        )
        self._receive_at_least(1)
        if unpack("!B", self._data[:1])[0] != len(PROTOCOL):
            raise PeerError("Handshake failed: invalid protocol length")
        self._consume(1)
        self._receive_at_least(len(PROTOCOL))
        if self._data[: len(PROTOCOL)] != PROTOCOL:
            raise PeerError("Handshake failed: invalid protocol")
        self._consume(len(PROTOCOL))
        self._receive_at_least(len(settings.reserved))
        self._consume(len(settings.reserved))
        self._receive_at_least(len(info_hash))
        if self._data[: len(info_hash)] != info_hash:
            raise PeerError("Handshake failed: invalid info hash")
        self._consume(len(info_hash))
        self._receive_at_least(len(settings.peer_id))
        self._consume(len(settings.peer_id))
        logger.info("Received handshake")

    def send_keep_alive(self):
        logger.info("Sending keep alive")
        self.socket.sendall(pack("!I", 0))

    def send_choke(self):
        self._am_i_choking = True
        logger.info("Sending choke")
        self.socket.sendall(pack("!IB", 1, MESSAGE_TYPE["choke"]))

    def send_unchoke(self):
        self._am_i_choking = False
        logger.info("Sending unchoke")
        self.socket.sendall(pack("!IB", 1, MESSAGE_TYPE["unchoke"]))

    def send_interested(self):
        self._am_i_interested = True
        logger.info("Sending interested")
        self.socket.sendall(pack("!IB", 1, MESSAGE_TYPE["interested"]))

    def send_not_interested(self):
        self._am_i_interested = False
        logger.info("Sending not interested")
        self.socket.sendall(pack("!IB", 1, MESSAGE_TYPE["not_interested"]))

    def send_have(self, piece_index):
        logger.info(f"Sending have: {piece_index}")
        self.socket.sendall(pack("!IBI", 5, MESSAGE_TYPE["have"], piece_index))

    def send_bitfield(self, bitfield):
        logger.info(f"Sending bitfield")
        self.socket.sendall(
            pack("!IB", 1 + len(bitfield.data), MESSAGE_TYPE["bitfield"])
            + bitfield.data
        )

    def send_request(self, piece):
        if self._is_choking:
            return

        if piece.index not in self._bitfield:
            raise PeerError(f"{self} doesn't have piece {piece.index}")

        while (
            self._request_count < settings.request_count
            and piece.is_next()
            and not self._is_choking
        ):
            piece_index, begin, subpiece_length = piece.next()
            logger.info(f"Sending request: {piece_index} {begin} {subpiece_length}")
            self.socket.sendall(
                pack(
                    "!IBIII",
                    13,
                    MESSAGE_TYPE["request"],
                    piece_index,
                    begin,
                    subpiece_length,
                )
            )
            self._request_count += 1

    def send_subpiece(self, piece_index, begin, subpiece):
        logger.info(f"Sending subpiece: {piece_index} {begin}")
        self.socket.sendall(
            pack(
                "!IBII", 9 + len(subpiece), MESSAGE_TYPE["subpiece"], piece_index, begin
            )
            + subpiece
        )

    def send_cancel(self, piece_index, begin, subpiece_length):
        logger.info(f"Sending cancel: {piece_index} {begin} {subpiece_length}")
        self.socket.sendall(
            pack(
                "!IBIII",
                13,
                MESSAGE_TYPE["cancel"],
                piece_index,
                begin,
                subpiece_length,
            )
        )

    def _received_keep_alive(self):
        logger.info("Received keep alive")

        return None, None

    def _received_choke(self):
        logger.info("Received choke")
        self._is_choking = True

        return MESSAGE_TYPE["choke"], None

    def _received_unchoke(self):
        logger.info("Received unchoke")
        self._is_choking = False

        return MESSAGE_TYPE["unchoke"], None

    def _received_interested(self):
        logger.info("Received interested")
        self._is_interested = True

        return MESSAGE_TYPE["interested"], None

    def _received_not_interested(self):
        logger.info("Received not interested")
        self._is_interested = False

        return MESSAGE_TYPE["not_interested"], None

    def _received_have(self, length):
        piece_index = unpack("!I", self._data[:length])[0]
        self._consume(length)
        logger.info(f"Received have: {piece_index}")
        self._bitfield.add(piece_index)

        return MESSAGE_TYPE["have"], None

    def _received_bitfield(self, length):
        logger.info(f"Received bitfield")
        self._bitfield = Bitfield(self._data[:length])
        self._consume(length)

        return MESSAGE_TYPE["bitfield"], None

    def _received_request(self, length):
        piece_index, begin, subpiece_length = unpack("!III", self._data[:length])
        self._consume(length)
        logger.info(f"Received request: {piece_index} {begin} {subpiece_length}")

        return MESSAGE_TYPE["request"], None

    def _received_subpiece(self, length):
        piece_index, begin = unpack("!II", self._data[:8])
        self._consume(8)
        logger.info(f"Received subpiece: {piece_index} {begin}")
        length -= 8
        subpiece = self._data[:length]
        self._consume(length)
        self._request_count -= 1

        return MESSAGE_TYPE["subpiece"], {
            "piece_index": piece_index,
            "begin": begin,
            "subpiece": subpiece,
        }

    def _received_cancel(self, length):
        piece_index, begin, subpiece_length = unpack("!III", self._data[:length])
        self._consume(length)
        logger.info(f"Received cancel: {piece_index} {begin} {subpiece_length}")

        return MESSAGE_TYPE["cancel"], None

    def receive(self):
        self._receive_at_least(4)
        message_length = unpack("!I", self._data[:4])[0]
        self._consume(4)

        if message_length == 0:
            self._received_keep_alive()
            return

        self._receive_at_least(message_length)
        message_type = unpack("!B", self._data[0:1])[0]
        self._consume(1)

        length = message_length - 1

        if message_type == MESSAGE_TYPE["choke"]:
            return self._received_choke()
        elif message_type == MESSAGE_TYPE["unchoke"]:
            return self._received_unchoke()
        elif message_type == MESSAGE_TYPE["interested"]:
            return self._received_interested()
        elif message_type == MESSAGE_TYPE["not_interested"]:
            return self._received_not_interested()
        elif message_type == MESSAGE_TYPE["have"]:
            return self._received_have(length)
        elif message_type == MESSAGE_TYPE["bitfield"]:
            return self._received_bitfield(length)
        elif message_type == MESSAGE_TYPE["request"]:
            return self._received_request(length)
        elif message_type == MESSAGE_TYPE["subpiece"]:
            return self._received_subpiece(length)
        elif message_type == MESSAGE_TYPE["cancel"]:
            return self._received_cancel(length)
        else:
            raise PeerError(f"Unexpected message type {message_type}")
