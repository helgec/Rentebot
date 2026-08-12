import time
import threading
import requests
from bs4 import BeautifulSoup
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# 🛑 LIM INN DINE NØKLER HER:
SLACK_BOT_TOKEN = "SLACK_BOT_TOKEN"
SLACK_APP_TOKEN = "SLACK_APP_TOKEN"

app = App(token=SLACK_BOT_TOKEN)

is_monitoring = False
last_text = None
monitoring_thread = None
TARGET_URL = "https://www.norges-bank.no/"

def finn_styringsrente():
    try:
        response = requests.get(TARGET_URL, headers={"Cache-Control": "no-cache"}, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for el in soup.find_all(True):
                if 'Styringsrenten nå' in el.text and len(el.children) > 0:
                    return el.get_text(separator=" ", strip=True)
    except Exception as e:
        print(f"Feil ved henting: {e}")
    return None

def monitor_loop(channel_id):
    global is_monitoring, last_text
    print("🔁 Overvåking startet i bakgrunnen...")
    
    while is_monitoring:
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

@app.command("/sjekk-rente")
def handle_sjekk_rente(ack, respond):
    ack()
    respond("Sjekker Norges Bank... ⏳")
    rente_tekst = finn_styringsrente()
    if rente_tekst:
        respond(f"📊 *Status fra Norges Bank akkurat nå:*\n```{rente_tekst}```")
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
    respond("🚀 *Overvåking startet!* Sjekker Norges Bank hvert 3. sekund...")

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