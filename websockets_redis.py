#!/usr/bin/python3
# python3 websockets_redis.py -wallet <btc_address>

import os, ssl
import argparse
from decimal import Decimal
import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import json

import logging
import logging.handlers
import os, time
 
handler = logging.handlers.WatchedFileHandler(
    os.environ.get("LOGFILE", "1.log"))
formatter = logging.Formatter(logging.BASIC_FORMAT)
handler.setFormatter(formatter)
root = logging.getLogger()
root.setLevel(os.environ.get("LOGLEVEL", "INFO"))
root.addHandler(handler)

import redis
r = redis.Redis(host='domain.com', port=31482, password='hunter2', db=0, decode_responses=True)

def on_message(ws, message):
    # Filter out pings
    ping = '{"type":"ping"}'
    success = '{"status":"success"}'
    if (message != ping):
        r.set(address, message)
        f = open(address + ".json", "w+")
        f.write(success)
        if (message != success): # Attempt to parse the message
            msg = json.loads(message)
            print(msg)
            try:
                AMOUNT_RECEIVED = Decimal(msg['data']['amount_received'])
                tx_id = msg['data']['txid']
                confirmations = msg['data']['confirmations']
                ret_address = msg['data']['address']
                f.write("\n" + str(AMOUNT_RECEIVED))
                r.set("___" + address, str(AMOUNT_RECEIVED))
                r.set("c_" + address, str(confirmations))
                r.set("t_" + address, str(tx_id))
                unix_time = int(time.time())
                r.set("l_" + address, unix_time)
                print(f'AMOUNT_RECEIVED: {AMOUNT_RECEIVED} ({confirmations} confirmations) txid: {tx_id} @ {unix_time}')
            except Exception as e:
                print(e)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    def run(*args):
        ws.send(
            '{"network": "' + network + '","type": "address","address": "' + address + '"}')
    thread.start_new_thread(run, ())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-wallet", help="wallet address")
    args = parser.parse_args()
    if (args.wallet):
        address = args.wallet
    else:
        address = "3B16kRBKdNYkrjHmc98Yjux8wDehu23b9B"

    websocket.enableTrace(False)
    # websocket.enableTrace(True)
    network = "BTC"    
    ws = websocket.WebSocketApp("wss://n.block.io/",
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close,
                              )
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})




