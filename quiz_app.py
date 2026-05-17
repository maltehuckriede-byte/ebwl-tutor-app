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
# (HINWEIS: Füge hier zur Sicherheit nochmal deinen kompletten KARTEN_KATALOG mit allen 25 Fahrzeugen ein!)
KARTEN_KATALOG = {
    "VW Golf VIII GTI": {"klasse": "C1", "staerke": "45", "kennzeichen": "GOLF-GTI", "rarity": "Common (Grau)", "daten": {"⚡ Leistung": "180 kW", "🕒 0-100": "6,2 s"}},
    "BMW M3 Competition": {"klasse": "B1", "staerke": "80", "kennzeichen": "M3-COMP", "rarity": "Rare (Blau)", "daten": {"⚡ Leistung": "375 kW", "🕒 0-100": "3,9 s"}},
    "Porsche 911 GT3": {"klasse": "S1", "staerke": "95", "kennzeichen": "GT3-992", "rarity": "Epic (Lila)", "daten": {"⚡ Leistung": "375 kW", "🕒 0-100": "3,4 s"}},
    "Bugatti Chiron": {"klasse": "H1", "staerke": "100", "kennzeichen": "CHIRON", "rarity": "Legendary (Gold)", "daten": {"⚡ Leistung": "1103 kW", "🕒 0-100": "2,4 s"}}
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
if "current_question" not in st.session_state: st.session_state.current_question = random.choice(fragen_pool)
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- 4. LOGIN ---
if not st.session_state.username:
    st.title("🐺 Wolf of Wüllnerstraße - Quiz Edition")
    new_user = st.text_input("Dein Name:")
    if st.button("Starten"):
        if new_user:
            st.session_state.username = new_user
            if new_user not in database:
                database[new_user] = {"xp": 0, "inventory": []}
                save_data(database)
            st.session_state.xp = database[new_user]["xp"]
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
            
            # --- DIE PACK OPENING ANIMATION ---
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
            # -----------------------------------
            
            pool_leg = [k for k, v in KARTEN_KATALOG.items() if "Legendary" in v["rarity"]]
            pool_epi = [k for k, v in KARTEN_KATALOG.items() if "Epic" in v["rarity"]]
            pool_rar = [k for k, v in KARTEN_KATALOG.items() if "Rare" in v["rarity"]]
            pool_com = [k for k, v in KARTEN_KATALOG.items() if "Common" in v["rarity"]]
            
            roll = random.randint(1, 100)
            if roll <= 5: gezogenes_auto = random.choice(pool_leg)
            elif roll <= 20: gezogenes_auto = random.choice(pool_epi)
            elif roll <= 50: gezogenes_auto = random.choice(pool_rar)
            else: gezogenes_auto = random.choice(pool_com)
            
            database[st.session_state.username]["inventory"].append(gezogenes_auto)
            save_data(database)
            
            st.success(f"Du hast gezogen: **{gezogenes_auto}**!")
            st.components.v1.html(render_card_html(gezogenes_auto), height=200)
            st.balloons()
            
        else:
            st.error("Nicht genug XP! Beantworte erst Fragen.")

# --- 6. QUIZ BEREICH ---
st.title("📈 Jordan's EBWL Drill")

q = st.session_state.current_question
st.info(f"**Schwierigkeit:** {q['Schwierigkeitsgrad']}\n\n### ❓ Frage:\n{q['Frage']}")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if student_answer := st.chat_input("Deine Antwort..."):
    st.session_state.chat_history.append({"role": "user", "content": student_answer})
    with st.chat_message("user"): st.markdown(student_answer)

    with st.chat_message("assistant"):
        with st.spinner("Jordan bewertet deine Antwort..."):
            
            system_prompt = f"""Du bist Jordan Belfort, Tutor für EBWL. Der Student hat geantwortet.
            FRAGE: {q['Frage']}
            MUSTERANTWORT: {q['Musterantwort']}
            STUDENTENANTWORT: {student_answer}
            
            DEINE AUFGABE:
            1. Bewerte die Antwort in deinem typischen Wall-Street-Slang. Sei streng, aber fair.
            2. Wenn die Antwort komplett falsch ist, vergib [+0 XP].
            3. Wenn sie teilweise richtig ist, vergib [+10 XP].
            4. Wenn sie absolut perfekt ist, vergib [+20 XP].
            Du MUSST die XP am Ende deiner Nachricht im Format [+X XP] schreiben!"""
            
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "system", "content": system_prompt}]
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