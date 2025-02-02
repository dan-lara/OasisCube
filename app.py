import streamlit as st
import requests
from utils import *
from PIL import Image
import pandas as pd

if not PLANTNET_API_KEY:
    st.error("Variables d'environnement non configurées correctement. Vérifiez le fichier .env")
    st.stop()

if not check_password():
    st.stop()

conn = get_db_connection()
run_script(conn, read_scrpit("predictions.sql"))

def save_prediction(conn, username, photo, result):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO predictions 
        (username, photo_data, photo_mime_type, result, project_id) 
        VALUES (?, ?, ?, ?, ?)
    """, (
        username,
        photo.getvalue() if photo else None,
        photo.type if photo else None,
        json.dumps(result),
        result['query']['project']
    ))
    conn.commit()
    return cur.lastrowid

st.set_page_config(
    page_title="Classification des Plantes",
    page_icon=":recycle:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/dan-lara/',
        'Report a bug': "https://github.com/dan-lara/",
        'About': "# C'est le Demo de l'application de classification des plantes"
    }
)

def main_app():
    draw_logo()
    st.title("Classification des Plantes v1")
    st.subheader(f"Bienvenue, {st.session_state.user}!")
    projects = load_projects()
    
    with st.sidebar:
        st.header("Sélection du Projet")
        project_options = {project['title']: project['id'] for project in projects}
        selected_project_title = st.selectbox(
            "Choisissez un projet",
            list(project_options.keys()),
            index=list(project_options.keys()).index("Middle Europe") if "Middle Europe" in project_options else 0
        )
        selected_project_id = project_options[selected_project_title]
        
        st.markdown("---")
        st.markdown("### Informations sur le Projet Sélectionné")
        project_info = next(p for p in projects if p['id'] == selected_project_id)
        st.write(f"**Description:** {project_info['description']}")
        st.write(f"**Nombre d'Espèces:** {project_info['speciesCount']:,}")
        
    col1, col2 = st.columns([1, 1]) 
        
    with col1:
        st.header("Télécharger une Image de Plante")
        upload_option = st.radio("Choisissez une option", ("Télécharger depuis la galerie", "Prendre une photo"))

        if upload_option == "Télécharger depuis la galerie":
            uploaded_image = st.file_uploader("Choisissez une image...", type=['jpg', 'jpeg', 'png'])
        else:
            uploaded_image = st.camera_input("Prendre une photo")
        
        if uploaded_image:
            image = Image.open(uploaded_image)
            st.image(image, caption="Image de Plante Téléchargée", use_container_width=True)
            
            if uploaded_image:
                with st.spinner("Analyse de l'image..."):
                    api_url = f"https://my-api.plantnet.org/v2/identify/{selected_project_id}?api-key={PLANTNET_API_KEY}"
                    
                    import io
                    image_bytes = io.BytesIO()
                    image.save(image_bytes, format='JPEG')
                    image_bytes.seek(0)
                    files = {
                        "images": ("photo.jpg", image_bytes, "image/jpeg")
                    }
                    data = {
                        "organs": "auto",
                    }
                    with st.spinner(f"Identification de la plante sur la photo..."):
                        response = requests.post(api_url, files=files, data=data)
                    if response.status_code == 200:
                        result = response.json()
                        save_prediction(conn, st.session_state.user, uploaded_image, result)
                    else:
                        st.error(f"Erreur lors de l'identification de la plante sur la photo : {response.text}")
                                    
                    st.session_state.prediction_result = result
    
    with col2:
        st.header("Résultats de l'Identification")
        if uploaded_image and 'prediction_result' in st.session_state:
            display_prediction_results(st.session_state.prediction_result)

def historique():
    if not check_password():
        st.stop()
        
    st.title("Historique des Prédictions")
    st.write(f"Bienvenue, {st.session_state.user}!")

    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, username, result, created_at
        FROM predictions 
        WHERE username = ? 
        ORDER BY created_at DESC""", 
        (st.session_state.user,)
    )
    predictions = cur.fetchall()
    
    if not predictions:
        st.info("Aucune prédiction trouvée.")
        return
    
    processed_data = []
    dfs = []
    
    for pred in predictions:
        id_, username, result_str, timestamp = pred
        current_data = []
        try:
            result = json.loads(result_str.replace("'", '"'))
            
            for pred_result in result.get('results', []):
                species = pred_result['species']
                
                prediction_data = {
                    'ID': id_,
                    'Date': timestamp,
                    'Score': f"{pred_result['score']:.2%}",
                    'Famille': species['family']['scientificName'],
                    'Genre': species['genus']['scientificName'],
                    'Nom Scientifique': species['scientificName'],
                    'Noms Communs': ', '.join(species.get('commonNames', []))[:50],
                    'GBIF ID': pred_result.get('gbif', {}).get('id', ''),
                    'POWO ID': pred_result.get('powo', {}).get('id', ''),
                    'Projet': result['query']['project'],
                }
                
                if result.get('predictedOrgans'):
                    organ = result['predictedOrgans'][0]
                    prediction_data.update({
                        'Organe Détecté': organ['organ'],
                        'Confiance Détection': f"{organ['score']:.2%}"
                    })
                
                processed_data.append(prediction_data)
                current_data.append(prediction_data)
        except json.JSONDecodeError:
            st.error(f"Erreur lors du traitement de la prédiction {id_}")
                    
        df = pd.DataFrame(current_data)  
        dfs.append(df) 
        
    df = pd.DataFrame(processed_data)   

    st.subheader("Statistiques")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total des Prédictions", len(df))        
        st.metric("Projets Différents", df['Projet'].nunique())
    with col2:
        st.metric("Confiance Moyenne", f"{df['Score'].str.rstrip('%').astype(float).mean():.1f}%")
        st.metric("Confiance Moyenne Organe", f"{df['Confiance Détection'].str.rstrip('%').astype(float).mean():.1f}%")
        
    with col3:
        st.metric("Familles Différentes", df['Famille'].nunique())        
        st.metric("Genres Différents", df['Genre'].nunique())
        st.metric("Espèces Différentes", df['Nom Scientifique'].nunique())
        
    for df in dfs:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_order=[
                'ID', 'Date', 'Score', 'Famille', 'Genre', 
                'Nom Scientifique', 'Noms Communs', 'Organe Détecté', 
                'Confiance Détection', 'GBIF ID', 'POWO ID', 'Projet'
            ]
        )
        
def main():
    pg = st.navigation([
        st.Page(main_app,       icon=":material/search:",   title="Analyse"),
        st.Page(historique,    icon=":material/history:",   title="Historique")
    ])
    pg.run()

if __name__ == "__main__":
    main()
