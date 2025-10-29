import time
import threading

class SnowflakeIDGenerator:
    def __init__(self, worker_id: int = 0, datacenter_id: int = 0):
        # 各部分的位数分配
        self.worker_id_bits = 10           # 机器ID位数
        self.datacenter_id_bits = 5        # 数据中心ID位数（可选扩展，这里简化，与 worker_id 合并使用）
        self.max_worker_id = (1 << self.worker_id_bits) - 1  # 最大 worker_id，即 1023
        self.sequence_bits = 12            # 序列号位数

        self.worker_id_shift = self.sequence_bits
        self.timestamp_left_shift = self.sequence_bits + self.worker_id_bits
        self.sequence_mask = (1 << self.sequence_bits) - 1  # 4095

        # 起始时间戳（可自定义，比如项目启动时间，单位毫秒。这里使用 2020-01-01）
        self.epoch = 1577836800000  # 2020-01-01 00:00:00 UTC

        self.worker_id = worker_id
        if self.worker_id > self.max_worker_id or self.worker_id < 0:
            raise ValueError(f"worker_id 必须在 0 ~ {self.max_worker_id} 之间")

        self.sequence = 0
        self.last_timestamp = -1

        self.lock = threading.Lock()

    def _current_timestamp(self) -> int:
        return int(time.time() * 1000)  # 当前毫秒时间戳

    def _wait_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._current_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._current_timestamp()
        return timestamp

    def generate_id(self) -> int:
        with self.lock:
            timestamp = self._current_timestamp()

            if timestamp < self.last_timestamp:
                raise Exception(f"时钟回拨！拒绝生成ID。当前时间戳: {timestamp}, 上次时间戳: {self.last_timestamp}")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.sequence_mask
                if self.sequence == 0:
                    # 当前毫秒序号用完，等待下一毫秒
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            id_ = ((timestamp - self.epoch) << self.timestamp_left_shift) | \
                  (self.worker_id << self.worker_id_shift) | \
                  self.sequence

            return id_