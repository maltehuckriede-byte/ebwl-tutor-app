import streamlit as st
from groq import Groq
import os
import json
import random
import re
import time
import base64

# --- 1. SETUP & API ---
st.set_page_config(page_title="Wolf of Wüllnerstraße - Quiz Edition", page_icon="🐺", layout="wide")

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --- 2. DIE FAHRZEUG-DATENBANK ---
# WICHTIG: Füge hier wieder deinen kompletten KARTEN_KATALOG ein!
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
    bg_color = "#fefce8" if "Legendary" in info['rarity'] else "#faf5ff" if "Epic" in info['rarity'] else "#eff6ff" if "Rare" in info['rarity'] else "#f3f4f6"
    
    return f"""
    <div style="width: 270px; border-radius: 14px; overflow: hidden; background: {bg_color}; border: 3px solid #333; margin-bottom: 15px;">
        <div style="background: #111; color: white; padding: 8px; text-align: center; font-weight: bold;">{auto_name} - {info['rarity']}</div>
        <div style="height: 150px; background: #ddd; display: flex; align-items: center; justify-content: center; font-size: 40px;">{bild_html}</div>
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
        with open("fragen.json", "r", encoding="utf-8") as f: return json.load(f)
    return [{"Frage": "Fehler: fragen.json nicht gefunden!", "Musterantwort": "Erstelle die Datei.", "Schwierigkeitsgrad": "Leicht"}]

database = load_data()
fragen_pool = load_questions()

# Session State Init
if "username" not in st.session_state: st.session_state.username = ""
if "xp" not in st.session_state: st.session_state.xp = 0
if "current_tutor" not in st.session_state: st.session_state.current_tutor = "Jordan Belfort"
if "current_question" not in st.session_state: st.session_state.current_question = random.choice(fragen_pool)
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- 4. LOGIN (MIT PASSWORT & TUTOR WAHL) ---
if not st.session_state.username:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🐺 Wolf of Wüllnerstraße")
        st.caption("🔒 QUIZ EDITION - CLOSED BETA")
        st.markdown("---")
        
        new_user = st.text_input("Gib deinen Namen ein (z.B. Malte):")
        tutor_choice = st.text_input("Name deines Tutors:", value="Jordan Belfort")
        beta_code = st.text_input("Beta-Zugangscode:", type="password", help="Nur für autorisierte Tester.")
        
        if st.button("Lern-Session Starten", width="stretch"):
            if beta_code != "PITCH2026": 
                st.error("❌ Falscher Zugangscode! Diese Version ist nur für geladene Beta-Tester.")
            elif not new_user:
                st.error("Bitte gib einen Namen ein, um zu starten!")
            else:
                st.session_state.username = new_user
                if new_user not in database:
                    database[new_user] = {"xp": 0, "tutor_name": tutor_choice, "inventory": []}
                else:
                    database[new_user]["tutor_name"] = tutor_choice
                    if "inventory" not in database[new_user]: database[new_user]["inventory"] = []
                
                save_data(database)
                st.session_state.xp = database[new_user]["xp"]
                st.session_state.current_tutor = tutor_choice 
                st.rerun()
    st.stop()

# --- 5. SEITENLEISTE: LOOTBOX MIT ANIMATION ---
with st.sidebar:
    st.title("⚙️ Garage & Album")
    st.success(f"Eingeloggt als: {st.session_state.username}")
    st.write(f"**Deine XP:** {st.session_state.xp}")
    
    if st.button("Lootbox öffnen (-30 XP) 🎁", width="stretch"):
        if st.session_state.xp >= 30:
            st.session_state.xp -= 30 
            database[st.session_state.username]["xp"] = st.session_state.xp
            save_data(database)
            
            # Pack Opening Animation
            animation_box = st.empty()
            phasen = [
                ("📦 Reiße das Booster-Pack auf...", "#9ca3af"),
                ("⚡ Scanne die Fahrzeugklasse...", "#3b82f6"),
                ("🔥 Überprüfe die Rarity...", "#a855f7"),
                ("✨ BÄÄM! Das ist dein Pull!", "#eab308")
            ]
            for text, color in phasen:
                animation_box.markdown(f"<h3 style='text-align: center; color: {color};'>{text}</h3>", unsafe_allow_html=True)
                time.sleep(0.7)
            animation_box.empty()
            
            pool_leg = [k for k, v in KARTEN_KATALOG.items() if "Legendary" in v["rarity"]]
            pool_epi = [k for k, v in KARTEN_KATALOG.items() if "Epic" in v["rarity"]]
            pool_rar = [k for k, v in KARTEN_KATALOG.items() if "Rare" in v["rarity"]]
            pool_com = [k for k, v in KARTEN_KATALOG.items() if "Common" in v["rarity"]]
            
            roll = random.randint(1, 100)
            if roll <= 5 and pool_leg: gezogenes_auto = random.choice(pool_leg)
            elif roll <= 20 and pool_epi: gezogenes_auto = random.choice(pool_epi)
            elif roll <= 50 and pool_rar: gezogenes_auto = random.choice(pool_rar)
            else: gezogenes_auto = random.choice(pool_com)
            
            database[st.session_state.username]["inventory"].append(gezogenes_auto)
            save_data(database)
            
            st.success(f"Du hast gezogen: **{gezogenes_auto}**!")
            st.components.v1.html(render_card_html(gezogenes_auto), height=200)
            st.balloons()
        else:
            st.error("Nicht genug XP! Beantworte erst Fragen.")

# --- 6. QUIZ BEREICH ---
st.title(f"📈 {st.session_state.current_tutor}'s EBWL Drill")

q = st.session_state.current_question
st.info(f"**Schwierigkeit:** {q.get('Schwierigkeitsgrad', 'Unbekannt')}\n\n### ❓ Frage:\n{q.get('Frage', 'Keine Frage gefunden')}")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if student_answer := st.chat_input("Deine Antwort..."):
    st.session_state.chat_history.append({"role": "user", "content": student_answer})
    with st.chat_message("user"): st.markdown(student_answer)

    with st.chat_message("assistant"):
        with st.spinner(f"{st.session_state.current_tutor} bewertet deine Antwort..."):
            
            # Sauber formatierter System Prompt ohne Einrückungs-Chaos
            sys_text = f"Du bist {st.session_state.current_tutor}, Tutor für EBWL. Bewerte die folgende Studentenantwort im passenden Slang. Wenn komplett falsch: [+0 XP]. Wenn teilweise richtig: [+10 XP]. Wenn perfekt: [+20 XP]. Du MUSST die XP am Ende im Format [+X XP] schreiben!"
            
            usr_text = f"FRAGE: {q.get('Frage', '')}\nMUSTERANTWORT: {q.get('Musterantwort', '')}\nSTUDENTENANTWORT: {student_answer}"
            
            try:
                completion = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {"role": "system", "content": sys_text},
                        {"role": "user", "content": usr_text}
                    ]
                )
                
                answer = completion.choices[0].message.content
                st.markdown(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                
                xp_matches = re.findall(r'\[\+(\d+)\s*XP\]', answer)
                if xp_matches:
                    gewonnene_xp = sum(int(match) for match in xp_matches)
                    if gewonnene_xp > 0:
                        st.session_state.xp += gewonnene_xp
                        database[st.session_state.username]["xp"] = st.session_state.xp
                        save_data(database)
                        st.success(f"BÄÄM! {gewonnene_xp} XP verdient!")
                        st.balloons()
                    
                    time.sleep(4)
                    st.session_state.current_question = random.choice(fragen_pool)
                    st.session_state.chat_history = [] 
                    st.rerun()
            except Exception as e:
                st.error(f"❌ API Fehler: {e}")
