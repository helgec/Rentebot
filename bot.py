import re
import os
import time
import threading
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv  # 👈 Importerer dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Laster inn variablene fra .env-filen lokalt
load_dotenv()

# Henter hemmelighetene trygt fra miljøvariabler
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

app = App(token=SLACK_BOT_TOKEN)

is_monitoring = False
last_text = None
monitoring_thread = None
TARGET_URL = "https://www.norges-bank.no/"

def finn_styringsrente():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cache-Control": "no-cache"
    }
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for el in soup.find_all(True):
                if 'Styringsrenten' in el.text:
                    tekst = el.get_text(separator=" ", strip=True)
                    # Henter KUN "Styringsrenten nå X,XX%" og kaster resten av teksten
                    match = re.search(r"(Styringsrenten\s+nå\s+\d+[\.,]\d+\s*%)", tekst, re.IGNORECASE)
                    if match:
                        return match.group(1)
    except Exception as e:
        print(f"❌ Feil ved tilkobling til Norges Bank: {e}")
        
    return None

def monitor_loop(channel_id):
    global is_monitoring, last_text
    print("🔁 Overvåking startet (stoppes automatisk etter 10 minutter)...")
    
    start_time = time.time()
    VARIGHET_SEKUNDER = 600  # 10 minutter (10 * 60)
    
    while is_monitoring and (time.time() - start_time < VARIGHET_SEKUNDER):
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
        time.sleep(3)
    
    # Sjekk om løkken stoppet fordi tiden gikk ut (og ikke fordi den ble stoppet manuelt)
    if is_monitoring:
        is_monitoring = False
        app.client.chat_postMessage(
            channel=channel_id,
            text="🛑 *Søk avsluttet*"
        )
        print("⏰ 10 minutter har gått. Søk avsluttet.")

@app.command("/sjekk-rente")
def handle_sjekk_rente(ack, respond):
    ack()
    respond("Sjekker Norges Bank... ⏳")
    rente_tekst = finn_styringsrente()
    if rente_tekst:
        # '#' foran gjør teksten stor i Slack
        respond(f"# 🏦 {rente_tekst}")
    else:
        respond("❌ Klarte ikke å hente status fra Norges Bank.")

@app.command("/ny-rente")
def handle_start(ack, respond, command):
    global is_monitoring, monitoring_thread
    ack()
    if is_monitoring:
        respond("⚠️ Overvåking kjører allerede!")
        return

    is_monitoring = True
    channel_id = command['channel_id']
    monitoring_thread = threading.Thread(target=monitor_loop, args=(channel_id,))
    monitoring_thread.start()
    respond("🚀 *# Overvåking startet!* Sjekker Norges Bank hvert 3. sekund...")

@app.command("/stopp-overvaking")
def handle_stop(ack, respond):
    global is_monitoring
    ack()
    is_monitoring = False
    respond("🛑 Overvåking er slått av.")

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    print("⚡️ RenteBot kjører og lytter på Slack!")
    handler.start()
