"""
DWG to PDF Home Assistant Add-on Backend
A Flask application that handles DXF uploads and generates PDFs using ezdxf.
"""

import os
import time
import threading
import io
import uuid

# pylint: disable=import-error
from flask import Flask, render_template, request, send_file, jsonify, send_from_directory
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import FigureCanvasPdf

app = Flask(__name__)

CONVERT_FOLDER = '/tmp/converted'
os.makedirs(CONVERT_FOLDER, exist_ok=True)


def _delete_old_files(folder: str, max_age_seconds: int):
    """Deletes files in the given folder that are older than max_age_seconds."""
    try:
        now = time.time()
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                if now - os.path.getmtime(file_path) > max_age_seconds:
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        print(f"Error deleting file {file_path}: {e}")
    except OSError as e:
        print(f"Error accessing directory {folder}: {e}")


def cleanup_old_files():
    """Background thread that deletes old converted files."""
    while True:
        time.sleep(3600)
        _delete_old_files(CONVERT_FOLDER, 3600)


cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()


@app.route('/')
def index():
    """Renders the main frontend interface."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Endpoint to upload a DXF file."""
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei gesendet'}), 400

    file = request.files['file']
    if not file or file.filename == '' or not file.filename.lower().endswith('.dxf'):
        return jsonify({'error': 'Bitte eine gültige DXF-Datei hochladen'}), 400

    req_id = str(uuid.uuid4())
    unique_dxf_filename = f"{req_id}.dxf"
    final_dxf_path = os.path.join(CONVERT_FOLDER, unique_dxf_filename)

    try:
        file.save(final_dxf_path)
    except OSError as e:
        return jsonify({'error': f'Fehler beim Speichern der Datei: {e}'}), 500

    return jsonify({
        'success': True,
        'dxf_file': unique_dxf_filename,
        'original_name': file.filename
    })


@app.route('/dxf/<filename>')
def serve_dxf(filename):
    """Serves uploaded DXF files to the frontend viewer."""
    return send_from_directory(CONVERT_FOLDER, filename)


def _apply_dynamic_scale(fig, ax, doc, unit_multiplier, scale_denominator):
    """Calculates Matplotlib axes dimensions mapped to exact real-world scale."""
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    # $INSUNITS: 1=Inches, 4=mm (Standard), 5=cm, 6=Meters
    insunits = doc.header.get('$INSUNITS', 4)
    unit_to_mm = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}.get(insunits, 1.0)

    # Calculate the paper size in inches based on selected scale and units
    final_width_mm = ((abs(x_max - x_min) or 10.0) * unit_to_mm * unit_multiplier) \
        / scale_denominator
    final_height_mm = ((abs(y_max - y_min) or 10.0) * unit_to_mm * unit_multiplier) \
        / scale_denominator

    w_in = max(1.0, min(final_width_mm / 25.4, 200.0))
    h_in = max(1.0, min(final_height_mm / 25.4, 200.0))
    fig.set_size_inches(w_in, h_in)

def _render_pdf_to_bytes(doc, msp, unit_multiplier: float, scale_denominator: float) -> io.BytesIO:
    """Renders a DXF document's modelspace to a PDF using Matplotlib with exact scale."""
    fig = Figure(dpi=300)

    # Axe spans the entire figure without margins to perfectly preserve scale
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor('white')

    Frontend(
        RenderContext(doc),
        MatplotlibBackend(ax),
        config=Configuration(
            background_policy=BackgroundPolicy.WHITE,
            color_policy=ColorPolicy.COLOR
        )
    ).draw_layout(msp, finalize=True)
    _apply_dynamic_scale(fig, ax, doc, unit_multiplier, scale_denominator)

    pdf_bytes = io.BytesIO()
    canvas = FigureCanvasPdf(fig)
    canvas.print_pdf(pdf_bytes)
    return pdf_bytes


def _parse_pdf_request(data: dict):
    """Extracts and validates parameters for PDF generation."""
    active_layers = data.get('layers', [])
    try:
        unit = float(data.get('unit', 10))
    except (ValueError, TypeError):
        unit = 10.0

    try:
        scale = float(data.get('scale', 100))
    except (ValueError, TypeError):
        scale = 100.0

    dxf_file = data.get('dxf_file')
    is_inv = not dxf_file or '/' in dxf_file or '\\' in dxf_file
    is_inv = is_inv or not dxf_file.endswith('.dxf')
    return active_layers, unit, scale, dxf_file, is_inv

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    # pylint: disable=too-many-locals
    """Generates a PDF from a specified DXF file after filtering layers."""
    data = request.get_json(silent=True) or {}
    layers, unit, scale, dxf_file, is_invalid = _parse_pdf_request(data)

    if is_invalid:
        return jsonify({'error': 'Ungültiger Dateiname'}), 400

    dxf_path = os.path.join(CONVERT_FOLDER, dxf_file)
    if not os.path.exists(dxf_path):
        return jsonify({'error': 'DXF-Datei nicht gefunden oder abgelaufen'}), 404

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        for entity in list(msp):
            if entity.dxf.layer not in layers:
                msp.delete_entity(entity)

        for layer in doc.layers:
            if layer.dxf.name not in layers:
                layer.off()

        pdf_bytes = _render_pdf_to_bytes(doc, msp, unit, scale)
        pdf_bytes.seek(0)
        pdf_download_name = data.get('original_name', 'export').rsplit('.', 1)[0] + '.pdf'

        return send_file(
            pdf_bytes,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_download_name
        )

    except OSError as e:
        return jsonify({'error': f'Dateifehler: {e}'}), 500
    except Exception as e:  # pylint: disable=broad-exception-caught
        return jsonify({'error': f'Unerwarteter Fehler: {e}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
