from pathlib import Path
from secrets import token_bytes

directory = Path.cwd()
peer_id_prefix = b"-hi0010-"
peer_id = peer_id_prefix + token_bytes(20 - len(peer_id_prefix))
port = 6881
request_count = 8
reserved = b"\x00\x00\x00\x00\x00\x00\x00\x00"
subpiece_length = 2**14
thread_count = 16
timeout = 60
verbose = False
