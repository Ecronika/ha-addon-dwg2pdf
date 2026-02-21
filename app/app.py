import os
import subprocess
from flask import Flask, render_template, request, send_file, jsonify
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

app = Flask(__name__)

# Temporäre Ordner für die Verarbeitung
UPLOAD_FOLDER = '/tmp/uploads'
CONVERT_FOLDER = '/tmp/converted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    # Lädt die Startseite mit dem Upload-Formular
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei gesendet'}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.dwg'):
        return jsonify({'error': 'Bitte eine gültige DWG-Datei hochladen'}), 400

    # 1. DWG speichern
    dwg_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(dwg_path)

    # 2. ODA Converter aufrufen (DWG zu DXF)
    # Syntax: ODAFileConverter <InputFolder> <OutputFolder> <Version> <Format> <Recurse> <Audit>
    try:
        subprocess.run([
            'ODAFileConverter', 
            UPLOAD_FOLDER, 
            CONVERT_FOLDER, 
            'ACAD2018', # Ziel-Version
            'DXF',      # Ziel-Format
            '0',        # Keine Unterordner
            '1'         # Audit (Fehlerkorrektur)
        ], check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Konvertierung fehlgeschlagen: {e}'}), 500

    # DXF Dateiname generieren
    dxf_filename = file.filename.rsplit('.', 1)[0] + '.dxf'
    
    # 3. Dem Frontend mitteilen, dass die DXF bereit ist
    return jsonify({'success': True, 'dxf_file': dxf_filename})

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    data = request.json
    dxf_filename = data.get('dxf_file')
    active_layers = data.get('layers', []) # Array der gewählten Layer
    
    dxf_path = os.path.join(CONVERT_FOLDER, dxf_filename)
    pdf_path = os.path.join(CONVERT_FOLDER, dxf_filename.replace('.dxf', '.pdf'))

    # 4. DXF mit ezdxf öffnen und PDF rendern
    try:
        doc = ezdxf.readfile(dxf_path)
        
        # HIER: Logik um nicht-gewählte Layer auszublenden/zu löschen
        for layer in doc.layers:
            if layer.dxf.name not in active_layers:
                layer.off() # Layer ausschalten

        # Matplotlib für PDF-Export konfigurieren
        fig = plt.figure()
        ax = fig.add_axes([0, 0, 1, 1])
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(doc.modelspace(), finalize=True)
        
        fig.savefig(pdf_path, format='pdf')
        plt.close(fig)

        # 5. PDF zum Download anbieten
        return send_file(pdf_path, as_attachment=True)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
