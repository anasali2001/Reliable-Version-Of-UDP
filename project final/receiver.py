from rdt import rdt
from argparse import ArgumentParser

def recv(rec_addr, pkt_size):
    skt = rdt(pkt_size)
    skt.bind(rec_addr)
    while True:
        msg, ret_addr = skt.recv()
        print('received', msg.decode("utf-8"), 'from', ret_addr)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('size') # size of packets to send
    parser.add_argument('-p') # local port
    args = parser.parse_args()

    rec_ip = 'localhost'
    if args.p:
        rec_port = int(args.p)
    else:
        rec_port = 8081

    rec_addr = (rec_ip, rec_port)
    pkt_size = int(args.size)
    #sen_addr = ('localhost', 8081)
    recv(rec_addr, pkt_size)