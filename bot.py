import os
import time
import threading
import requests
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Laster inn miljøvariabler
load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

app = App(token=SLACK_BOT_TOKEN)

# Trådstyring og globale tilstander
stop_event = threading.Event()
last_text = None
monitoring_thread = None
TARGET_URL = "https://www.norges-bank.no/"

def finn_styringsrente():
    url = "https://data.norges-bank.no/api/data/IR/B.KPRA.SD.R?format=csv&lastNObservations=1"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            lines = response.text.strip().splitlines()
            if len(lines) >= 2:
                # Siste linje inneholder nyeste observasjon
                data = lines[-1].split(";")
                rente_verdi = data[10].replace('"', '').strip()
                return f"Styringsrenten nå {rente_verdi}%"
    except Exception as e:
        print(f"❌ Feil ved henting fra Norges Bank API: {e}")
    return None

def monitor_loop(channel_id):
    global last_text
    print("🔁 Overvåking startet (stoppes automatisk etter 2 minutter)...")
    
    start_time = time.time()
    VARIGHET_SEKUNDER = 120  # 2 minutter (2 * 60 sekunder)
    SLEEP_INTERVAL = 3       # Sjekker hvert 3. sekund

    while not stop_event.is_set() and (time.time() - start_time < VARIGHET_SEKUNDER):
        rente_tekst = finn_styringsrente()
        if rente_tekst:
            if last_text is None:
                last_text = rente_tekst
            elif rente_tekst != last_text:
                app.client.chat_postMessage(
                    channel=channel_id,
                    text=f"🚨 *ENDRING I STYRINGSRENTEN!* 🚨\n\n```{rente_tekst}```\n\n<{TARGET_URL}|Åpne Norges Bank>"
                )
                last_text = rente_tekst
        
        # Vent i 3 sekunder, eller avbryt umiddelbart dersom stop_event blir satt
        stop_event.wait(SLEEP_INTERVAL)

    # Sjekk om løkken stoppet fordi tiden (2 minutter) gikk ut
    if not stop_event.is_set():
        stop_event.set()
        app.client.chat_postMessage(
            channel=channel_id,
            text="🛑 *Søk avsluttet (2 minutter har gått)*"
        )
        print("⏰ 2 minutter har gått. Søk avsluttet.")

@app.command("/sjekk-rente")
def handle_sjekk_rente(ack, respond):
    ack()
    respond("Sjekker Norges Bank... ⏳")
    rente_tekst = finn_styringsrente()
    if rente_tekst:
        respond(f"# 🏦 {rente_tekst}")
    else:
        respond("❌ Klarte ikke å hente status fra Norges Bank.")

@app.command("/ny-rente")
def handle_start(ack, respond, command):
    global monitoring_thread
    ack()
    
    # Sjekker om tråden allerede kjører
    if monitoring_thread and monitoring_thread.is_alive():
        respond("⚠️ Overvåking kjører allerede!")
        return

    stop_event.clear()
    channel_id = command['channel_id']
    monitoring_thread = threading.Thread(target=monitor_loop, args=(channel_id,))
    monitoring_thread.start()
    respond("🚀 *Overvåking startet!* Sjekker Norges Bank hvert 3. sekund i 2 minutter...")

@app.command("/stopp-overvaking")
def handle_stop(ack, respond):
    ack()
    if monitoring_thread and monitoring_thread.is_alive():
        stop_event.set()
        respond("🛑 Overvåking er slått av manuelt.")
    else:
        respond("⚠️ Det kjører ingen overvåking for øyeblikket.")

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    print("⚡️ RenteBot kjører og lytter på Slack!")
    handler.start()
