import streamlit as st
import cv2
import requests
from bs4 import BeautifulSoup
import datetime
from PIL import Image
import numpy as np
import pandas as pd
import os
from pygame import mixer
import io

# Configuración inicial de la página
st.set_page_config(
    page_title="Sistema de Registro QR",
    page_icon="📱",
    layout="wide"
)

# Inicializar el sistema de sonido
# Inicializar el sistema de sonido
try:
    mixer.init()
except Exception as e:
    st.warning("El Sistema de sonido no esta disponible")
    
# Función para decodificar QR usando OpenCV
def decode_qr_with_opencv(image_np):
    qr_code_detector = cv2.QRCodeDetector()
    data, bbox, _ = qr_code_detector.detectAndDecode(image_np)
    return data if data else "No se encontró ningún código QR."

# Función para decodificar QR
def decode_qr_data(image):
    """
    Decodifica un código QR desde una imagen usando OpenCV.
    
    Args:
        image: Imagen PIL o ruta a la imagen
    
    Returns:
        str: Datos decodificados del QR o mensaje de error
    """
    try:
        # Si la entrada es una ruta de archivo, abrir la imagen
        if isinstance(image, str):
            image = Image.open(image)
        
        # Convertir la imagen PIL a un array numpy
        if isinstance(image, Image.Image):
            # Convertir a RGB si es necesario
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image_np = np.array(image)
        else:
            st.error("Formato de imagen no soportado")
            return "Error en formato de imagen"

        # Decodificar el código QR usando OpenCV
        return decode_qr_with_opencv(image_np)
            
    except Exception as e:
        st.error(f"Error al decodificar QR: {str(e)}")
        return f"Error: {str(e)}"

# Función para reproducir sonido de éxito
def play_success_sound():
    try:
        duration = 0.1  # segundos
        freq = 1000  # Hz
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * freq * t)
        sound = (signal * 32767).astype(np.int16)
        
        sound_file = io.BytesIO()
        import wave
        with wave.open(sound_file, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(sound.tobytes())
        
        sound_file.seek(0)
        mixer.music.load(sound_file)
        mixer.music.play()
    except Exception as e:
        st.warning(f"No se pudo reproducir el sonido: {str(e)}")

# Función para guardar datos en Excel
def save_to_excel(data, filename="registros.xlsx"):
    try:
        # Crear el directorio si no existe
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        try:
            # Intentar leer el archivo existente
            df_existing = pd.read_excel(filename)
            df_new = pd.DataFrame([data])
            df_updated = pd.concat([df_existing, df_new], ignore_index=True)
        except FileNotFoundError:
            # Si el archivo no existe, crear uno nuevo
            df_updated = pd.DataFrame([data])
        
        # Guardar el DataFrame actualizado
        df_updated.to_excel(filename, index=False)
        return True
    except Exception as e:
        st.error(f"Error al guardar en Excel: {str(e)}")
        return False

# Función para procesar la URL y obtener datos
def process_url(url):
    try:
        url_convertida = url.replace("idperfil=", "action=consulta&id=")
        response = requests.get(url_convertida, timeout=10)  # Añadido timeout
        
        if response.status_code != 200:
            st.error(f"Error al acceder a la URL: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraer datos
        data = {
            'nombre': None,
            'identificacion': None,
            'correo': None,
            'rol': None,
            'fecha_registro': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Nombre
        h5_content = soup.find('h5', style="text-align: center;")
        if h5_content:
            data['nombre'] = h5_content.string
        
        # Rol
        h6_content = soup.find('h6', style="text-align: center; line-height: 10px")
        if h6_content:
            data['rol'] = h6_content.string
        
        # Identificación y Correo
        h6_elements = soup.find_all('h6', style="text-align: center; line-height: 15px")
        for element in h6_elements:
            if "No. Identificación" in element.text:
                data['identificacion'] = element.text.replace("No. Identificación:", "").strip()
            elif "Correo Institucional" in element.text:
                data['correo'] = element.get_text(separator=" ").replace("Correo Institucional:", "").strip()
        
        # Verificar si se obtuvieron todos los datos necesarios
        if not all([data['nombre'], data['identificacion'], data['correo'], data['rol']]):
            st.warning("Algunos datos no pudieron ser extraídos correctamente")
        
        return data
        
    except requests.RequestException as e:
        st.error(f"Error en la solicitud HTTP: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return None

# Interfaz principal
def main():
    # Título y descripción
    st.title("📱 Sistema de Registro QR")
    st.markdown("""
    ### Bienvenido al Sistema de Registro
    Este sistema permite registrar usuarios mediante lectura de códigos QR.
    """)
    
    # Crear columnas para mejor organización
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Botón de activación de cámara más atractivo
        st.markdown("### 📸 Control de Cámara")
        camera_placeholder = st.empty()
        enable = st.toggle('Activar Cámara', help='Activa/Desactiva la cámara web')
        
        if enable:
            picture = st.camera_input('Capturar QR', key='camera')
            if picture:
                # Procesar la imagen capturada
                image = Image.open(picture)
                
                # Mostrar spinner mientras se procesa
                with st.spinner('Procesando código QR...'):
                    qr_data = decode_qr_data(image)
                
                if qr_data and qr_data != "No se encontró ningún código QR.":
                    # Reproducir sonido de éxito
                    play_success_sound()
                    
                    # Procesar datos
                    with st.spinner('Obteniendo datos...'):
                        user_data = process_url(qr_data)
                    
                    if user_data:
                        # Guardar en Excel
                        if save_to_excel(user_data):
                            st.success("✅ Registro guardado exitosamente!")
                        else:
                            st.error("❌ Error al guardar el registro")
                        
                        # Mostrar datos
                        with col2:
                            st.markdown("### 📋 Datos Registrados")
                            st.info(f"""
                            **Nombre:** {user_data['nombre']}  
                            **ID:** {user_data['identificacion']}  
                            **Rol:** {user_data['rol']}  
                            **Correo:** {user_data['correo']}  
                            **Fecha:** {user_data['fecha_registro']}
                            """)
                else:
                    st.warning("⚠️ No se detectó ningún código QR válido")
    
    # Mostrar historial de registros
    if st.checkbox("📊 Ver Historial de Registros"):
        try:
            df = pd.read_excel("registros.xlsx")
            st.dataframe(df, use_container_width=True)
            
            # Añadir botón para descargar Excel
            if not df.empty:
                st.download_button(
                    label="⬇️ Descargar Registros",
                    data=df.to_csv(index=False).encode('utf-8'),
                    file_name='registros.csv',
                    mime='text/csv'
                )
        except FileNotFoundError:
            st.info("No hay registros guardados aún")
        except Exception as e:
            st.error(f"Error al cargar los registros: {str(e)}")

if __name__ == "__main__":
    main()
