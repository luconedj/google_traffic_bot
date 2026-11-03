import json
import os
import re
import signal
import sys
import time
import urllib.parse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

# ================= CONFIGURAZIONE DA HOME ASSISTANT =================
options = {}
if os.path.exists("/data/options.json"):
  try:
    with open("/data/options.json", "r") as f:
      options = json.load(f)
  except Exception as e:
    print(f"[CONFIG] Errore lettura /data/options.json: {e}")

ORIGIN = options.get("origin", os.getenv("ORIGIN", ""))
DESTINATION = options.get("destination", os.getenv("DESTINATION", ""))

CHECK_INTERVAL_MINUTES = int(options.get("check_interval_minutes", os.getenv("CHECK_INTERVAL_MINUTES", 10)))
DIFF_THRESHOLD_MINUTES = int(options.get("diff_threshold_minutes", os.getenv("DIFF_THRESHOLD_MINUTES", 5)))
FREE_TRAFFIC_THRESHOLD_MINUTES = int(options.get("free_traffic_threshold_minutes", os.getenv("FREE_TRAFFIC_THRESHOLD_MINUTES", 35)))

enable_tel_val = options.get("enable_telegram", os.getenv("ENABLE_TELEGRAM", False))
if isinstance(enable_tel_val, str):
  ENABLE_TELEGRAM = enable_tel_val.lower() in ("true", "1", "yes", "on")
else:
  ENABLE_TELEGRAM = bool(enable_tel_val)

TELEGRAM_BOT_TOKEN = options.get("telegram_bot_token", os.getenv("TELEGRAM_BOT_TOKEN", ""))
TELEGRAM_CHAT_ID = options.get("telegram_chat_id", os.getenv("TELEGRAM_CHAT_ID", ""))
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")
# =========================================================================

STATE_PATH = "/data/browser_state.json"
SCREENSHOT_PATH = "/share/traffic_debug.png"

# Risorse pesanti non necessarie: la durata è testo nel DOM
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-sync",
    "--no-first-run",
    "--mute-audio",
    "--disable-blink-features=AutomationControlled",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

last_duration = None


def send_telegram_notification(message):
  if not ENABLE_TELEGRAM or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    return

  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  try:
    response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=5)
    if not response.ok:
      print(f"Errore invio Telegram: {response.text}")
  except Exception as e:
    print(f"Errore di connessione a Telegram: {e}")


def update_ha_sensor(duration):
  if not SUPERVISOR_TOKEN:
    print("[HA API] SUPERVISOR_TOKEN non trovato. Aggiornamento HA saltato.")
    return

  url = "http://supervisor/core/api/states/sensor.traffico_napoli_caserta"
  headers = {
      "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
      "Content-Type": "application/json",
  }

  payload = {
      "state": duration if duration is not None else "unavailable",
      "attributes": {
          "unit_of_measurement": "min",
          "friendly_name": "Tratta Monitorata (Traffico)",
          "icon": "mdi:car-clock",
          "bot_status": "Attivo",
          "origin": ORIGIN,
          "destination": DESTINATION,
      },
  }

  try:
    response = requests.post(url, json=payload, headers=headers, timeout=5)
    if not response.ok:
      print(f"[HA API] Errore aggiornamento sensore: {response.status_code}")
  except Exception as e:
    print(f"[HA API] Eccezione di rete verso Home Assistant: {e}")


def clean_text(text):
  if not text:
    return ""
  cleaned = "".join(c for c in text if not (0xE000 <= ord(c) <= 0xF8FF))
  return cleaned.strip()


def parse_duration_to_minutes(text):
  cleaned_text = clean_text(text)
  if not cleaned_text:
    return None

  total_minutes = 0
  hours_match = re.search(r"(\d+)\s*(?:ora|ore|h)", cleaned_text, re.IGNORECASE)
  if hours_match:
    total_minutes += int(hours_match.group(1)) * 60

  mins_match = re.search(r"(\d+)\s*(?:min|m)", cleaned_text, re.IGNORECASE)
  if mins_match:
    total_minutes += int(mins_match.group(1))

  return total_minutes if total_minutes > 0 else None


def save_debug_screenshot(page):
  try:
    os.makedirs("/share", exist_ok=True)
    page.screenshot(path=SCREENSHOT_PATH)
    print(f"Screenshot salvato in {SCREENSHOT_PATH}")
  except Exception as e:
    print(f"Screenshot fallito: {e}")


def block_heavy_resources(route):
  if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
    route.abort()
  else:
    route.continue_()


def get_traffic_duration(page):
  if not ORIGIN or not DESTINATION:
    print("[ERRORE] Indirizzo di partenza o arrivo non configurati in Home Assistant!")
    return None

  encoded_origin = urllib.parse.quote(ORIGIN)
  encoded_dest = urllib.parse.quote(DESTINATION)
  url = f"https://www.google.com/maps/dir/{encoded_origin}/{encoded_dest}?hl=it"

  print(f"[{datetime.now().strftime('%H:%M:%S')}] Apertura Google Maps in corso...")
  try:
    page.goto(url, timeout=60000, wait_until="domcontentloaded")
  except Exception as e:
    print(f"Errore di navigazione Playwright: {e}")
    return None

  print(f"URL raggiunto: {page.url}")

  # Banner cookie / consenso (anche su consent.google.com)
  try:
    btn = page.locator(
        "button:has-text('Accetta tutto'), "
        "button[aria-label='Accetta tutto'], "
        "button:has-text('Accept all')"
    ).first
    btn.wait_for(state="visible", timeout=5000)
    btn.click()
    print("Banner cookie chiuso con successo.")
    page.wait_for_load_state("domcontentloaded", timeout=30000)
  except Exception:
    pass  # nessun banner presente

  try:
    page.wait_for_selector("div.ivN21e, div.tUEPjf, div[data-trip-index]", timeout=15000)

    duration_elements = page.locator(
        "div[data-trip-index] div.Fk3nvb, div.ivN21e, div.tUEPjf, span[jsan*='7.fontHeadlineLarge']"
    ).all_inner_texts()

    if not duration_elements:
      duration_elements = page.locator("span:has-text('min'), div:has-text('min')").all_inner_texts()

    for text in duration_elements:
      cleaned = clean_text(text)
      if (
          len(cleaned) < 25
          and ("min" in cleaned.lower() or "h" in cleaned.lower())
          and "partenza" not in cleaned.lower()
          and "arrivo" not in cleaned.lower()
      ):
        mins = parse_duration_to_minutes(cleaned)
        if mins:
          print(f"Tempo rilevato con successo: '{cleaned}' -> {mins} minuti")
          return mins

    time_text = page.evaluate(
        """() => {
            const elements = Array.from(document.querySelectorAll('div, span'));
            const match = elements.find(el => el.innerText && (el.innerText.includes('min') || el.innerText.includes('ora')) && el.innerText.length < 15 && !el.innerText.includes('partenza'));
            return match ? match.innerText : null;
        }"""
    )
    if time_text:
      cleaned_js = clean_text(time_text)
      mins = parse_duration_to_minutes(cleaned_js)
      if mins:
        print(f"Tempo rilevato via JS fallback: '{cleaned_js}' -> {mins} minuti")
        return mins

    print("[AVVISO] Nessun elemento della durata trovato nel DOM.")
  except Exception as e:
    print(f"Errore durante il recupero dei dati da Google Maps: {e}")

  save_debug_screenshot(page)
  return None


def fetch_duration():
  """Avvia Chromium, legge il tempo e chiude tutto: a riposo la RAM resta libera."""
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=CHROMIUM_ARGS)
    try:
      ctx_kwargs = {
          "locale": "it-IT",
          "user_agent": USER_AGENT,
          "viewport": {"width": 1280, "height": 800},
      }

      # Riusa il consenso cookie salvato (se il file è valido)
      if os.path.exists(STATE_PATH):
        try:
          with open(STATE_PATH, "r") as f:
            json.load(f)
          ctx_kwargs["storage_state"] = STATE_PATH
        except Exception:
          os.remove(STATE_PATH)

      context = browser.new_context(**ctx_kwargs)
      context.route("**/*", block_heavy_resources)
      page = context.new_page()

      duration = get_traffic_duration(page)

      if duration is not None:
        try:
          context.storage_state(path=STATE_PATH)
        except Exception:
          pass

      return duration
    finally:
      browser.close()


def job_check_traffic():
  global last_duration

  current_time = datetime.now().strftime("%H:%M")
  current_duration = fetch_duration()

  if current_duration is not None:
    print(f"[{current_time}] Durata attuale stimata: {current_duration} min")

    update_ha_sensor(current_duration)

    if last_duration is not None:
      diff = current_duration - last_duration

      if abs(diff) >= DIFF_THRESHOLD_MINUTES:
        direction = "aumentato" if diff > 0 else "diminuito"
        msg = (
            f"⚠️ Attenzione! Il traffico è {direction} di {abs(diff)} min.\n"
            f"🕒 Tempo attuale: {current_duration} min (precedente: {last_duration} min)."
        )
        send_telegram_notification(msg)
      elif (
          current_duration <= FREE_TRAFFIC_THRESHOLD_MINUTES
          and last_duration > FREE_TRAFFIC_THRESHOLD_MINUTES
      ):
        send_telegram_notification(
            f"🟢 Percorso libero! Il tempo di percorrenza è sceso a {current_duration} min."
        )
    else:
      send_telegram_notification(
          f"🤖 Bot Add-on avviato. Monitoraggio attivo. Tempo iniziale: {current_duration} min."
      )

    last_duration = current_duration
  else:
    print(f"[{current_time}] Impossibile leggere il tempo di traffico.")

  print(f"Prossimo controllo pianificato tra {CHECK_INTERVAL_MINUTES} minuti.\n")


def main():
  signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

  print("--- Avvio Google Maps Traffic Bot (HA Local Add-on) ---")
  print(f"Partenza: {ORIGIN if ORIGIN else '[Non configurata]'}")
  print(f"Arrivo:   {DESTINATION if DESTINATION else '[Non configurata]'}")
  print(f"Intervallo: {CHECK_INTERVAL_MINUTES} minuti")
  print(f"Telegram abilitato: {ENABLE_TELEGRAM}\n")

  send_telegram_notification("🤖 Bot Traffico Add-on avviato in Home Assistant!")

  interval_seconds = CHECK_INTERVAL_MINUTES * 60

  while True:
    started = time.time()
    try:
      job_check_traffic()
    except Exception as e:
      print(f"[ERRORE] Controllo fallito: {e}")

    time.sleep(max(5, interval_seconds - (time.time() - started)))


if __name__ == "__main__":
  main()
