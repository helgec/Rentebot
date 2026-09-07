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
last_date = None
last_rate = None
monitoring_thread = None
TARGET_URL = "https://www.norges-bank.no/"

def finn_styringsrente():
    url = "https://data.norges-bank.no/api/data/IR/B.KPRA.SD.R?format=csv&lastNObservations=1"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            lines = response.text.strip().splitlines()
            if len(lines) >= 2:
                data = lines[-1].split(";")
                
                # Henter dato (TIME_PERIOD, indeks 8) og verdi (OBS_VALUE, indeks 10)
                dato = data[8].replace('"', '').strip()
                rente_verdi = data[10].replace('"', '').strip()
                
                return {"dato": dato, "verdi": rente_verdi}
    except Exception as e:
        print(f"❌ Feil ved henting fra Norges Bank API: {e}")
    return None

def monitor_loop(channel_id):
    global last_date, last_rate
    print("🔁 Overvåking startet (stoppes automatisk etter 2 minutter)...")
    
    start_time = time.time()
    VARIGHET_SEKUNDER = 120  # 2 minutter
    SLEEP_INTERVAL = 3       # 3 sekunder

    while not stop_event.is_set() and (time.time() - start_time < VARIGHET_SEKUNDER):
        data = finn_styringsrente()
        if data:
            ny_dato = data["dato"]
            ny_rente = data["verdi"]

            if last_date is None:
                # Første kjøring: sett baseline
                last_date = ny_dato
                last_rate = ny_rente
            elif ny_dato != last_date:
                # Ny dato registrert hos Norges Bank (ny rentebeslutning)
                uendret_tag = " (uendret)" if ny_rente == last_rate else ""
                melding = f"Styringsrente per {ny_dato}: {ny_rente}%{uendret_tag}"

                app.client.chat_postMessage(
                    channel=channel_id,
                    text=f"📢 *NY RENTEBESLUTNING FRA NORGES BANK!* 📢\n\n```{melding}```\n\n<{TARGET_URL}|Åpne Norges Bank>"
                )
                
                last_date = ny_dato
                last_rate = ny_rente

        stop_event.wait(SLEEP_INTERVAL)

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
    data = finn_styringsrente()
    if data:
        respond(f"# 🏦 Styringsrente per {data['dato']}: {data['verdi']}%")
    else:
        respond("❌ Klarte ikke å hente status fra Norges Bank.")

@app.command("/ny-rente")
def handle_start(ack, respond, command):
    global monitoring_thread
    ack()
    
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
