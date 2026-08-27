import time
import urllib.request
import json
import sys

try:
    from smartcard.CardMonitoring import CardMonitor, CardObserver
    from smartcard.util import toHexString
except ImportError:
    print("Please install pyscard: sudo apt-get install python3-pyscard")
    sys.exit(1)

class PrintObserver(CardObserver):
    def update(self, observable, actions):
        (addedcards, removedcards) = actions
        for card in addedcards:
            try:
                card.connection = card.createConnection()
                card.connection.connect()
                # APDU to get UID (Standard ISO 14443-A)
                data, sw1, sw2 = card.connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
                if sw1 == 0x90 and sw2 == 0x00:
                    uid = toHexString(data).replace(" ", "")
                    print(f"Card inserted: {uid}")
                    try:
                        # Send to local API
                        
                        req = urllib.request.Request('http://localhost:8000/api/scans/pending', data=json.dumps({"card_id": uid}).encode('utf-8'), headers={'Content-Type': 'application/json'})
                        urllib.request.urlopen(req, timeout=2)

                    except Exception as e:
                        print(f"API Error: {e}")
            except Exception as e:
                print(f"Error connecting to card: {e}")
        for card in removedcards:
            print("Card removed")

def main():
    cardmonitor = CardMonitor()
    cardobserver = PrintObserver()
    cardmonitor.addObserver(cardobserver)
    print("Listening for CAC taps... (Press Ctrl+C to exit)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cardmonitor.deleteObserver(cardobserver)

if __name__ == '__main__':
    main()
