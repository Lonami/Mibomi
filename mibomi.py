import getpass
import json
import os
import pprint

import mibomi.authenticator
import mibomi.client
import mibomi.enums

ACCESS_TOKEN = 'access.token'


def main():
    if os.path.isfile(ACCESS_TOKEN):
        with open(ACCESS_TOKEN) as file:
            access_token = file.read().strip()
    else:
        response = mibomi.authenticator.authenticate(
            input('Enter Mojang username (or email): '),
            getpass.getpass('Enter account password: ')
        )
        access_token = response.access_token
        print('The client token is', response.client_token)
        with open(ACCESS_TOKEN, 'w') as f:
            f.write(response.access_token)

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
