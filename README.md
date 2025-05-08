# 🕵️‍♂️ OSINT & Image Metadata Analyzer

Un outil web simple et puissant pour l'analyse OSINT :

- 🔍 Recherche de profils en ligne avec **Sherlock** et **Socialscan**
- 🖼️ Analyse complète des **métadonnées d'image** (EXIF, GPS)
- 🔁 **Recherche inversée d’image** via Google Images

## 🚀 Fonctionnalités

- Entrer un pseudo et détecter sa présence sur diverses plateformes
- Uploader une image et récupérer :
  - Le format, dimensions, et données EXIF
  - Les coordonnées GPS (si présentes)
  - Des correspondances via Google Images

---

## ⚙️ Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/fofademba/osint-image-analyzer.git
cd osint-image-analyzer


### 2. Créer un environnement virtuel (optionnel mais conseillé)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

### 3. Installer les dépendances Python

```bash
pip install -r requirements.txt

### 4. Installer Sherlock et Socialscan

```bash
# Sherlock
git clone https://github.com/sherlock-project/sherlock.git
cd sherlock
pip install -r requirements.txt
cd ..

# Socialscan
pip install socialscan


Lancer l'application
 python app.py
Puis ouvre ton navigateur à l'adresse :
➡️ http://127.0.0.1:5000



