import streamlit as st
from google import genai
from google.genai import types
from groq import Groq
import pypdf
import os
import json
import random
import re
import time
import base64
from fpdf import FPDF

# --- 1. SETUP & API-CLIENTS ---
st.set_page_config(page_title="Wolf of Wüllnerstraße", page_icon="🐺", layout="wide")

GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
google_client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --- 2. DIE RIESIGE FAHRZEUG-DATENBANK ---
# WICHTIG: Füge hier deinen kompletten Katalog mit allen 25 Autos ein!
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
    
    if not bild_url: bild_html = f'<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:50px; background: #e2eaf3;">🏎️</div>'
    else: bild_html = f'<img src="{bild_url}" style="width: 100%; height: 100%; object-fit: cover;">'
        
    tabellen_rows = "".join([f"<tr><td style='padding: 4px 8px; border-bottom: 1px solid #eee; color: #333;'>{k}</td><td style='padding: 4px 8px; text-align: right; font-weight: bold; border-bottom: 1px solid #eee; color: #111;'>{v}</td></tr>" for k, v in info['daten'].items()])

    if "Legendary" in info['rarity']: main_color, dark_color, bg_color = "#eab308", "#422006", "#fefce8"
    elif "Epic" in info['rarity']: main_color, dark_color, bg_color = "#a855f7", "#3b0764", "#faf5ff"
    elif "Rare" in info['rarity']: main_color, dark_color, bg_color = "#3b82f6", "#172554", "#eff6ff"
    else: main_color, dark_color, bg_color = "#9ca3af", "#1f2937", "#f3f4f6"

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

# ==========================================
# 📄 HELPER FÜR PDF-GENERIERUNG (/zettel)
# ==========================================
def generate_pdf_bytes(thema, text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    pdf.cell(0, 10, f"Lernzettel: {thema.replace('/zettel', '').strip().upper()}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 11)
    
    # 1. Grobe Formatierungen glätten
    safe_text = text.replace("**", "").replace("#", "").replace("•", "-").replace("*", "-")
    
    # 2. Umlaute manuell umschreiben (Sicherheitsnetz)
    safe_text = safe_text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    safe_text = safe_text.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue").replace("ß", "ss")
    
    for line in safe_text.split("\n"):
        # 3. DER PITCH-SCHUTZ: Alles was Arial nicht drucken kann, wird durch ein '-' ersetzt.
        # Kein Absturz mehr bei Emojis oder komischen Groq-Sonderzeichen!
        clean_line = line.encode('latin-1', 'replace').decode('latin-1').replace("?", "-")
        pdf.multi_cell(0, 6, clean_line)
        
    return pdf.output() # In fpdf2 gibt das direkt die sauberen Bytes zurück

# ==========================================
# 🃏 HELPER FÜR INTERAKTIVE KARTEIKARTEN (/karten)
# ==========================================
def display_html_flashcards(ai_text):
    # Regulärer Ausdruck, um Vorder- und Rückseiten aus dem KI-Text zu filtern
    cards = re.findall(r'(?:Vorderseite|Frage)[:\s\(]*([^*|\n]+)(?:\s*\|\s*|\n+)(?:Rückseite|Antwort)[:\s\(]*([^*|\n\\]+)', ai_text, re.IGNORECASE)
    
    if not cards:
        # Alternativer Fallback-Parser, falls das Format leicht abweicht
        cards = re.findall(r'\*\*(.*?)\*\*.*?\n.*?\*\*(.*?)\*\*', ai_text)

    if cards:
        st.write("### 🃏 Deine interaktiven Karteikarten (Zum Wenden anklicken):")
        cards_html = ""
        
        for i, (front, back) in enumerate(cards):
            front_text = front.replace("):", "").strip()
            back_text = back.replace("):", "").strip()
            
            # Jede Karte bekommt eine unsichtbare Checkbox. Klickt man das Label, dreht CSS die Karte um!
            cards_html += f"""
            <div class="card-box">
                <input type="checkbox" id="card-{i}" class="flip-checkbox" style="display:none;">
                <label for="card-{i}" class="flip-card">
                    <div class="flip-card-inner">
                        <div class="flip-card-front">
                            <div style="font-size: 11px; color: #3b82f6; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">❓ KREUZ / FRAGE</div>
                            <div style="font-size: 14px; font-weight: 600; line-height: 1.4;">{front_text}</div>
                        </div>
                        <div class="flip-card-inner-back">
                            <div style="font-size: 11px; color: #10b981; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">🎯 LÖSUNG / ANTWORT</div>
                            <div style="font-size: 13px; line-height: 1.4; color: #333;">{back_text}</div>
                        </div>
                    </div>
                </label>
            </div>
            """
            
        # Das komplette Styling für das 3D-Quartett-Feeling
        full_html = f"""
        <style>
            .container {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; font-family: Arial, sans-serif; padding: 10px; }}
            .card-box {{ display: inline-block; margin: 10px; }}
            .flip-card {{ display: block; width: 260px; height: 170px; perspective: 1000px; cursor: pointer; }}
            .flip-card-inner {{ position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.5s; transform-style: preserve-3d; }}
            .flip-checkbox:checked + .flip-card .flip-card-inner {{ transform: rotateY(180deg); }}
            .flip-card-front, .flip-card-inner-back {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; -webkit-backface-visibility: hidden; border-radius: 12px; padding: 15px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }}
            .flip-card-front {{ background: #1e293b; color: #f8fafc; border: 2px solid #3b82f6; }}
            .flip-card-inner-back {{ background: #ffffff; color: #0f172a; transform: rotateY(180deg); border: 2px solid #10b981; }}
        </style>
        <div class="container">{cards_html}</div>
        """
        st.components.v1.html(full_html, height=210 if len(cards) <= 3 else 420, scrolling=True)

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
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.write("") 
        st.markdown("<h1 style='text-align: center; white-space: nowrap;'>Wolf of Wüllnerstraße</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; margin-top: -15px;'>🔒 OPEN CHAT & RAG BETA</p>", unsafe_allow_html=True)
        
        img_col1, img_col2, img_col3 = st.columns([1, 3, 1])
        with img_col2:
            if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
            else: st.markdown("<h1 style='text-align: center; font-size: 80px; margin-top: 0;'>🐺</h1>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        new_user = st.text_input("Gib deinen Namen ein (z.B. Malte):")
        
        # NEU: Der Tutor-Name und der Kommunikationsstil
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            tutor_choice = st.text_input("Name deines Tutors:", value="Jordan Belfort")
        with col_t2:
            tutor_style = st.selectbox("Kommunikationsstil:", ["Charakter & Slang", "Rein Sachlich (Klassische KI)"])
            
        beta_code = st.text_input("Beta-Zugangscode:", type="password")
        
        st.write("") 
        if st.button("Lern-Session Starten", use_container_width=True):
            if beta_code != "PITCH2026": st.error("❌ Falscher Zugangscode!")
            elif not new_user: st.error("Bitte gib einen Namen ein!")
            else:
                st.session_state.username = new_user
                if new_user not in database:
                    database[new_user] = {"xp": 0, "tutor_name": tutor_choice, "tutor_style": tutor_style, "history": [], "inventory": []}
                else:
                    database[new_user]["tutor_name"] = tutor_choice
                    database[new_user]["tutor_style"] = tutor_style
                    if "inventory" not in database[new_user]: database[new_user]["inventory"] = []
                
                save_data(database)
                st.session_state.xp = database[new_user]["xp"]
                st.session_state.current_tutor = tutor_choice 
                st.session_state.tutor_style = tutor_style
                st.session_state.messages = database[new_user].get("history", [])
                st.rerun()
    st.stop()

# --- 5.5 POP-UP ANIMATION FÜR DIE LOOTBOX ---
@st.dialog("🎁 Epischer Loot-Drop!", width="small")
def show_lootbox_popup(auto, inv_len):
    anim_key = f"anim_{inv_len}"
    if anim_key not in st.session_state:
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
        st.session_state[anim_key] = True
    
    st.success(f"Herzlichen Glückwunsch! Du hast **{auto}** gezogen!")
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2: st.components.v1.html(render_card_html(auto), height=460)
        
    st.balloons()
    if st.button("Ab in die Garage 🏁", width="stretch"): st.rerun()

# --- DYNAMISCHES SKRIPT VERZEICHNIS ---
verfuegbare_pdfs = []
if os.path.exists("studienmaterial"):
    verfuegbare_pdfs = sorted([f for f in os.listdir("studienmaterial") if f.endswith(".pdf")])

# --- 6. SEITENLEISTE (Inklusive Gamification Toggle!) ---
with st.sidebar:
    st.title("📚 Themenauswahl")
    if verfuegbare_pdfs:
        # NEU: "Alle Foliensätze" als erste Option hinzufügen
        pdf_auswahl = ["Alle Foliensätze"] + verfuegbare_pdfs
        gewaehlter_foliensatz = st.selectbox("Aktueller Foliensatz:", pdf_auswahl)
    else:
        gewaehlter_foliensatz = "Kein Skript gefunden"
        st.warning("Bitte lade PDFs in 'studienmaterial' hoch.")
        
    st.markdown("---")
    st.title("⚙️ Einstellungen")
    st.success(f"Eingeloggt als: {st.session_state.username}")
    
    # NEU: Gamification / Freier Lernmodus Schalter
    lern_modus = st.radio("🎮 System-Modus:", ["XP-Drill-Modus (Mit Quests & Belohnung)", "Freier Lernmodus (Reiner Q&A Sandbox)"])
    
    ki_modus = st.radio("🤖 KI-Engine:", ["Google (Gemini Base)", "Groq (RAG Highspeed)"])
    st.markdown("---")
    
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
    st.title("🃏 Fahrzeug-Quartett")
    st.write(f"**Deine XP:** {st.session_state.xp}")
    
    if st.button("Lootbox öffnen (-30 XP) 🎁", width="stretch"):
        if st.session_state.xp >= 30:
            st.session_state.xp -= 30 
            database[st.session_state.username]["xp"] = st.session_state.xp
            
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
            
            neue_inv_laenge = len(database[st.session_state.username]["inventory"])
            show_lootbox_popup(auto, neue_inv_laenge)
        else:
            st.error("Nicht genug XP!")

    with st.expander("📚 Dein Sammelalbum", expanded=True):
        inventar = database[st.session_state.username].get("inventory", [])
        if not inventar: st.info("Garage ist leer.")
        else:
            for karte, anzahl in {karte: inventar.count(karte) for karte in set(inventar)}.items():
                st.write(f"**Anzahl: {anzahl}x**")
                st.components.v1.html(render_card_html(karte), height=460)

# --- 7. BACKEND WISSEN (Google & RAG für Groq) ---
@st.cache_resource
def get_google_files(filename):
    """Lädt entweder das spezifische PDF oder ALLE PDFs zu Google hoch."""
    hochgeladene_dateien = []
    if google_client and filename != "Kein Skript gefunden":
        dateien_zum_laden = [f for f in os.listdir("studienmaterial") if f.endswith(".pdf")] if filename == "Alle Foliensätze" else [filename]
        
        for datei in dateien_zum_laden:
            file_path = os.path.join("studienmaterial", datei)
            hochgeladene_dateien.append(google_client.files.upload(file=file_path))
    return hochgeladene_dateien

@st.cache_data
def load_pdf_pages(filename):
    """Liest für das Groq-RAG entweder ein PDF oder ALLE PDFs ein."""
    pages_dict = {}
    if filename != "Kein Skript gefunden":
        dateien_zum_laden = [f for f in os.listdir("studienmaterial") if f.endswith(".pdf")] if filename == "Alle Foliensätze" else [filename]
        
        global_page_count = 1
        for datei in dateien_zum_laden:
            file_path = os.path.join("studienmaterial", datei)
            try:
                with open(file_path, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text: 
                            # Den Dateinamen dazuschreiben, damit die KI weiß, woher die Info stammt
                            pages_dict[global_page_count] = f"[Aus {datei}]:\n{text}"
                            global_page_count += 1
            except Exception as e: st.error(f"PDF Lesefehler bei {datei}: {e}")
    return pages_dict

def get_rag_context(prompt, pages_dict, top_k=3):
    # (Diese Funktion bleibt exakt so wie sie in deinem Code war!)
    if not pages_dict: return ""
    stopwords = {"was", "ist", "der", "die", "das", "und", "oder", "ein", "eine", "wie", "erkläre", "bitte"}
    prompt_words = set(re.findall(r'\w{3,}', prompt.lower())) - stopwords
    if not prompt_words: return "\n".join(list(pages_dict.values())[:top_k])
    scored = []
    for p_num, text in pages_dict.items():
        score = sum(text.lower().count(w) for w in prompt_words)
        scored.append((score, p_num, text))
    scored.sort(key=lambda x: x[0], reverse=True)
    context = ""
    for score, p_num, text in scored[:top_k]:
        if score > 0: context += f"\n--- ABSCHNITT {p_num} ---\n{text}\n"
    return context if context else "Keine direkten Treffer auf den Folien gefunden."

# --- 8. SYSTEM PROMPT ANPASSUNG JE NACH MODUS ---

# Neue Session States für das Lernbot-Konzept
if "level" not in st.session_state: st.session_state.level = "klausur"
if "klausur_modus" not in st.session_state: st.session_state.klausur_modus = False
if "tutor_style" not in st.session_state: st.session_state.tutor_style = "Charakter & Slang"

# --- DYNAMISCHE IDENTITÄT ---
if "Sachlich" in st.session_state.tutor_style:
    persona_text = f"""Du bist ein rein sachlicher, hochprofessioneller EBWL-Tutor an der RWTH Aachen.
WICHTIGSTE REGEL: Nutze KEINEN Slang, keine Floskeln und spiele KEINE Rolle. Antworte wie eine klassische, hochintelligente KI: extrem präzise, trocken und direkt auf den Punkt.
KEINE SCHIMPFWÖRTER: Verwende unter keinen Umständen vulgäre, beleidigende oder unangemessene Sprache. Absolute Professionalität ist Pflicht!"""
else:
    persona_text = f"""Du bist {st.session_state.current_tutor}, ein klausurorientierter, aber extrem charakterstarker Tutor für EBWL Studenten an der RWTH Aachen.
WICHTIGSTE REGEL: Du musst die Persönlichkeit, den Slang und die Eigenarten von {st.session_state.current_tutor} PERFEKT imitieren!
KEINE SCHIMPFWÖRTER: Auch wenn du einen harten Slang sprichst, ist vulgäre, beleidigende oder diskriminierende Sprache absolut verboten. Fluche nicht und bleibe immer jugendfrei!"""
    

# Identität
SYSTEM_PROMPT = f"""{persona_text}

DEINE MISSION: Lernende optimal auf ihre EBWL Klausuren vorbereiten, indem du präzise, verständliche und prüfungsrelevante Antworten gibst. Nutze den bereitgestellten Foliensatz als Hauptquelle für deine Erklärungen und beziehe dich immer darauf, wenn es relevant ist. Minimiere die Lernzeit und maximiere das Wissen.
AKTUELLER FOLIENSATZ: {gewaehlter_foliensatz}

# Fachlicher Kontext:
1. Kurs: Einführung in die Betriebswirtschaftslehre (EBWL)
2. Lehrstuhl: Prof. Brettel, TIME Research Area / Innovation & Enterpreneurship Group (WIN)
3. Hochschule: RWTH Aachen
4. Klausurformat: Dynexite (Multiple Choice + offene Fragen), Taschenrechner erlaubt, 60 Minuten

# Wissenensbasis: 
1. Primärquelle: Der aktuell ausgewählte Foliensatz, der als PDF vorliegt. Ziehe alle relevanten Informationen, Beispiele und Erklärungen aus diesem Material.
2. Modulstruktur der Folien: 
    2.1. Unternehmensgrundlagen: Accounting, Finanzen, Investitionen
    2.2. Leadership & Management: Organisation, Controlling, HA
    2.3. Wertschöpfung: Strategie, Marketing, Produktion

# Wie du antworten sollst:
1. Kompakt vor ausführlich: Jeder Satz muss Mehrwert haben. Keine Ausschmückungen, keine Floskeln, kein Geschwätz.
2. Folien-Treue ist Pflicht: Was nicht in den Folien steht, wird klar markiert. Wenn du etwas nicht weißt, sag es direkt, anstatt zu raten oder zu spekulieren.
3. Adaptiv nach Level und Modus: Quiz = knapp. Erklärung = strukturiert. Lernzettel = vollständig.
4. Strukturreiche Formatierung: mit Tabellen, gezielten Emojis als Anker (✅ ❌ 📎 💡 🔥), klaren Überschriften.

# Regeln für Spache und Stil:
1. Sprache & Anrede: Deutsch, sprich den Studenten immer per "Du" an.
2. Länge: Immer aufs Wesentliche beschränken. Niemals eine Wall-of-Text generieren! Nutze Stichpunkte und fette Keywords.
3. Fachbegriffe: Beim ersten Auftreten eines Fachbegriffs nennst du den englischen Terminus und in Klammern die deutsche Übersetzung (z.B. NPV (Kapitalwert), Break-Even (Gewinnschwelle)). Danach nutzt du nur noch den englischen Begriff.
4. Folien-Treue: Was in den Folien steht, ist Gesetz.
5. Adaptive Level-Empfehlung: Wenn du merkst, dass der Student mehrere Fragen in Folge richtig hat, schlage ihm kurz vor, mit '/level vertiefung' das Niveau zu erhöhen. Bei wiederholten Fehlern schlage '/level basic' vor.

# DEINE WEITEREN REGELN:
1. RECHTSCHREIBUNG: Achte strikt auf korrekte Grammatik.
2. QUELLENANGABE: Beziehe dich logisch auf das bereitgestellte Material, vermeide aber konkrete Seitenzahlen, da der Nutzer eventuell nicht exakt die gleiche Version hat. Stattdessen kannst du allgemeine Hinweise geben wie "In den ersten Folien wird das Thema X behandelt..." oder "Später im Skript findest du eine gute Erklärung zu Y...".
3. SEI KRITISCH: Rede nicht um den heißen Brei herum, sondern beantworte die Fragen direkt und ohne Umschweife. Vermeide es, zu sehr auszuschweifen oder unnötige Informationen zu liefern, die nicht direkt zur Beantwortung der Frage beitragen. Rede falsche Antworten aber nicht schön.
4. Verrate niemals das Endergebnis sofort. Nutze Analogien.
"""

# Dynamischer Prompt-Zusatz je nach Modus
if "XP-Drill-Modus" in lern_modus:
    SYSTEM_PROMPT += "\n5. XP VERGEBEN: Wenn der Nutzer eine Frage inhaltlich richtig beantwortet oder eine Aufgabe perfekt löst, schreibe exakt '[+10 XP]' oder '[+20 XP]' ganz ans Ende deiner Nachricht!"
else:
    SYSTEM_PROMPT += "\n5. FREIER LERNMODUS: Der Student möchte sich ungezwungen mit dir unterhalten oder Unklarheiten klären. Vergib KEINE XP und schreibe niemals '[+10 XP]'. Beantworte einfach seine Fragen im gewohnten Charakter-Slang."

LADE_ZITATE = [
    "Preis ist das, was du zahlst. Wert ist das, was du bekommst. - Warren Buffett",
    "Der Markt kann länger irrational bleiben, als du liquide. - Keynes",
    "Zinseszins ist das achte Weltwunder. - Einstein",
    "Das Geheimnis des Erfolgs ist, den Standpunkt des anderen zu verstehen. - Henry Ford",
    "Risiko entsteht dann, wenn man nicht weiß, was man tut. - Warren Buffett"
    "Erfolg hat drei Buchstaben: TUN. - Goethe"
]

# --- 9. BENUTZEROBERFLÄCHE & CHAT LOGIK ---
st.title(f"Willkommen in der Session, {st.session_state.username}! 🐺")

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]): 
        st.markdown(message["content"])
        
        # NEU: Lade den Button aus dem Gedächtnis, falls es ein Lernzettel war
        if "pdf_data" in message:
            st.download_button(
                label="📄 Deinen Lernzettel als PDF herunterladen",
                data=message["pdf_data"],
                file_name=message["pdf_name"],
                mime="application/pdf",
                key=f"dl_btn_{i}"
            )
            
        # NEU: Lade die Karteikarten aus dem Gedächtnis
        if message.get("is_flashcard"):
            display_html_flashcards(message["content"])

st.markdown("<div style='text-align: center; font-size: 13px; color: #888; margin-top: 30px; margin-bottom: 5px;'>🐺 Wolf of Wüllnerstraße ist eine KI und kann Fehler machen. Bitte überprüfe wichtige Fakten.</div>", unsafe_allow_html=True)

if prompt := st.chat_input(f"Nachricht oder /befehl eingeben..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # ==========================================
    # 💥 DER NEUE SLASH-COMMAND PARSER
    # ==========================================
    system_override = ""
    direct_response = None
    user_input_lower = prompt.strip().lower()

    # 1. Befehle, die Python direkt beantwortet (Ohne KI-Aufruf)
    if user_input_lower == "/menu":
        direct_response = """**🐺 Wolf of Wüllnerstraße - EBWL-Tutor Menü:**
        `/quiz [Thema]` - MC- & offene Fragen abfragen
        `/klausur` - Probeklausur starten (Auswertung am Ende)
        `/erklär [Konzept]` - Strukturierte Erklärung
        `/rechnen [Thema] (/kurz)` - Rechenaufgabe Schritt-für-Schritt (oder nur Ergebnis)
        `/karten` - Kompakte Karteikarten
        `/zettel [Thema]` - Kompakter Lernzettel
        `/merk [Thema]` - Eselsbrücken & Memory-Toolkit
        `/level [basic/klausur/vertiefung]` - Schwierigkeit anpassen
        `/stats` - Deinen Session-Fortschritt anzeigen
        `/taktik` - Dynexite Klausurstrategie"""

    elif user_input_lower.startswith("/level"):
        neues_level = user_input_lower.replace("/level", "").strip()
        if neues_level in ["basic", "klausur", "vertiefung"]:
            st.session_state.level = neues_level
            direct_response = f"✅ Schwierigkeitsgrad erfolgreich auf **{neues_level.upper()}** gesetzt!"
        else:
            direct_response = "❌ Bitte wähle: `/level basic`, `/level klausur` oder `/level vertiefung`."

    # 2. Befehle, die eine strenge KI-Anweisung (System Override) erfordern
    elif user_input_lower.startswith("/stats"):
        system_override = "Der Nutzer ruft /stats auf. Analysiere den bisherigen Chatverlauf. Gib eine kompakte Schätzung seiner Trefferquote, nenne sein schwächstes Modul/Thema basierend auf seinen Fehlern und gib eine konkrete Lernempfehlung. Mach es in einer übersichtlichen Liste."
    
    elif user_input_lower.startswith("/taktik"):
        system_override = "Der Nutzer ruft /taktik auf. Berate ihn aktiv zur Klausurtaktik (60 Min Dynexite EBWL). Gehe zwingend auf diese Punkte ein: 1. Dynexite-spezifische Tipps (MC-Strategie bei Unsicherheit, Navigation, Bookmarking). 2. Zeitmanagement (Puffer, Verteilung). 3. Reihenfolge der Aufgaben (Sichere zuerst). Mach es kompakt, strukturiert und motivierend."

    elif user_input_lower.startswith("/rechnen"):
        if "/kurz" in user_input_lower:
            system_override = "Rechne das genannte Thema. Da /kurz aktiv ist: Zeige NUR das Ergebnis und die Schlüsselformel. Lasse alle Zwischenschritte weg."
        else:
            system_override = f"Rechne das genannte Thema. Mache jeden Rechenschritt EINZELN nachvollziehbar. Passe die Erklärung an das aktuelle Level ({st.session_state.level}) an: Bei 'basic' mit vielen textlichen Erläuterungen, bei 'klausur' extrem kompakt, bei 'vertiefung' ergänze alternative Lösungsansätze."
    
    elif user_input_lower.startswith("/klausur"):
        if "auswerten" in user_input_lower or "beenden" in user_input_lower:
            st.session_state.klausur_modus = False
            system_override = "KLAUSUR BEENDET. Werte jetzt ALLE vorherigen Antworten des Nutzers in dieser Klausur-Session auf einmal aus. Gib eine Punktzahl, zeige die Fehler und erkläre die korrekten Lösungen streng aber fair."
        else:
            st.session_state.klausur_modus = True
            system_override = "STARTE KLAUSURMODUS. Suche im Kontext nach hochgeladenen Altklausuren. Generiere basierend auf deren Stil, Umfang und Länge eine neue, prüfungsnahe Klausurfrage aus den Folien. WICHTIG: Gib die Lösung NICHT vor. Werte noch nichts aus. Stelle einfach die erste Frage!"

    elif st.session_state.klausur_modus:
        system_override = "KLAUSURMODUS AKTIV. Der Nutzer hat geantwortet. WICHTIGSTE REGEL: BEWERTE DIE ANTWORT NICHT! Sag nicht 'Richtig' oder 'Falsch'. Korrigiere noch nichts. Nimm die Antwort nur wortlos hin und stelle direkt die NÄCHSTE Klausurfrage. Erinnere den Nutzer am Ende kurz: 'Tippe /klausur auswerten, um die Klausur zu beenden und dein Ergebnis zu sehen.'"

    elif user_input_lower.startswith("/erklär"):
        system_override = "WENDE ZWINGEND DIESES FORMAT AN: 1. Kurzdefinition (1 Satz), 2. Ausführliche Erklärung (3-6 Sätze), 3. Formel (falls relevant), 4. Zahlenbeispiel, 5. Typische Klausurfalle (1-2 Sätze), 6. Folien-Referenz. Schließe mit: 'Verstanden? Vertiefen / Quiz / Lernzettel?'"

    elif user_input_lower.startswith("/zettel"):
        system_override = "Erstelle einen extrem kompakten, übersichtlichen Lernzettel zu diesem Thema (Definition, Erklärung, Beispiel, Formel, Klausurhinweis). Nutze Tabellen, sauberes Markdown und markiere Inhalte mit [Hochrelevant], [Wichtig] oder [Nice-to-know]."

    elif user_input_lower.startswith("/karten"):
        system_override = "Erstelle 3-5 kompakte, auf die Klausur getrimmte Karteikarten zum aktuellen Thema. Format: **Vorderseite (Frage):** ... | **Rückseite (Antwort):** ... (in knappen Stichpunkten)."

    elif user_input_lower.startswith("/taktik"):
        system_override = "Gib taktische Ratschläge für eine 60-minütige Dynexite-Klausur in EBWL. Themen: Zeitmanagement, MC-Strategie bei Unsicherheit, Navigation und Bookmarking. Sei prägnant."

    elif user_input_lower.startswith("/quiz"):
        system_override = "Stelle eine kompakte Multiple-Choice oder offene Frage zum gewünschten Thema. Format: Frage X/N | Modul | Level. Gib Optionen A-D an. Warte auf die Antwort."

    elif user_input_lower.startswith("/rechnen"):
        if "/kurz" in user_input_lower:
            system_override = "Rechne das genannte Thema. Da /kurz aktiv ist: Zeige NUR das Ergebnis und die Schlüsselformel. Keine Zwischenschritte."
        else:
            system_override = "Rechne das genannte Thema. Zeige die Lösung Schritt-für-Schritt, sodass jeder Rechenschritt einzeln nachvollziehbar ist."
    elif user_input_lower.startswith("/merk"):
        system_override = """Generiere ein 'Memory-Toolkit' für das genannte Thema. Halte dich EXAKT an diese Struktur:
        1. 🧠 **Der Reim / Das Akronym:** Erfinde einen griffigen Spruch oder ein Akronym, um sich die Bestandteile zu merken.
        2. 🦄 **Die absurde Story:** Erfinde eine völlig übertriebene, bizarre oder lustige Mini-Geschichte (max. 3 Sätze), die die Fakten verknüpft. Das Gehirn merkt sich Absurdes am besten!
        3. 👁️ **Die visuelle Brücke:** Beschreibe kurz, wie man sich das Konzept bildlich auf dem Klausur-Schmierblatt aufzeichnen oder vorstellen sollte (z.B. 'Stell dir einen Bruchstrich vor...').
        Schließe mit: 'Welche Brücke hilft dir am meisten?'"""

    # 3. Level-Modifikator hinzufügen
    level_instruction = {
        "basic": "Level BASIC: Erkläre alles sehr einfach. Reagiere bei Fehlern aufbauend ('Nicht ganz, denk nochmal an...').",
        "klausur": "Level KLAUSUR: Antworte präzise auf RWTH-Klausurniveau. Reagiere bei Fehlern streng und sachlich ('Falsch. Richtig ist X, weil...').",
        "vertiefung": "Level VERTIEFUNG: Ergänze Standard-BWL Wissen über die Folien hinaus (klar markiert). Stelle Sokratische Gegenfragen, wenn der Nutzer Fehler macht."
    }
    
    FINAL_SYSTEM_PROMPT = SYSTEM_PROMPT + "\n" + level_instruction[st.session_state.level]

    if system_override:
        FINAL_SYSTEM_PROMPT += "\n\nSONDERBEFEHL FÜR DIESE NACHRICHT:\n" + system_override
    if "XP-Drill-Modus" in lern_modus and not st.session_state.klausur_modus:
        FINAL_SYSTEM_PROMPT += "\nXP VERGEBEN: Wenn inhaltlich richtig geantwortet wird, schreibe exakt '[+10 XP]' oder '[+20 XP]' ans Ende."

    # ==========================================
    # 💥 AUSFÜHRUNG
    # ==========================================
    if direct_response:
        # Python antwortet direkt ohne API
        st.markdown(direct_response)
        st.session_state.messages.append({"role": "assistant", "content": direct_response})
        st.rerun()
    else:
        # API Aufruf an Groq / Gemini
        with st.chat_message("assistant"):
            spinner_text = f"{st.session_state.current_tutor} analysiert... | 💡 {random.choice(LADE_ZITATE)}"
            with st.spinner(spinner_text):
                try:
                    answer = ""
                    # --- GROQ PFAD ---
                    if "Groq" in ki_modus:
                        if not groq_client: st.error("Groq API Key fehlt!")
                        else:
                            pages_dict = load_pdf_pages(gewaehlter_foliensatz)
                            rag_context = get_rag_context(prompt, pages_dict)
                            groq_messages = [{"role": "system", "content": FINAL_SYSTEM_PROMPT + "\n\nAUSZUG AUS DEM SKRIPT:\n" + rag_context}]
                            for msg in st.session_state.messages[-8:]: groq_messages.append({"role": msg["role"], "content": msg["content"]})
                            
                            completion = groq_client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=groq_messages
                            )
                            answer = completion.choices[0].message.content

                    # --- GOOGLE PFAD ---
                    else:
                        if not google_client: st.error("Google API Key fehlt!")
                        else:
                            google_files = get_google_files(gewaehlter_foliensatz)
                            history_for_api = [msg["content"] for msg in st.session_state.messages[-8:]]
                            
                            full_contents = []
                            # NEU: .extend nutzen, da google_files jetzt eine Liste ist
                            if google_files: full_contents.extend(google_files)
                            full_contents.extend(history_for_api)
                            
                            response = google_client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=full_contents,
                                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
                            )
                            answer = response.text
                    
                    # --- ANTWORT VERARBEITEN ---
                    if answer:
                        # 1. Prüfen, ob ein PDF generiert werden soll
                        pdf_bytes = None
                        pdf_filename = None
                        if prompt.strip().lower().startswith("/zettel"):
                            pdf_bytes = generate_pdf_bytes(prompt, answer)
                            pdf_filename = f"Lernzettel_{gewaehlter_foliensatz.replace('.pdf','')}.pdf"

                        # 2. Nachricht inkl. aller Dateien ins Gedächtnis packen
                        neue_nachricht = {"role": "assistant", "content": answer}
                        if pdf_bytes:
                            neue_nachricht["pdf_data"] = pdf_bytes
                            neue_nachricht["pdf_name"] = pdf_filename
                        if prompt.strip().lower().startswith("/karten"):
                            neue_nachricht["is_flashcard"] = True
                            
                        st.session_state.messages.append(neue_nachricht)

                        # 3. XP Berechnen
                        if "XP-Drill-Modus" in lern_modus and not st.session_state.klausur_modus:
                            xp_matches = re.findall(r'\[\+(\d+)\s*XP\]', answer)
                            if xp_matches:
                                total_gained_xp = sum(int(match) for match in xp_matches)
                                st.session_state.xp += total_gained_xp
                                database[st.session_state.username]["xp"] = st.session_state.xp
                                st.balloons()
                                
                        database[st.session_state.username]["history"] = st.session_state.messages
                        save_data(database)
                        
                        # 4. PITCH-TRICK: Ein kurzer Rerun baut die Seite neu auf und holt den 
                        # Download-Button und die Karteikarten sicher aus der Historie (Block 2).
                        time.sleep(1)
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Fehler bei der Server-Anfrage: {e}")
                            
                
