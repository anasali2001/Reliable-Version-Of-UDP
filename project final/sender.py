from rdt import rdt
from argparse import ArgumentParser

def send(sen_addr, rec_addr, pkt_count, pkt_size):
    msg = 'A'*18 + 'B'*18 + 'C'*18 + 'D'*18 + 'E'*18

    skt = rdt(pkt_size)
    skt.send(msg.encode('utf-8'), rec_addr)
    # try:
    #     # for i in range(pkt_count):
    # except Exception as e:
    #     print(e.args)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('recver_ip')
    parser.add_argument('recver_port')
    parser.add_argument('count') # count of packets to send
    parser.add_argument('size') # size of packets to send
    parser.add_argument('-p') # local port
    args = parser.parse_args()

    rec_ip = args.recver_ip
    rec_port =  int(args.recver_port)
    if args.p:
        sen_port = int(args.p)
    else:
        sen_port = 8080

    rec_addr = (rec_ip, rec_port)
    sen_addr = ('localhost', sen_port)
    pkt_size = int(args.size)
    pkt_count = int(args.count)
    send(sen_addr, rec_addr, pkt_count, pkt_size)