from time import sleep, time
import logging

from hiroka.bitfield import Bitfield
from hiroka.peer import MESSAGE_TYPE, Peer
from hiroka.piece import Piece

logger = logging.getLogger(__name__)


def peer(transfer):
    while True:
        piece = transfer.pieces.get()
        peer = transfer.tracker.peers.popleft()

        with peer.socket as socket:
            logger.info(f"Connecting to {peer}")

            try:
                socket.connect((str(peer.ip), peer.port))
                peer.handshake(transfer.metainfo.info_hash)
                peer.send_bitfield(transfer.bitfield)
                peer.send_interested()
                peer.send_unchoke()

                while True:
                    peer.send_request(piece)
                    message_type, message = peer.receive()

                    if message_type is None:
                        continue

                    if message_type == MESSAGE_TYPE["subpiece"]:
                        with transfer.stats.lock:
                            transfer.stats.downloaded += len(message["subpiece"])

                        piece.add(
                            message["piece_index"],
                            message["begin"],
                            message["subpiece"],
                        )

                        if piece.is_downloaded():
                            piece.write()

                            with transfer.stats.lock:
                                transfer.bitfield.add(piece.index)
                                transfer.stats.downloaded_and_verified += len(
                                    piece.data
                                )

                            peer.send_have(piece.index)
                            transfer.pieces.task_done()
                            piece = transfer.pieces.get()
            except Exception as error:
                if isinstance(error, KeyboardInterrupt):
                    raise

                logger.info(repr(error))
                transfer.pieces.task_done()
                transfer.pieces.put(Piece(piece.index, transfer.metainfo))

        transfer.tracker.peers.append(
            Peer(peer.ip, peer.port, Bitfield(transfer.metainfo.piece_count))
        )


def status(transfer):
    while True:
        start = time()

        with transfer.stats.lock:
            transfer.status()
            transfer.stats.prev_downloaded = transfer.stats.downloaded

        diff = time() - start

        if diff >= 1:
            continue

        sleep(1 - diff)
