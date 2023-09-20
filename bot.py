from flask import Flask, request
import requests
from datetime import datetime, timedelta
from threading import Timer
import logging

key = ""
app = Flask(__name__)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

CHAT_ID0 = "" # Owner's ID
CHAT_ID1 = "" # Target group's ID

HOST = "0.0.0.0:8888" # Arduino bot host address:port

last_on = datetime.now()
on_time = timedelta(minutes=1)

timer = None

state = False

def send(chatid, msg):
    url = "https://api.telegram.org/bot{}/sendMessage".format(key)
    payload = {
        "text": msg,
        "chat_id": chatid
        }

    resp = requests.get(url, params=payload)
    logger.debug(resp.text)

@app.route("/online",methods=["GET"])
def online():
    global state
    send(CHAT_ID0, "ESP32 Connected!")
    send(CHAT_ID1, "ESP32 Connected!")
    logging.info("ESP32 Connected!")
    state = False
    return "Sent!"

@app.route("/timesup",methods=["GET"])
def timesup():
    global state
    send(CHAT_ID0, "Time's up! State set to OFF.")
    logging.info("Time's up! State set to OFF.")
    state = False
    return "Sent!"

@app.route("/switchon",methods=["GET"])
def switchon():
    global state, last_on, timer
    send(CHAT_ID0, "Set pump to ON by switch.")
    logging.info("Set pump to ON by switch.")
    state = True
    last_on = datetime.now()
    timer = Timer(on_time.seconds, timesup_local)
    timer.start()
    return "Sent!"

@app.route("/switchoff",methods=["GET"])
def switchoff():
    global state
    send(CHAT_ID0, "Set pump to OFF by switch.")
    logging.info("Set pump to OFF by switch.")
    state = False
    return "Sent!"

def timesup_local():
    resp = requests.get(f'http://{HOST}/L')
    logging.debug(resp.text)
    timesup()

@app.route("/",methods=["POST", "GET"])
def index():
    global state, last_on
    if(request.method == "POST"):
        resp = request.get_json()

        chatid = resp["message"]["chat"]["id"]

        if str(chatid) not in (CHAT_ID0, CHAT_ID1):
            send(chatid, 'Unauthorized user!')
            return "Done"

        msgtext = resp["message"]["text"]
        logger.debug("Text: " + msgtext)
        sendername = resp["message"]["from"]["first_name"]
        logger.debug("Name: " + sendername)

        if msgtext.startswith("/pump_on"):
            resp = requests.get(f'http://{HOST}/H')
            logging.debug(resp.text)
            state = True
            last_on = datetime.now()
            Timer(on_time.seconds, timesup_local).start()
            send(chatid, 'State set to ON.')
            logging.info('State set to ON.')
        elif msgtext.startswith("/pump_off"):
            resp = requests.get(f'http://{HOST}/L')
            logging.debug(resp.text)
            state = False
            send(chatid, 'State set to OFF.')
            logging.info('State set to OFF.')
        elif msgtext.startswith("/state"):
            if state == True:
                if (last_on + on_time - datetime.now()).days < 0:
                    timeleft = "0.0"
                else:
                    timeleft = f'{(last_on + on_time - datetime.now()).seconds / 60:.1f}'
                send(chatid, f'Pump is ON, {timeleft} minutes left.')
            else:
                send(chatid, "Pump is OFF.")

        return "Done"
    return "Hi!"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
