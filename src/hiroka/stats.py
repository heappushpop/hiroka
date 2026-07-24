from threading import Lock


class Stats:
    def __init__(self):
        self.downloaded = 0
        self.downloaded_and_verified = 0
        self.lock = Lock()
        self.prev_downloaded = 0
        self.uploaded = 0
