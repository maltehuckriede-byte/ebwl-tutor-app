import streamlit as st
from groq import Groq
import os
import json
import random
import re
import time
import base64

# --- 1. SETUP & API ---
st.set_page_config(page_title="Wolf of Wüllnerstraße - Quiz", page_icon="🐺", layout="wide")

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --- 2. DIE FAHRZEUG-DATENBANK ---
# WICHTIG: Füge hier deinen kompletten KARTEN_KATALOG mit allen Fahrzeugen ein!
KARTEN_KATALOG = {
    # --- COMMON (GRAU) ---
    "VW Golf VIII GTI": {"klasse": "C1", "staerke": "45", "kennzeichen": "GOLF-GTI", "rarity": "Common (Grau)", "daten": {"Modell": "GTI Performance", "⚡ Leistung": "180 kW (245 PS)", "🕒 0–100 km/h": "6,2 s", "🏁 V-Max": "250 km/h"}},
    "Opel Corsa F Elektro": {"klasse": "D2", "staerke": "20", "kennzeichen": "CORSA-E", "rarity": "Common (Grau)", "daten": {"Modell": "Pre-Facelift 2021", "⚡ Leistung": "100 kW (136 PS)", "🔋 Reichweite": "330 km", "⚖️ Gewicht": "1.530 kg"}},
    "Ford Fiesta ST": {"klasse": "C1", "staerke": "40", "kennzeichen": "FIESTA", "rarity": "Common (Grau)", "daten": {"Modell": "ST", "⚡ Leistung": "147 kW (200 PS)", "🕒 0–100 km/h": "6,5 s", "🏁 V-Max": "230 km/h"}},
    "Toyota GR Yaris": {"klasse": "C1", "staerke": "55", "kennzeichen": "YARIS-GR", "rarity": "Common (Grau)", "daten": {"Modell": "Gazoo Racing", "⚡ Leistung": "192 kW (261 PS)", "⚙️ Antrieb": "Allrad (GR-FOUR)", "🕒 0–100 km/h": "5,5 s"}},
    "Honda Civic Type R": {"klasse": "C1", "staerke": "65", "kennzeichen": "TYPE-R", "rarity": "Common (Grau)", "daten": {"Modell": "FL5", "⚡ Leistung": "242 kW (329 PS)", "🕒 0–100 km/h": "5,4 s", "🏁 V-Max": "275 km/h"}},
    "Yamaha MT-07": {"klasse": "M1", "staerke": "30", "kennzeichen": "MT-07", "rarity": "Common (Grau)", "daten": {"Typ": "Naked Bike", "⚡ Leistung": "54 kW (73 PS)", "🕒 0–100 km/h": "3,8 s", "⚖️ Gewicht": "184 kg"}},
    "Kawasaki Ninja 400": {"klasse": "M1", "staerke": "20", "kennzeichen": "NINJA400", "rarity": "Common (Grau)", "daten": {"Typ": "Supersport", "⚡ Leistung": "33 kW (45 PS)", "🕒 0–100 km/h": "4,8 s", "🏁 V-Max": "180 km/h"}},

    # --- RARE (BLAU) ---
    "BMW M3 Competition": {"klasse": "B1", "staerke": "80", "kennzeichen": "M3-COMP", "rarity": "Rare (Blau)", "daten": {"Modell": "G80", "⚡ Leistung": "375 kW (510 PS)", "🕒 0–100 km/h": "3,9 s", "🏁 V-Max": "290 km/h"}},
    "Audi RS4 Avant": {"klasse": "B1", "staerke": "75", "kennzeichen": "RS4-AV", "rarity": "Rare (Blau)", "daten": {"Modell": "B9", "⚡ Leistung": "331 kW (450 PS)", "⚙️ Antrieb": "quattro", "🕒 0–100 km/h": "4,1 s"}},
    "Mercedes-AMG C 63": {"klasse": "B1", "staerke": "80", "kennzeichen": "AMG-C63", "rarity": "Rare (Blau)", "daten": {"Modell": "W205 (V8)", "⚡ Leistung": "375 kW (510 PS)", "🕒 0–100 km/h": "4,0 s", "🔊 Motor": "4.0L V8 Biturbo"}},
    "Tesla Model 3 Performance": {"klasse": "E1", "staerke": "85", "kennzeichen": "MODEL-3", "rarity": "Rare (Blau)", "daten": {"Modell": "Dual Motor", "⚡ Leistung": "393 kW (534 PS)", "🕒 0–100 km/h": "3,3 s", "🔋 Reichweite": "547 km"}},
    "Kawasaki Z900": {"klasse": "M2", "staerke": "45", "kennzeichen": "Z-900", "rarity": "Rare (Blau)", "daten": {"Typ": "Naked Bike", "⚡ Leistung": "92 kW (125 PS)", "🕒 0–100 km/h": "3,2 s", "🏁 V-Max": "240 km/h"}},
    "Ducati Monster": {"klasse": "M2", "staerke": "45", "kennzeichen": "MONSTER", "rarity": "Rare (Blau)", "daten": {"Typ": "Naked Bike", "⚡ Leistung": "82 kW (111 PS)", "🕒 0–100 km/h": "3,2 s", "⚖️ Gewicht": "188 kg"}},
    "KTM 890 Duke R": {"klasse": "M2", "staerke": "50", "kennzeichen": "DUKE-890", "rarity": "Rare (Blau)", "daten": {"Typ": "Super Scalpel", "⚡ Leistung": "89 kW (121 PS)", "🕒 0–100 km/h": "3,0 s", "⚖️ Gewicht": "166 kg"}},

    # --- EPIC (LILA) ---
    "Porsche 911 GT3": {"klasse": "S1", "staerke": "95", "kennzeichen": "GT3-992", "rarity": "Epic (Lila)", "daten": {"Modell": "Generation 992", "⚡ Leistung": "375 kW (510 PS)", "🕒 0–100 km/h": "3,4 s", "🏁 V-Max": "318 km/h"}},
    "Audi R8 V10": {"klasse": "S1", "staerke": "90", "kennzeichen": "R8-V10", "rarity": "Epic (Lila)", "daten": {"Modell": "Performance", "⚡ Leistung": "456 kW (620 PS)", "🕒 0–100 km/h": "3,1 s", "🏁 V-Max": "331 km/h"}},
    "McLaren 720S": {"klasse": "S2", "staerke": "98", "kennzeichen": "MAC-720", "rarity": "Epic (Lila)", "daten": {"Modell": "Coupé", "⚡ Leistung": "530 kW (720 PS)", "🕒 0–100 km/h": "2,9 s", "🏁 V-Max": "341 km/h"}},
    "Honda NC 700S (Custom)": {"klasse": "M1", "staerke": "50", "kennzeichen": "NC-700", "rarity": "Epic (Lila)", "daten": {"Typ": "Naked Bike", "⚡ Leistung": "35 kW (48 PS)", "⚙️ Drehmoment": "60 Nm", "📦 Feature": "Helmfach im Tank"}},
    "BMW S 1000 RR": {"klasse": "M3", "staerke": "85", "kennzeichen": "S1000RR", "rarity": "Epic (Lila)", "daten": {"Typ": "Superbike", "⚡ Leistung": "154 kW (210 PS)", "🕒 0–100 km/h": "3,1 s", "🏁 V-Max": "303 km/h"}},
    "Ducati Panigale V4": {"klasse": "M3", "staerke": "88", "kennzeichen": "PANI-V4", "rarity": "Epic (Lila)", "daten": {"Typ": "Superbike", "⚡ Leistung": "158 kW (215 PS)", "🕒 0–100 km/h": "3,0 s", "🏁 V-Max": "300 km/h"}},

    # --- LEGENDARY (GOLD) ---
    "Bugatti Chiron": {"klasse": "H1", "staerke": "100", "kennzeichen": "CHIRON", "rarity": "Legendary (Gold)", "daten": {"Modell": "W16", "⚡ Leistung": "1103 kW (1500 PS)", "🕒 0–100 km/h": "2,4 s", "🏁 V-Max": "420 km/h"}},
    "Ferrari LaFerrari": {"klasse": "H1", "staerke": "99", "kennzeichen": "LAFERRARI", "rarity": "Legendary (Gold)", "daten": {"Modell": "F150", "⚡ Leistung": "708 kW (963 PS)", "🕒 0–100 km/h": "2,6 s", "🏁 V-Max": "350 km/h"}},
    "Koenigsegg Jesko": {"klasse": "H1", "staerke": "100", "kennzeichen": "JESKO", "rarity": "Legendary (Gold)", "daten": {"Modell": "Attack", "⚡ Leistung": "1195 kW (1625 PS)", "🕒 0–100 km/h": "2,5 s", "🏁 V-Max": "480 km/h"}},
    "Kawasaki Ninja H2R": {"klasse": "M4", "staerke": "100", "kennzeichen": "H2R", "rarity": "Legendary (Gold)", "daten": {"Typ": "Track-Only", "⚡ Leistung": "228 kW (310 PS)", "🕒 0–100 km/h": "2,6 s", "🏁 V-Max": "400 km/h"}},
    "Ducati Superleggera V4": {"klasse": "M4", "staerke": "99", "kennzeichen": "SUPERLEG", "rarity": "Legendary (Gold)", "daten": {"Typ": "Limited", "⚡ Leistung": "165 kW (224 PS)", "⚖️ Gewicht": "159 kg (Trocken)", "🏁 V-Max": "300 km/h"}}
}

def get_image_base64(auto_name):
    moegliche_dateien = [(f"karten/{auto_name}.png", "image/png"), (f"karten/{auto_name}.jpg", "image/jpeg"), (f"karten/{auto_name}.jpeg", "image/jpeg")]
    for datei_pfad, mime_type in moegliche_dateien:
        if os.path.exists(datei_pfad):
            with open(datei_pfad, "rb") as img_file:
                return f"data:{mime_type};base64,{base64.b64encode(img_file.read()).decode()}"
    return ""

def render_card_html(auto_name):
    info = KARTEN_KATALOG.get(auto_name)
    if not info: return ""
    bild_url = get_image_base64(auto_name)
    bild_html = f'<img src="{bild_url}" style="width: 100%; height: 100%; object-fit: cover;">' if bild_url else '🏎️'
    
    tabellen_rows = "".join([f"<tr><td style='padding: 4px 8px; border-bottom: 1px solid #eee; color: #333;'>{k}</td><td style='padding: 4px 8px; text-align: right; font-weight: bold; border-bottom: 1px solid #eee; color: #111;'>{v}</td></tr>" for k, v in info['daten'].items()])

    if "Legendary" in info['rarity']:
        main_color, dark_color, bg_color = "#eab308", "#422006", "#fefce8"
    elif "Epic" in info['rarity']:
        main_color, dark_color, bg_color = "#a855f7", "#3b0764", "#faf5ff"
    elif "Rare" in info['rarity']:
        main_color, dark_color, bg_color = "#3b82f6", "#172554", "#eff6ff"
    else: 
        main_color, dark_color, bg_color = "#9ca3af", "#1f2937", "#f3f4f6"

    return f"""
    <style>body {{ margin: 0; padding: 0; overflow: hidden; background-color: transparent; }} ::-webkit-scrollbar {{ display: none; }}</style>
    <div style="width: 270px; border-radius: 14px; overflow: hidden; background: {bg_color}; font-family: Arial, sans-serif; border: 3px solid {main_color}; margin-bottom: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.25);">
        <div style="background: {dark_color}; color: white; padding: 8px; text-align: center; font-size: 11px; font-weight: 900; letter-spacing: 1.5px; border-bottom: 2px solid {main_color};">⚡ WOLF OF WÜLLNERSTRASSE ⚡</div>
        <div style="display: flex; align-items: center; padding: 10px 8px; gap: 8px;">
            <div style="width: 34px; height: 34px; border-radius: 50%; background: white; border: 2px solid {dark_color}; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 900; color: {dark_color}; box-shadow: 0 2px 5px rgba(0,0,0,0.15);">{info['klasse']}</div>
            <div style="flex: 1; height: 130px; border-radius: 8px; overflow: hidden; position: relative; border: 2px solid {dark_color}; box-shadow: inset 0 0 10px rgba(0,0,0,0.2);">{bild_html}
                <div style="position: absolute; bottom: 5px; left: 50%; transform: translateX(-50%); background: white; border: 1.5px solid {dark_color}; border-radius: 4px; padding: 2px 8px; font-size: 9px; font-weight: 900; color: #111; letter-spacing: 1px; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.4);">{info['kennzeichen']}</div>
            </div>
            <div style="width: 34px; height: 34px; border-radius: 50%; background: white; border: 2px solid {main_color}; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 900; color: {main_color}; box-shadow: 0 2px 5px rgba(0,0,0,0.15); text-shadow: 0px 0px 2px {main_color}44;">{info['staerke']}</div>
        </div>
        <div style="text-align: center; padding: 8px; background: {dark_color}; color: white; border-top: 2px solid {main_color}; border-bottom: 2px solid {main_color};">
            <div style="font-weight: 900; font-size: 15px; letter-spacing: 0.5px; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">{auto_name}</div>
            <div style="font-size: 10px; font-weight: 800; color: {main_color}; text-transform: uppercase; margin-top: 3px; letter-spacing: 1px;">{info['rarity']}</div>
        </div>
        <div style="padding: 8px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 11px; background: white; border-radius: 6px; overflow: hidden; border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">{tabellen_rows}</table>
        </div>
    </div>
    """

# --- 3. SAVEGAMES & FRAGEN LADEN ---
DATA_FILE = "savegames.json"
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

@st.cache_data
def load_questions():
    if os.path.exists("fragen.json"):
        with open("fragen.json", "r", encoding="utf-8") as f: 
            fragen = json.load(f)
            total_q = len(fragen)
            for i, q in enumerate(fragen):
                if i < 30: q["Foliensatz"] = "Foliensatz 01"
                elif i < 60: q["Foliensatz"] = "Foliensatz 02"
                elif i < 80: q["Foliensatz"] = "Foliensatz 02 Geldumschlag"
                elif i < 110: q["Foliensatz"] = "Foliensatz 03"
                elif i >= total_q - 5: q["Foliensatz"] = "Foliensatz 12 Andlerformel"
                else:
                    block_index = (i - 110) // 30
                    current_fs = 4 + block_index
                    q["Foliensatz"] = f"Foliensatz {current_fs:02d}"
            return fragen
    return [{"Frage": "Fehler: fragen.json fehlt!", "Musterantwort": "Bitte hochladen.", "Schwierigkeitsgrad": "Leicht", "Foliensatz": "Fehler"}]

database = load_data()
fragen_pool = load_questions()

if "username" not in st.session_state: st.session_state.username = ""
if "xp" not in st.session_state: st.session_state.xp = 0
if "current_tutor" not in st.session_state: st.session_state.current_tutor = "Jordan Belfort"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "current_question" not in st.session_state: st.session_state.current_question = None

# --- 4. STARTBILDSCHIRM & LOGIN ---
if not st.session_state.username:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"): st.image("logo.png")
        else: st.markdown("<h1 style='text-align: center; font-size: 80px;'>🐺</h1>", unsafe_allow_html=True)
            
        st.title("Wolf of Wüllnerstraße")
        st.caption("🔒 QUIZ EDITION - CLOSED BETA")
        st.markdown("---")
        
        new_user = st.text_input("Gib deinen Namen ein (z.B. Malte):")
        tutor_choice = st.text_input("Name deines Tutors:", value="Jordan Belfort")
        beta_code = st.text_input("Beta-Zugangscode:", type="password")
        
        if st.button("Lern-Session Starten", width="stretch"):
            if beta_code != "PITCH2026": st.error("❌ Falscher Zugangscode!")
            elif not new_user: st.error("Bitte gib einen Namen ein!")
            else:
                st.session_state.username = new_user
                if new_user not in database: database[new_user] = {"xp": 0, "tutor_name": tutor_choice, "inventory": [], "history": [], "current_question": None}
                else: database[new_user]["tutor_name"] = tutor_choice
                save_data(database)
                st.session_state.xp = database[new_user].get("xp", 0)
                st.session_state.current_tutor = tutor_choice 
                st.session_state.chat_history = database[new_user].get("history", [])
                st.session_state.current_question = database[new_user].get("current_question", None)
                st.rerun()
    st.stop()

# --- 5. POP-UP ANIMATION FÜR DIE LOOTBOX ---
@st.dialog("🎁 Epischer Loot-Drop!", width="small")
def show_lootbox_popup():
    animation_box = st.empty()
    phasen = [
        ("📦 Reiße das Booster-Pack auf...", "#9ca3af"),
        ("⚡ Scanne Fahrzeugdaten...", "#3b82f6"),
        ("🔥 Berechne Rarity...", "#a855f7"),
        ("✨ BÄÄM! Das ist dein Pull!", "#eab308")
    ]
    for text, color in phasen:
        animation_box.markdown(f"<h3 style='text-align: center; color: {color};'>{text}</h3>", unsafe_allow_html=True)
        time.sleep(0.8)
    animation_box.empty()
    
    pool_leg = [k for k, v in KARTEN_KATALOG.items() if "Legendary" in v["rarity"]]
    pool_epi = [k for k, v in KARTEN_KATALOG.items() if "Epic" in v["rarity"]]
    pool_rar = [k for k, v in KARTEN_KATALOG.items() if "Rare" in v["rarity"]]
    pool_com = [k for k, v in KARTEN_KATALOG.items() if "Common" in v["rarity"]]
    
    roll = random.randint(1, 100)
    if roll <= 5 and pool_leg: auto = random.choice(pool_leg)
    elif roll <= 20 and pool_epi: auto = random.choice(pool_epi)
    elif roll <= 50 and pool_rar: auto = random.choice(pool_rar)
    else: auto = random.choice(pool_com)
    
    database[st.session_state.username]["inventory"].append(auto)
    save_data(database)
    
    st.success(f"Herzlichen Glückwunsch! Du hast **{auto}** gezogen!")
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        st.components.v1.html(render_card_html(auto), height=460)
        
    st.balloons()
    if st.button("Ab in die Garage 🏁", width="stretch"):
        st.rerun()

# --- 6. SEITENLEISTE ---
with st.sidebar:
    st.title("📚 Themenauswahl")
    alle_foliensaetze = sorted(list(set([q["Foliensatz"] for q in fragen_pool])))
    default_idx = 0
    if st.session_state.current_question and st.session_state.current_question["Foliensatz"] in alle_foliensaetze:
        default_idx = alle_foliensaetze.index(st.session_state.current_question["Foliensatz"])
        
    gewaehlter_foliensatz = st.selectbox("Aktueller Foliensatz:", alle_foliensaetze, index=default_idx)
    gefilterte_fragen = [q for q in fragen_pool if q["Foliensatz"] == gewaehlter_foliensatz]
    
    if "last_foliensatz" not in st.session_state: st.session_state.last_foliensatz = gewaehlter_foliensatz

    if gewaehlter_foliensatz != st.session_state.last_foliensatz or st.session_state.current_question is None:
        st.session_state.last_foliensatz = gewaehlter_foliensatz
        neue_frage = random.choice(gefilterte_fragen)
        st.session_state.current_question = neue_frage
        willkommens_text = f"🏁 **Themenblock: {gewaehlter_foliensatz}**\n\nHier ist deine Aufgabe (Schwierigkeit: {neue_frage.get('Schwierigkeitsgrad', 'Mittel')}):\n### {neue_frage['Frage']}"
        st.session_state.chat_history.append({"role": "assistant", "content": willkommens_text})
        database[st.session_state.username]["history"] = st.session_state.chat_history
        database[st.session_state.username]["current_question"] = neue_frage
        save_data(database)
        st.rerun()
        
    st.markdown("---")
    st.title("⚙️ Garage & Album")
    st.success(f"Spieler: {st.session_state.username}")
    st.write(f"**Deine XP:** {st.session_state.xp}")
    
    if st.button("Lootbox öffnen (-30 XP) 🎁", width="stretch"):
        if st.session_state.xp >= 30:
            st.session_state.xp -= 30 
            database[st.session_state.username]["xp"] = st.session_state.xp
            save_data(database)
            show_lootbox_popup()
        else:
            st.error("Nicht genug XP!")
            
    with st.expander("📚 Dein Sammelalbum", expanded=True):
        inventar = database[st.session_state.username].get("inventory", [])
        if not inventar:
            st.info("Deine Garage ist noch leer.")
        else:
            karten_counts = {karte: inventar.count(karte) for karte in set(inventar)}
            for karte, anzahl in karten_counts.items():
                st.write(f"**Anzahl: {anzahl}x**")
                st.components.v1.html(render_card_html(karte), height=460)

# --- 7. CHAT OBERFLÄCHE ---
st.title(f"📈 {st.session_state.current_tutor}'s Quiz-Drill")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

q = st.session_state.current_question

# NEU: Der Disclaimer über dem Eingabefeld
st.markdown("<div style='text-align: center; font-size: 13px; color: #888; margin-top: 30px; margin-bottom: 5px;'>🐺 Wolf of Wüllnerstraße ist eine KI und kann Fehler machen. Bitte überprüfe wichtige Fakten.</div>", unsafe_allow_html=True)

if student_answer := st.chat_input("Deine Antwort eingeben..."):
    # Wir fügen die Antwort der Historie hinzu
    st.session_state.chat_history.append({"role": "user", "content": student_answer})
    with st.chat_message("user"): st.markdown(student_answer)

    with st.chat_message("assistant"):
        with st.spinner(f"{st.session_state.current_tutor} prüft deine Antwort..."):
            
            # --- DER NEUE, HARTE ROLLENSPIEL- UND INTERAKTIONS-PROMPT ---
            sys_text = f"""Du bist {st.session_state.current_tutor}, ein genialer, aber extrem charakterstarker Tutor für BWL. 
            WICHTIGSTE REGEL: Du MUSST deine Rolle absolut übertrieben spielen! Nutze deinen typischen Slang, Floskeln und deine Persönlichkeit in JEDEM Satz. (Ein Jordan Belfort nutzt Wall-Street-Slang, redet über Geld, nennt den Studenten 'Rookie'. Ein Albert Einstein redet über das Universum, Physik und nennt ihn 'mein lieber Forscherfreund'). Verlass NIEMALS deine Rolle!

            Du prüfst gerade folgende Frage:
            FRAGE: {q.get('Frage', '')}
            MUSTERANTWORT: {q.get('Musterantwort', '')}

            BEWERTUNGSREGELN (Sei kulant bei Grammatik, es geht um den inhaltlichen Sinn):
            1. Komplett falsch: Beleidige den Studenten passend zu deiner Rolle, erkläre die korrekte Lösung, vergib [+0 XP] und schreibe GANZ AM ENDE das Wort [WEITER].
            2. Teilweise richtig: Lobe ihn leicht in deiner Rolle, vergib Teilpunkte (z.B. [+10 XP]) und HAKE SPEZIFISCH NACH, was noch fehlt! Schreibe in diesem Fall NICHT das Wort [WEITER], damit der Student noch einmal antworten kann.
            3. Perfekt beantwortet (oder fehlenden Rest nachgeliefert): Feiere ihn extrem ab, vergib die restlichen oder vollen Punkte (z.B. [+20 XP] oder [+10 XP]) und schreibe GANZ AM ENDE exakt das Wort [WEITER].
            
            Du MUSST die XP in jedem Fall in deiner Antwort exakt im Format [+X XP] ausgeben!
            """
            
            # Wir übergeben Llama die Anweisungen UND die letzten Nachrichten für den Kontext
            groq_messages = [{"role": "system", "content": sys_text}]
            
            # Die letzten 6 Nachrichten des Chats mitsenden, damit die KI weiß, ob sie gerade nachgehakt hat!
            for msg in st.session_state.chat_history[-6:]:
                groq_messages.append({"role": msg["role"], "content": msg["content"]})
            
            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=groq_messages
                )
                answer = completion.choices[0].message.content
                
                # Wir filtern das [WEITER] für die Anzeige heraus, damit es unsichtbar für den Nutzer bleibt
                display_answer = answer.replace("[WEITER]", "").strip()
                st.markdown(display_answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                
                # XP auslesen und gutschreiben
                xp_matches = re.findall(r'\[\+(\d+)\s*XP\]', answer)
                if xp_matches:
                    gewonnene_xp = sum(int(match) for match in xp_matches)
                    if gewonnene_xp > 0:
                        st.session_state.xp += gewonnene_xp
                        database[st.session_state.username]["xp"] = st.session_state.xp
                        st.success(f"Konto aktualisiert! +{gewonnene_xp} XP gutgeschrieben!")
                        st.balloons()
                
                # DIE NEUE SCHRANKE: Erst wenn die KI [WEITER] ausgibt, geht es zur nächsten Frage
                if "[WEITER]" in answer:
                    time.sleep(3)
                    neue_frage = random.choice(gefilterte_fragen)
                    st.session_state.current_question = neue_frage
                    
                    next_text = f"Nächste Runde! 🚀 ({gewaehlter_foliensatz})\n\n### {neue_frage['Frage']}"
                    st.session_state.chat_history.append({"role": "assistant", "content": next_text})
                
                # Speichern und neu laden
                database[st.session_state.username]["history"] = st.session_state.chat_history
                database[st.session_state.username]["current_question"] = st.session_state.current_question
                save_data(database)
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Server-Verbindungsfehler: {e}")
