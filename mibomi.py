import getpass
import json
import os
import pprint

import mibomi.authenticator
import mibomi.client
import mibomi.enums

AUTH_DATA = 'auth.data'


def main():
    if os.path.isfile(AUTH_DATA):
        with open(AUTH_DATA) as file:
            access_token = file.readline().rstrip()
            client_token = file.readline().rstrip()
            profile_id = file.readline().rstrip()
    else:
        response = mibomi.authenticator.authenticate(
            input('Enter Mojang username (or email): '),
            getpass.getpass('Enter account password: ')
        )
        access_token = response.access_token
        client_token = response.client_token
        profile_id = response.selected_profile.id
        with open(AUTH_DATA, 'w') as f:
            f.write('\n'.join((
                access_token,
                client_token,
                profile_id
            )))

    print('The client token is', client_token)
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

    with mibomi.client.Client('localhost') as client:
        username = input('Enter player name: ')
        client.handshake(mibomi.enums.HandshakeState.LOGIN)
        client.login(username, access_token, profile_id)


if __name__ == '__main__':
    main()
