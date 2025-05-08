from flask import Flask, render_template, request, jsonify
import subprocess
import os
import re
from PIL import Image
from PIL.ExifTags import TAGS
import piexif
from werkzeug.utils import secure_filename
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import exifread
from GPSPhoto import gpsphoto

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_results(raw_output, tool_name):
    """Formate les résultats pour l'affichage"""
    if not raw_output:
        return "Aucune présence trouvée"
    
    results = []
    for line in raw_output.split('\n'):
        if 'http' in line:
            url = re.search(r'(https?://[^\s]+)', line).group(1)
            if tool_name == "sherlock":
                platform = re.search(r'\[\+\] (.*?):', line)
                platform_name = platform.group(1) if platform else "Lien"
                results.append(f'<div class="result-item"><span class="platform">{platform_name}</span>: <a href="{url}" target="_blank" class="result-link">{url}</a></div>')
            else:
                results.append(f'<div class="result-item"><a href="{url}" target="_blank" class="result-link">Profil trouvé</a>: {url}</div>')
        elif ':' in line and tool_name == "socialscan":
            parts = line.split(':', 1)
            if len(parts) > 1:
                status_class = "available" if "available" in parts[1].lower() else "unavailable"
                results.append(f'<div class="result-item"><span class="platform">{parts[0].strip()}</span>: <span class="status {status_class}">{parts[1].strip()}</span></div>')
    
    return ''.join(results) if results else "Aucun résultat trouvé"

def analyze_metadata(filepath):
    """Analyse complète des métadonnées d'une image avec EXIF et GPS"""
    try:
        metadata = {}
        
        # Informations basiques avec Pillow
        with Image.open(filepath) as img:
            metadata['Format'] = img.format
            metadata['Dimensions'] = f"{img.width}x{img.height} pixels"
            metadata['Mode'] = img.mode
            
            # EXIF de base avec Pillow
            if hasattr(img, '_getexif') and img._getexif():
                for tag, value in img._getexif().items():
                    decoded = TAGS.get(tag, tag)
                    metadata[f'EXIF_{decoded}'] = str(value)
        
        # Analyse EXIF plus poussée avec exifread
        with open(filepath, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            for tag, value in tags.items():
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
                    metadata[str(tag)] = str(value)
        
        # Extraction des coordonnées GPS
        try:
            gps_data = gpsphoto.getGPSData(filepath)
            if gps_data:
                metadata['GPS_Latitude'] = gps_data.get('Latitude', 'N/A')
                metadata['GPS_Longitude'] = gps_data.get('Longitude', 'N/A')
                metadata['GPS_Altitude'] = gps_data.get('Altitude', 'N/A')
                metadata['Google_Maps_Link'] = f"https://www.google.com/maps?q={gps_data.get('Latitude')},{gps_data.get('Longitude')}"
        except Exception as gps_error:
            metadata['GPS_Error'] = str(gps_error)
        
        return metadata
        
    except Exception as e:
        return {"Erreur": str(e)}

def google_reverse_search(filepath):
    """Recherche d'image inversée avec extraction des résultats - Version corrigée"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.google.com/imghp")
        
        # Attendre que la page soit chargée
        time.sleep(2)
        
        # Cliquer sur le bouton de recherche par image
        try:
            camera_icon = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-label='Recherche par image']"))
            )
            camera_icon.click()
        except Exception as e:
            print(f"Erreur recherche icône caméra: {str(e)}")
            # Fallback alternative
            try:
                driver.get("https://www.google.com/imghp?hl=en")
                time.sleep(2)
                camera_icon = driver.find_element(By.XPATH, "//div[@aria-label='Search by image']")
                camera_icon.click()
            except Exception as fallback_error:
                print(f"Erreur fallback: {str(fallback_error)}")
                driver.quit()
                return None
        
        # Attendre que le dialogue d'upload apparaisse
        time.sleep(2)
        
        # Upload de l'image
        try:
            upload_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            upload_input.send_keys(os.path.abspath(filepath))
        except Exception as e:
            print(f"Erreur upload image: {str(e)}")
            driver.quit()
            return None
        
        # Attendre les résultats
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-ri]"))
            )
            time.sleep(3)  # Attendre supplémentaire pour le chargement
            
            # Récupérer l'URL de recherche
            search_url = driver.current_url
            
            # Récupérer les premiers résultats
            results = []
            match_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-ri]")[:5]
            
            for elem in match_elements:
                try:
                    title = elem.find_element(By.CSS_SELECTOR, "h3").text
                    link = elem.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    results.append({"title": title, "url": link})
                except:
                    continue
            
            driver.quit()
            return {
                "search_url": search_url,
                "matches": results
            }
            
        except Exception as e:
            print(f"Erreur attente résultats: {str(e)}")
            # Essayer de récupérer quand même l'URL
            search_url = driver.current_url
            driver.quit()
            return {
                "search_url": search_url,
                "matches": []
            }
            
    except Exception as e:
        print(f"Erreur globale recherche image: {str(e)}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    result_sherlock = ""
    result_socialscan = ""
    
    if request.method == "POST" and 'username' in request.form:
        username = request.form["username"].strip()
        username = re.sub(r'[^a-zA-Z0-9_-]', '', username)
        
        try:
            output_sherlock = subprocess.check_output(
                f"sherlock {username} --print-found",
                shell=True,
                universal_newlines=True,
                stderr=subprocess.STDOUT
            )
            result_sherlock = format_results(output_sherlock, "sherlock")
        except subprocess.CalledProcessError as e:
            result_sherlock = f'<div class="error">Erreur Sherlock:<br>{e.output}</div>'

        try:
            output_socialscan = subprocess.check_output(
                f"python3 -m socialscan {username}",
                shell=True,
                universal_newlines=True,
                stderr=subprocess.STDOUT
            )
            result_socialscan = format_results(output_socialscan, "socialscan")
        except subprocess.CalledProcessError as e:
            result_socialscan = f'<div class="error">Erreur Socialscan:<br>{e.output}</div>'

    return render_template("index.html", 
                         result_sherlock=result_sherlock,
                         result_socialscan=result_socialscan)

@app.route('/reverse-image', methods=['POST'])
def handle_image_upload():
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "Aucun fichier envoyé"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "error": "Aucun fichier sélectionné"}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            metadata = analyze_metadata(filepath)
            google_results = google_reverse_search(filepath)
            
            os.remove(filepath)
            
            return jsonify({
                "metadata": metadata,
                "search_url": google_results['search_url'] if google_results else None,
                "matches": google_results['matches'] if google_results else [],
                "success": True
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    return jsonify({"success": False, "error": "Format non supporté (JPG/PNG/WEBP/GIF)"}), 400

if __name__ == '__main__':
    app.run(debug=True)
