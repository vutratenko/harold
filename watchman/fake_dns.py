import datetime
import sys
import time
import threading
import traceback
import socketserver
import struct
import json
from config import settings
import logging
from dns import resolver
import redis
from multiprocessing import Process
try:
    from dnslib import *
except ImportError:
    print("Missing dependency dnslib: <https://pypi.python.org/pypi/dnslib>. Please install it with `pip`.")
    sys.exit(2)


logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)


r = redis.Redis(host='localhost', port=6379, db=0)



class DomainName(str):
    def __getattr__(self, item):
        return DomainName(item + '.' + self)

def get_records(name):
    split_name = name.rsplit(".")[0]
    resolv = resolver.Resolver(filename='/etc/resolv.conf')
    try:
        logger.debug(f"Trying to resolve name { name } externally")
        answer = resolv.resolve(qname=name)
        for rr in answer.response.answer:
            for item in rr.items:
                return dict(name=name, ip=item.address)
    except (resolver.NXDOMAIN, resolver.NoAnswer) as err:            
        logger.debug(f"Failure. Trying to resolve name { name } internally")
        #logger.error(err)
        records_bytes = r.get('services')
        while True:
            if records_bytes is None:
                logger.debug("Got None from Redis")
                records_bytes = r.get('services')
            else:
                break
        records_json = records_bytes.decode("utf-8") 
        logger.debug(f"Got from Redis: { records_json }")
        records = json.loads(records_json)
        logger.debug("Created an object")
        for record in records:
            if split_name == record["name"]:
                logger.debug(f"Passed thru split")
                record["name"] = name
                logger.debug(f"Returning { str(record) }")
                return record
    logger.debug(f"Not resolved { name }")
    return dict(name="none.", ip="127.0.0.1")


def get_records_from_db(name):

    namedb = get_records(name)

    logger.debug(f"Got { namedb }")

    D = DomainName(namedb["name"])
    IP = namedb["ip"]
    TTL = 60 * 5

    soa_record = SOA(
        mname=D.ns1,  # primary name server
        rname=D.azaza,  # email of the domain administrator
        times=(
            201307231,  # serial number
            60 * 60 * 1,  # refresh
            60 * 60 * 3,  # retry
            60 * 60 * 24,  # expire
            60 * 60 * 1,  # minimum
        )
    )
    ns_records = [NS(D.ns1), NS(D.ns2)]
    records = {
        D: [A(IP)],
    }
    return D, TTL, soa_record, ns_records, records

def dns_response(data):
    request = DNSRecord.parse(data)

    reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q)

    qname = request.q.qname
    qn = str(qname)
    qtype = request.q.qtype
    qt = QTYPE[qtype]

    logger.debug(f"Full query is { qn }")

    #D, TTL, soa_record, ns_records, records = get_records_from_db(qn.rsplit(".")[0])

    D, TTL, soa_record, ns_records, records = get_records_from_db(qn)

    if qn == D or qn.endswith('.' + D):

        for name, rrs in records.items():
            if name == qn:
                for rdata in rrs:
                    rqt = rdata.__class__.__name__
                    if qt in ['*', rqt]:
                        reply.add_answer(RR(rname=qname, rtype=getattr(QTYPE, rqt), rclass=1, ttl=TTL, rdata=rdata))


    return reply.pack()


class BaseRequestHandler(socketserver.BaseRequestHandler):

    def get_data(self):
        raise NotImplementedError

    def send_data(self, data):
        raise NotImplementedError

    def handle(self):
        now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
        try:
            data = self.get_data()
            self.send_data(dns_response(data))
        except Exception:
            traceback.print_exc(file=sys.stderr)


class TCPRequestHandler(BaseRequestHandler):

    def get_data(self):
        data = self.request.recv(8192).strip()
        sz = struct.unpack('>H', data[:2])[0]
        if sz < len(data) - 2:
            raise Exception("Wrong size of TCP packet")
        elif sz > len(data) - 2:
            raise Exception("Too big TCP packet")
        return data[2:]

    def send_data(self, data):
        sz = struct.pack('>H', len(data))
        return self.request.sendall(sz + data)


class UDPRequestHandler(BaseRequestHandler):

    def get_data(self):
        return self.request[0]
#        return self.request[0].strip()

    def send_data(self, data):
        return self.request[1].sendto(data, self.client_address)

def main():
    logger.info("Starting nameserver...")

    servers = []
    if settings["dns_connection_type"] == "tcp": 
        servers.append(socketserver.ThreadingTCPServer(('', settings["dns_port"]), TCPRequestHandler))
    else:
        servers.append(socketserver.ThreadingUDPServer(('', settings["dns_port"]), UDPRequestHandler))


    for s in servers:
        thread = threading.Thread(target=s.serve_forever, name="DNS Server Thread")  # that thread will start one more thread for each request
        thread.daemon = True  # exit the server thread when the main thread terminates
        thread.start()
        logger.info("%s server loop running in thread: %s" % (s.RequestHandlerClass.__name__[:3], thread.name))

    try:
        while 1:
            time.sleep(1)
            sys.stderr.flush()
            sys.stdout.flush()

    except KeyboardInterrupt:
        pass
    finally:
        for s in servers:
            s.shutdown()

def run_dns_server():
    dns_server = Process(target=main, daemon=True, name="DNS Server")
    dns_server.start()