import os
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

last_scanned_card = None
last_scanned_time = 0.0

class PrintObserver(CardObserver):
    def update(self, observable, actions):
        global last_scanned_card, last_scanned_time
        (addedcards, removedcards) = actions
        for card in addedcards:
            try:
                card.connection = card.createConnection()
                card.connection.connect()
                # APDU to get UID (Standard ISO 14443-A)
                data, sw1, sw2 = card.connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
                if sw1 == 0x90 and sw2 == 0x00:
                    uid = toHexString(data).replace(" ", "")
                    now = time.time()
                    if uid == last_scanned_card and (now - last_scanned_time) < 1.2:
                        print(f"Duplicate card tap ignored (debounced): {uid}")
                        continue
                    last_scanned_card = uid
                    last_scanned_time = now
                    print(f"Card inserted: {uid}")
                    # Guarantee kiosk window on Display 1 is active/focused in X11
                    os.system('DISPLAY=:0 xdotool search --classname "chromium-display1" windowactivate 2>/dev/null &')
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
