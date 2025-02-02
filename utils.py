import streamlit as st
import hmac
import sqlite3
import json
import requests
import os
import json
import geocoder
import folium
from streamlit_folium import folium_static
from dotenv import load_dotenv

load_dotenv()
PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY")


def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            st.session_state["user"] = st.session_state["username"]
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False

def display_prediction_results(result):
    if not result.get('results'):
        return
    
    for pred in result['results']:
        species_info = pred['species']
        
        # Create a container for each prediction
        with st.container():
            st.markdown(f"### {pred['species']['scientificName']} -   Score: {pred['score']:.2%}")
            
            # Create three columns for organized display
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Classification**")
                st.write("Family:", species_info['family']['scientificName'])
                st.write("Genus:", species_info['genus']['scientificName'])
                
            with col2:
                st.markdown("**Species**")
                st.write("Scientific Name:", species_info['scientificName'])
                if species_info.get('commonNames'):
                    st.write("Common Names:", ", ".join(species_info['commonNames']))
                    
            with col3:
                st.markdown("**References**")
                if pred.get('gbif'):
                    st.write("GBIF ID:", pred['gbif']['id'])
                if pred.get('powo'):
                    st.write("POWO ID:", pred['powo']['id'])
            
            st.divider()


def get_db_connection():
    conn = sqlite3.connect("predictions.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def read_scrpit(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError as e:
        print(f"Erreur lors de la lecture du fichier SQL: {e}")
        exit(1)

def run_script(conn, sql_script: str):
    try:
        conn.executescript(sql_script)
        print("Script exécuté avec succès!")
    except sqlite3.Error as e:
        print(f"Erreur lors de l'exécution du script SQL: {e}")
    finally:
        conn.commit()

def load_projects(cache=True):
    if not cache:
        api_url = f"https://my-api.plantnet.org/v2/projects?api-key={PLANTNET_API_KEY}"
        response = requests.get(api_url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erro ao obter projetos: {response.text}")
            return None
    else:
        with open('projects.json', 'r') as f:
            return json.load(f)
        
def draw_logo():
    st.logo(
        image = os.getenv("LOGO_PATH"),
        icon_image = os.getenv("ICON_PATH"),
        size = "large"
    ) 
        
def get_location():
    g = geocoder.ip('me')
    return g

def plot_location(g):
    if g.ok:
        latitude, longitude = g.latlng
        st.write(f"Sua localização aproximada: Latitude {latitude}, Longitude {longitude}")
    else:
        st.warning("Não foi possível determinar sua localização")
    if g.ok:
        # Cria um mapa centrado na localização do usuário
        map_center = [latitude, longitude]
        m = folium.Map(location=map_center, zoom_start=13)

        # Adiciona um marcador na localização do usuário
        folium.Marker(location=map_center, popup="Você está aqui").add_to(m)

        # Exibe o mapa no Streamlit
        folium_static(m)