from socket import socket, SOCK_DGRAM, AF_INET
from logger import logger
import struct
from select import select
from random import random, randint
from time import sleep

_HEADER_FORMAT = 'HHHiH'
_HEADER_FORMAT_NO_CHK = 'HHHi'
_HEADER_LEN = struct.calcsize(_HEADER_FORMAT)

_SYN = 0b00000001
_FIN = 0b00000010
_ACK = 0b00000100

_TIMEOUT = 1

class rdt:
    # CTOR
    def __init__(self, pkt_size : int = 4096) -> None:
        if pkt_size < _HEADER_LEN:
            raise Exception(f'PKT SIZE must at least be equal to or greater than {_HEADER_LEN}')
        self.logger = logger()
        self.pkt_size = pkt_size
        self.skt = socket(AF_INET, SOCK_DGRAM)
        self.seq_num = 0
        self.ack_num = 0
        self.cwnd = 1
        print(_HEADER_LEN)
    
    # INTERFACE FUNCTIONS

    def bind(self, bind_addr):
        self.skt.bind(bind_addr)

    # sends a maximum of pkt_size - header_len bytes
    def send(self, msg : bytes, addr) -> None:
        total_sent = 0
        buf = [msg[i:i+self.pkt_size-_HEADER_LEN] for i in range(0, len(msg), self.pkt_size-_HEADER_LEN)]
        n_pkts = min(len(buf), self.cwnd)
        pkts = [rdt.__mk_pkt(self.seq_num + i, self.ack_num, 0, buf[i]) for i in range(n_pkts)]

        for i in range(n_pkts):
            self.logger.log_info(f'PKT {int(self.seq_num + i)} SENT, WAITING FOR RESPONSE')
            self.udt_send(pkts[i], addr)

        rlist = [self.skt]
        while True:
            r, _, _ = select(rlist, [], [], _TIMEOUT)
            if r:
                res_pkt, _ = self.skt.recvfrom(self.pkt_size)
                if rdt.__corrupted(res_pkt):
                    self.logger.log_info('RECEIVED CORRUPTED PKT, WAITING FOR TIMEOUT')
                elif not rdt.__is_ack(res_pkt, self.seq_num + 1):
                    self.logger.log_info('RECEIVED DUPLICATE ACK, WAITING FOR TIMEOUT')
                else:
                    header, _ = rdt.__unwrap_pkt(res_pkt)
                    n_sent = header[1] - self.seq_num
                    total_sent += n_sent
                    self.logger.log_info(f'RECEIVED ACK {int(header[1] - 1)}, SEND SUCCESSFUL, CWND = {self.cwnd + 1}')
                    self.seq_num = header[1]
                    buf = buf[n_sent:]
                    self.cwnd += 1
                    n_pkts = min(len(buf), self.cwnd)
                    pkts = [rdt.__mk_pkt(self.seq_num + i, self.ack_num, 0, buf[i]) for i in range(n_pkts)]
                    # print(total_sent, self.cwnd)
                    if n_pkts == 0:
                        break
                    elif total_sent % self.cwnd - 1 == 0:
                        for i in range(n_pkts):
                            self.logger.log_info(f'PKT {int(self.seq_num + i)} SENT, WAITING FOR RESPONSE')
                            self.udt_send(pkts[i], addr)
            else:
                self.logger.log_info(f'TIMED OUT, RESENDING PKTS, CWND = {max(int(self.cwnd / 2), 1)}')
                self.cwnd = max(int(self.cwnd / 2), 1)
                n_pkts = min(len(buf), self.cwnd)
                pkts = [rdt.__mk_pkt(self.seq_num + i, self.ack_num, 0, buf[i]) for i in range(n_pkts)]
                for i in range(n_pkts):
                    self.logger.log_info(f'PKT {int(self.seq_num + i)} SENT, WAITING FOR RESPONSE')
                    self.udt_send(pkts[i], addr)

    # recvs a maximum of pkt_size - header_len bytes
    def recv(self) -> tuple:
        rlist = [self.skt]
        while True:
            self.logger.log_info(f'WAITING FOR PKT {int(self.ack_num)}')
            r, _, _ = select(rlist, [], [])
            if r:
                pkt, ret_addr = self.skt.recvfrom(self.pkt_size)
                header, msg = rdt.__unwrap_pkt(pkt)
                if rdt.__corrupted(pkt):
                    self.logger.log_info('RECEIVED CORRUPTED PKT, RESENDING ACK')
                    self.__send_ack_num(ret_addr)
                elif header[0] != self.ack_num:
                    self.logger.log_info('RECEIVED UNORDERED PKT, RESENDING ACK')
                    self.__send_ack_num(ret_addr)
                else:
                    self.logger.log_info('RECEIVE SUCCESSFUL, SENDING ACK')
                    self.ack_num = self.ack_num + 1
                    self.__send_ack_num(ret_addr)
                    break
        return msg, ret_addr
    
    def udt_send(self, pkt : bytes, addr):
        x = random()
        if x < 0.1:
            self.logger.log_error('PKT CORRUPTED')
            err_pkt = bytearray(pkt)
            pos = randint(0, len(err_pkt) - 1)
            err_pkt[pos] = (err_pkt[pos] ^ 0x01)
            pkt = bytes(err_pkt)
        elif x < 0.2:
            self.logger.log_error('PKT LOST')
            return
        #elif x >= 0.2 and x < 0.3:
        #    self.logger.log_error('PKT DELAYED')
        #    sleep(1)
        self.skt.sendto(pkt, addr)

    # non-static utility functions
    def __send_ack_num(self, addr):
        ack_pkt = rdt.__mk_pkt(self.seq_num, self.ack_num, _ACK, b'')
        self.udt_send(ack_pkt, addr)

    # STATIC UTILITY FUNCTIONS

    @staticmethod
    def __is_ack(pkt, exp_ack_num):
        header, _ = rdt.__unwrap_pkt(pkt)
        return (header[2] & _ACK) == _ACK and header[1] >= exp_ack_num
    #@staticmethod
    #def __is_nak(pkt, exp_sq_num):
    #    header, _ = rdt.__unwrap_pkt(pkt)
    #    return header[1] == NAK or header[0] != exp_sq_num
    @staticmethod
    def __corrupted(pkt):
        return rdt.__chksum(pkt) != 0
    
    @staticmethod
    def __chksum(msg : bytes):
        length = len(msg)
        if length % 2 == 1:
            msg += b'\0'
            length += 1

        s = 0
        for i in range(0, length, 2):
            temp = msg[i] + (msg[i + 1] << 8)
            s += temp
            s = (s & 0xffff) + (s >> 16)
        return ~s & 0xffff
    
    @staticmethod
    def __mk_pkt(sq_num : bool, ack_num : bool, flags : int, msg : bytes) -> bytes:
        length = len(msg)
        csum = rdt.__chksum(struct.pack(_HEADER_FORMAT_NO_CHK, sq_num, ack_num, flags, length) + msg)
        return struct.pack(_HEADER_FORMAT, sq_num, ack_num, flags, length, csum) + msg

    @staticmethod
    def __unwrap_pkt(pkt : bytes):
        header = struct.unpack(_HEADER_FORMAT, pkt[0:_HEADER_LEN])
        msg = pkt[_HEADER_LEN:]
        return header, msg