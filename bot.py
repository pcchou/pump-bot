from flask import Flask, request
import requests
from datetime import datetime, timedelta
from threading import Timer
import logging
from requests.adapters import HTTPAdapter, Retry

key = ""
app = Flask(__name__)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

s = requests.Session()
retries = Retry(total=16, connect=8, backoff_factor=0.5)
s.mount('http://', HTTPAdapter(max_retries=retries))

CHAT_ID0 = "" # Owner's ID
CHAT_ID1 = "" # Group
CHAT_IDs = [""] # allowed id
HOST = '0.0.0.0:8888'

last_on = datetime.now()
on_mins = 10
on_time = timedelta(minutes=on_mins)

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
    #send(CHAT_ID1, "ESP32 Connected!")
    logging.info("ESP32 Connected!")
    return str(state)

@app.route("/timesup",methods=["GET"])
def timesup(local=False):
    global state
    if local:
        send(CHAT_ID0, "Time's up! State set to OFF.")
        logging.info("Time's up! State set to OFF.")
    else:
        send(CHAT_ID0, "Time's up! State set to OFF by ESP32.")
        logging.info("Time's up! State set to OFF by ESP32.")
    state = False
    return "Sent!"

@app.route("/switchon",methods=["GET"])
def switchon():
    global state, last_on, timer
    send(CHAT_ID0, "Pump set to ON by switch.")
    logging.info("Pump set to ON by switch.")
    state = True
    last_on = datetime.now()
    if isinstance(timer, Timer):
        timer.cancel()
    timer = Timer(on_time.seconds, timesup_local)
    timer.start()
    return "Sent!"

@app.route("/switchoff",methods=["GET"])
def switchoff():
    global state
    send(CHAT_ID0, "Pump set to OFF by switch.")
    logging.info("Pump set to OFF by switch.")
    state = False
    if isinstance(timer, Timer):
        timer.cancel()
    return "Sent!"

def timesup_local():
    logging.debug("The local timer has gone off!")
    resp = s.get(f'http://{HOST}/L')
    logging.debug(resp.text)
    timesup(local=True)

@app.route("/",methods=["POST", "GET"])
def index():
    global state, last_on, timer
    if(request.method == "POST"):
        resp = request.get_json()

        if "message" not in resp:
            return "QQ"

        chatid = resp["message"]["chat"]["id"]

        if str(chatid) not in [CHAT_ID0, CHAT_ID1] + CHAT_IDs:
            send(chatid, 'Unauthorized user!')
            return "Done"

        try:
            msgtext = resp["message"]["text"]
            logger.debug("Text: " + msgtext)
            sendername = resp["message"]["from"]["first_name"]
            logger.debug("Name: " + sendername)
        except:
            print(resp)
            msgtext = ""

        if msgtext.startswith("/pump_on"):
            resp = s.get(f'http://{HOST}/H')
            logging.debug(resp.text)
            state = True
            last_on = datetime.now()
            if isinstance(timer, Timer):
                timer.cancel()
            timer = Timer(on_time.seconds, timesup_local)
            timer.start()
            send(chatid, f'Set pump to ON for {on_mins} minutes.')
            logging.info('State set to ON.')
        elif msgtext.startswith("/pump_off"):
            resp = s.get(f'http://{HOST}/L')
            logging.debug(resp.text)
            state = False
            if isinstance(timer, Timer):
                timer.cancel()
            send(chatid, 'Pump set to OFF.')
            logging.info('State set to OFF.')
        elif msgtext.startswith("/state"):
            resp = s.get(f'http://{HOST}/')
            status = resp.text.replace('\r\n', '')
            if status.isnumeric():
                state = True
            else: # status == "OFF":
                state = False

            if state == True:
                timeleft = (on_time - timedelta(seconds=int(status)/1000))
                if timeleft.days < 0:
                    timeleft = "0.0"
                else:
                    timeleft = f'{timeleft.seconds / 60:.1f}'
                send(chatid, f'Pump is ON, {timeleft} minutes left.')
            else:
                send(chatid, "Pump is OFF.")

        return "Done"
    return "Hi!"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8087)

