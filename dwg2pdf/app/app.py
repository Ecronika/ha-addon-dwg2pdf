import os
import uuid
import uuid
import shutil
import time
import threading
import io
from flask import Flask, render_template, request, send_file, jsonify, send_from_directory
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy

app = Flask(__name__)

# Temporäre Ordner für die Verarbeitung
UPLOAD_FOLDER = '/tmp/uploads'
CONVERT_FOLDER = '/tmp/converted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERT_FOLDER, exist_ok=True)

# Background cleanup thread
def cleanup_old_files():
    while True:
        time.sleep(3600) # Check every hour
        now = time.time()
        for folder in [UPLOAD_FOLDER, CONVERT_FOLDER]:
            try:
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    if os.path.isfile(file_path):
                        if now - os.path.getmtime(file_path) > 3600: # Older than 1 hour
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                print(f"Error deleting file {file_path}: {e}")
            except Exception as e:
                print(f"Error accessing directory {folder}: {e}")

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei gesendet'}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.dxf'):
        return jsonify({'error': 'Bitte eine gültige DXF-Datei hochladen'}), 400

    # 1. Unique ID für diesen Vorgang
    req_id = str(uuid.uuid4())
    
    # Da wir nun direkt DXF hochladen, überspringen wir den ODA-Konverter.
    # Wir speichern die DXF direkt im CONVERT_FOLDER unter der eindeutigen ID.
    unique_dxf_filename = f"{req_id}.dxf"
    final_dxf_path = os.path.join(CONVERT_FOLDER, unique_dxf_filename)
    
    try:
        file.save(final_dxf_path)
    except Exception as e:
        return jsonify({'error': f'Fehler beim Speichern der Datei: {e}'}), 500

    # 2. Dem Frontend mitteilen, dass die DXF bereit ist
    return jsonify({'success': True, 'dxf_file': unique_dxf_filename, 'original_name': file.filename})

@app.route('/dxf/<filename>')
def serve_dxf(filename):
    # Sendet die DXF-Datei an den Browser-Viewer
    return send_from_directory(CONVERT_FOLDER, filename)
    
@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    data = request.json
    dxf_filename = data.get('dxf_file')
    original_name = data.get('original_name', 'export')
    active_layers = data.get('layers', []) # Array der gewählten Layer
    
    if not dxf_filename:
        return jsonify({'error': 'Keine DXF-Datei angegeben'}), 400
        
    dxf_path = os.path.join(CONVERT_FOLDER, dxf_filename)
    if not os.path.exists(dxf_path):
        return jsonify({'error': 'DXF-Datei nicht gefunden oder abgelaufen'}), 404

    try:
        # 4. DXF mit ezdxf öffnen und PDF rendern
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        
        # Logik um nicht-gewählte Layer auszublenden/zu löschen
        # Wir durchlaufen alle Elemente im Modelspace. 
        # Falls ihr Layer nicht in active_layers ist, entfernen wir das Element.
        entities_to_delete = []
        for entity in msp:
            if entity.dxf.layer not in active_layers:
                entities_to_delete.append(entity)
                
        for entity in entities_to_delete:
            msp.delete_entity(entity)

        for layer in doc.layers:
            if layer.dxf.name not in active_layers:
                layer.off()

        # Matplotlib für PDF-Export konfigurieren
        fig = plt.figure(figsize=(11.69, 8.27), dpi=300) # A4 Querformat
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor('white')
        
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        
        # Konfiguration für weißen Hintergrund, aber Beibehaltung der Originalfarben
        config = Configuration(
            background_policy=BackgroundPolicy.WHITE,
            color_policy=ColorPolicy.COLOR
        )
        
        Frontend(ctx, out, config=config).draw_layout(msp, finalize=True)
        
        # PDF in Speicher (BytesIO) schreiben statt auf die Festplatte
        pdf_bytes = io.BytesIO()
        fig.savefig(pdf_bytes, format='pdf')
        plt.close(fig)
        
        pdf_bytes.seek(0)
        
        pdf_download_name = original_name.rsplit('.', 1)[0] + '.pdf'

        # 5. PDF zum Download anbieten
        return send_file(pdf_bytes, as_attachment=True, download_name=pdf_download_name, mimetype='application/pdf')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
