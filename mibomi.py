import pprint
import json

import mibomi.client
import mibomi.enums


def main():
    with mibomi.client.Client('localhost') as client:
        client.handshake(mibomi.enums.HandshakeState.STATUS)
        client.request()

        packet_id, data = client.recv()
        if packet_id == 0:
            packet = 'Response'
        else:
            packet = '?'

        print('Received packet ID: ', packet_id, ' (', packet, ')', sep='')
        print('JSON data:')
        pprint.pprint(json.loads(data.readstr()))


if __name__ == '__main__':
    main()
