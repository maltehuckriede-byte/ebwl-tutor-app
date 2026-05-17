import streamlit as st
from groq import Groq
import os
import json
import random
import re
import base64

# --- 1. SETUP & API ---
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)
st.set_page_config(page_title="Wolf of Wüllnerstraße", page_icon="🐺", layout="wide")

# --- 2. DIE RIESIGE FAHRZEUG-DATENBANK ---
# Alle 25 Autos und Motorräder mit recherchierten Realdaten!
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

# --- 3. HILFSFUNKTIONEN (HTML & BILDER) ---
def get_image_base64(auto_name):
    """Sucht automatisch nach PNG oder JPG und wandelt es um."""
    # Wir sagen dem Code, welche Endungen er nacheinander prüfen soll
    moegliche_dateien = [
        (f"karten/{auto_name}.png", "image/png"),
        (f"karten/{auto_name}.jpg", "image/jpeg"),
        (f"karten/{auto_name}.jpeg", "image/jpeg")
    ]
    
    for datei_pfad, mime_type in moegliche_dateien:
        if os.path.exists(datei_pfad):
            with open(datei_pfad, "rb") as img_file:
                return f"data:{mime_type};base64,{base64.b64encode(img_file.read()).decode()}"
                
    # Wenn er weder PNG noch JPG findet, gibt er leer zurück (dann kommt das Emoji)
    return ""

def render_card_html(auto_name):
    """Erzeugt den Code für die fertige Karte mit dynamischem Farb-Theme."""
    info = KARTEN_KATALOG.get(auto_name)
    if not info: return ""
    
    # Smarter Bild-Abruf (PNG oder JPG)
    bild_url = get_image_base64(auto_name)
    
    if not bild_url:
        bild_html = f'<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:50px; background: #e2eaf3;">🏎️</div>'
    else:
        bild_html = f'<img src="{bild_url}" style="width: 100%; height: 100%; object-fit: cover;">'
        
    # Tabellenzeilen stylen
    tabellen_rows = "".join([f"<tr><td style='padding: 4px 8px; border-bottom: 1px solid #eee; color: #333;'>{k}</td><td style='padding: 4px 8px; text-align: right; font-weight: bold; border-bottom: 1px solid #eee; color: #111;'>{v}</td></tr>" for k, v in info['daten'].items()])

    # --- DAS NEUE DYNAMISCHE FARB-SYSTEM ---
    if "Legendary" in info['rarity']:
        main_color = "#eab308" # Strahlendes Gold
        dark_color = "#422006" # Sehr dunkles Braun/Gold für Header
        bg_color = "#fefce8"   # Zartes Hellgelb
    elif "Epic" in info['rarity']:
        main_color = "#a855f7" # Leuchtendes Lila
        dark_color = "#3b0764" # Sehr dunkles Lila
        bg_color = "#faf5ff"   # Zartes Hell-Lila
    elif "Rare" in info['rarity']:
        main_color = "#3b82f6" # Kräftiges Blau
        dark_color = "#172554" # Sehr dunkles Blau
        bg_color = "#eff6ff"   # Zartes Hellblau
    else: # Common
        main_color = "#9ca3af" # Industrie-Grau
        dark_color = "#1f2937" # Dunkelgrau/Anthrazit
        bg_color = "#f3f4f6"   # Zartes Hellgrau

    # Das HTML mit den eingefügten Farb-Variablen
    return f"""
    <style>
        body {{ margin: 0; padding: 0; overflow: hidden; background-color: transparent; }}
        ::-webkit-scrollbar {{ display: none; }}
    </style>
    
    <div style="width: 270px; border-radius: 14px; overflow: hidden; background: {bg_color}; font-family: Arial, sans-serif; border: 3px solid {main_color}; margin-bottom: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.25);">
        
        <div style="background: {dark_color}; color: white; padding: 8px; text-align: center; font-size: 11px; font-weight: 900; letter-spacing: 1.5px; border-bottom: 2px solid {main_color};">
            ⚡ WOLF OF WÜLLNERSTRASSE ⚡
        </div>

        <div style="display: flex; align-items: center; padding: 10px 8px; gap: 8px;">
            <div style="width: 34px; height: 34px; border-radius: 50%; background: white; border: 2px solid {dark_color}; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 900; color: {dark_color}; box-shadow: 0 2px 5px rgba(0,0,0,0.15);">
                {info['klasse']}
            </div>
            
            <div style="flex: 1; height: 130px; border-radius: 8px; overflow: hidden; position: relative; border: 2px solid {dark_color}; box-shadow: inset 0 0 10px rgba(0,0,0,0.2);">
                {bild_html}
                <div style="position: absolute; bottom: 5px; left: 50%; transform: translateX(-50%); background: white; border: 1.5px solid {dark_color}; border-radius: 4px; padding: 2px 8px; font-size: 9px; font-weight: 900; color: #111; letter-spacing: 1px; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.4);">
                    {info['kennzeichen']}
                </div>
            </div>
            
            <div style="width: 34px; height: 34px; border-radius: 50%; background: white; border: 2px solid {main_color}; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 900; color: {main_color}; box-shadow: 0 2px 5px rgba(0,0,0,0.15); text-shadow: 0px 0px 2px {main_color}44;">
                {info['staerke']}
            </div>
        </div>

        <div style="text-align: center; padding: 8px; background: {dark_color}; color: white; border-top: 2px solid {main_color}; border-bottom: 2px solid {main_color};">
            <div style="font-weight: 900; font-size: 15px; letter-spacing: 0.5px; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">{auto_name}</div>
            <div style="font-size: 10px; font-weight: 800; color: {main_color}; text-transform: uppercase; margin-top: 3px; letter-spacing: 1px;">{info['rarity']}</div>
        </div>

        <div style="padding: 8px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 11px; background: white; border-radius: 6px; overflow: hidden; border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                {tabellen_rows}
            </table>
        </div>
        
    </div>
    """

# --- 4. PROFISAVEGAME-SYSTEM ---
DATA_FILE = "savegames.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

database = load_data()

if "username" not in st.session_state: st.session_state.username = ""
if "xp" not in st.session_state: st.session_state.xp = 0
if "current_tutor" not in st.session_state: st.session_state.current_tutor = "Jordan Belfort"
if "messages" not in st.session_state: st.session_state.messages = []

# --- 5. STARTBILDSCHIRM & LOGIN ---
if not st.session_state.username:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", width="stretch")
            
        st.title("🐺 Wolf of Wüllnerstraße")
        st.caption("🔒 CLOSED BETA VERSION")
        st.markdown("---")
        
        new_user = st.text_input("Gib deinen Namen ein (z.B. Malte):")
        tutor_choice = st.text_input("Name deines Tutors:", value="Jordan Belfort")
        
        # NEU: Das VIP-Passwortfeld
        beta_code = st.text_input("Beta-Zugangscode:", type="password", help="Nur für autorisierte Tester.")
        
        if st.button("Lern-Session Starten", width="stretch"):
            # NEU: Die Türsteher-Logik
            if beta_code != "PITCH2026": 
                st.error("❌ Falscher Zugangscode! Diese Version ist nur für geladene Beta-Tester.")
            elif not new_user:
                st.error("Bitte gib einen Namen ein, um zu starten!")
            else:
                # Wenn Passwort stimmt und Name da ist:
                st.session_state.username = new_user
                if new_user not in database:
                    database[new_user] = {"xp": 0, "tutor_name": tutor_choice, "history": [], "inventory": []}
                else:
                    database[new_user]["tutor_name"] = tutor_choice
                    if "inventory" not in database[new_user]: database[new_user]["inventory"] = []
                
                save_data(database)
                user_save = database[new_user]
                st.session_state.xp = user_save["xp"]
                st.session_state.current_tutor = tutor_choice 
                st.session_state.messages = user_save.get("history", [])
                st.rerun()
    st.stop()

# --- AB HIER: NUR WENN EINGELOGGT ---

# --- 6. SEITENLEISTE (Garage, Shop & Logout) ---
with st.sidebar:
    st.title("⚙️ Garage & Album")
    st.success(f"Eingeloggt als: {st.session_state.username}")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Abmelden", width="stretch"):
            st.session_state.username = ""
            st.rerun()
    with col_btn2:
        if st.button("🗑️ Chat leeren", width="stretch"):
            st.session_state.messages = [] 
            database[st.session_state.username]["history"] = [] 
            save_data(database)
            st.rerun()
            
    st.markdown("---")
    
    # --- DER KARTEN-SHOP (Gacha Logik sortiert nach Rarity) ---
    st.title("🃏 Fahrzeug-Quartett")
    st.write(f"**Deine XP (Währung):** {st.session_state.xp}")
    
    if st.button("Lootbox öffnen (-30 XP) 🎁", width="stretch"):
        if st.session_state.xp >= 30:
            st.session_state.xp -= 30 
            
            # Trennt den Katalog in die Seltenheits-Pools auf
            pool_leg = [k for k, v in KARTEN_KATALOG.items() if "Legendary" in v["rarity"]]
            pool_epi = [k for k, v in KARTEN_KATALOG.items() if "Epic" in v["rarity"]]
            pool_rar = [k for k, v in KARTEN_KATALOG.items() if "Rare" in v["rarity"]]
            pool_com = [k for k, v in KARTEN_KATALOG.items() if "Common" in v["rarity"]]
            
            # Gacha-Wahrscheinlichkeiten
            roll = random.randint(1, 100)
            if roll <= 5: target_pool = pool_leg
            elif roll <= 20: target_pool = pool_epi
            elif roll <= 50: target_pool = pool_rar
            else: target_pool = pool_com
            
            gezogenes_auto = random.choice(target_pool)
            
            database[st.session_state.username]["xp"] = st.session_state.xp
            database[st.session_state.username]["inventory"].append(gezogenes_auto)
            save_data(database)
            
            st.success(f"BÄÄM! Du hast gezogen: **{gezogenes_auto}**")
            st.balloons()
        else:
            st.error("Nicht genug XP! Beantworte erst Fragen des Tutors.")

    # --- DAS VISUELLE SAMMELALBUM ---
    with st.expander("📚 Dein Sammelalbum", expanded=True):
        inventar = database[st.session_state.username].get("inventory", [])
        if not inventar:
            st.info("Deine Garage ist noch leer.")
        else:
            # Zählt die Karten und rendert das HTML Widget!
            karten_counts = {karte: inventar.count(karte) for karte in set(inventar)}
            for karte, anzahl in karten_counts.items():
                st.write(f"**Anzahl: {anzahl}x**")
                st.iframe(render_card_html(karte), height=450)

# --- 7. SYSTEM PROMPT (Der Charakter-Schauspieler & Quellen-Nazi) ---
echte_dateien = []
if os.path.exists("studienmaterial"): echte_dateien = [f for f in os.listdir("studienmaterial") if f.endswith(".pdf")]
dateien_string = ", ".join(echte_dateien)

SYSTEM_PROMPT = f"""Du bist {st.session_state.current_tutor}, ein anspruchsvoller Tutor für EBWL an der RWTH Aachen.
WICHTIGSTE REGEL: Du musst die Persönlichkeit, den Slang und die Eigenarten von {st.session_state.current_tutor} PERFEKT imitieren!

DEINE WEITEREN REGELN:
1. RECHTSCHREIBUNG: Achte strikt auf korrekte Grammatik.
2. QUELLENANGABE: Du darfst als Quelle AUSSCHLIESSLICH diese exakten Dateinamen verwenden: {dateien_string}. Erfinde NIEMALS eigene Dateinamen! Wenn der Nutzer dich auf visuelle Details (Pfeile, Farben) hinweist, vertraue seiner Beschreibung, da du PDFs nur als Text liest.
3. SEI KRITISCH: Faulheit wird nicht akzeptiert.
4. XP VERGEBEN: Wenn der Nutzer inhaltlich richtig antwortet, schreibe exakt "[+10 XP]".
5. Verrate niemals das Endergebnis sofort. Nutze Analogien.
"""

# --- 8. BACKEND WISSEN ---
@st.cache_resource
def load_knowledge():
    if not os.path.exists("studienmaterial"): os.makedirs("studienmaterial")
    files_to_send = []
    for filename in os.listdir("studienmaterial"):
        if filename.endswith(".pdf"):
            file_path = os.path.join("studienmaterial", filename)
            uploaded_file = client.files.upload(file=file_path)
            files_to_send.append(uploaded_file)
    return files_to_send

backend_files = load_knowledge()

# --- 9. ZITATE FÜR DEN LADESCREEN ---
LADE_ZITATE = [
    "Preis ist das, was du zahlst. Wert ist das, was du bekommst. - Warren Buffett",
    "Der Markt kann länger irrational bleiben, als du liquide. - Keynes",
    "Zinseszins ist das achte Weltwunder. - Albert Einstein",
    "Geduld ist die oberste Tugend des Investors."
]

# --- 10. BENUTZEROBERFLÄCHE & CHAT LOGIK ---
st.title(f"Willkommen in der Session, {st.session_state.username}! 🐺")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input(f"Frag deinen Tutor {st.session_state.current_tutor}..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        if not backend_files:
            st.warning("Bitte lege zuerst ein PDF in 'studienmaterial' ab!")
        else:
            spinner_text = f"{st.session_state.current_tutor} analysiert... | 💡 {random.choice(LADE_ZITATE)}"
        with st.spinner(spinner_text):
            try:
                # 1. System-Prompt und Chat-Historie für Groq zusammenbauen
                groq_messages = [
                    {"role": "system", "content": f"Du bist {st.session_state.current_tutor}. Antworte im passenden Stil und vergib für gute Antworten XP in dem Format [+10 XP]."}
                ]
                
                # Die gesamte bisherige Konversation hinzufügen
                for msg in st.session_state.messages:
                    groq_messages.append({"role": msg["role"], "content": msg["content"]})

                # 2. Die blitzschnelle Anfrage an Groq (Llama 3)
                completion = client.chat.completions.create(
                    model="llama3-8b-8192", 
                    messages=groq_messages
                )
                
                # 3. Die Antwort sauber auslesen
                answer = completion.choices[0].message.content
                
                # 4. Antwort anzeigen und in der Historie speichern
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # 5. Die altbekannte XP-Logik
                xp_matches = re.findall(r'\[\+(\d+)\s*XP\]', answer)
                if xp_matches:
                    total_gained_xp = sum(int(match) for match in xp_matches)
                    st.session_state.xp += total_gained_xp
                    database[st.session_state.username]["xp"] = st.session_state.xp
                    st.balloons()
                    
            except Exception as e:
                st.error(f"❌ Fehler bei der API-Anfrage: {e}")
                        
        database[st.session_state.username]["history"] = st.session_state.messages
        save_data(database)
