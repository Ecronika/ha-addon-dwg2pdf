"""
DWG to PDF Home Assistant Add-on Backend.

A Flask application that handles DXF uploads and generates PDFs using ezdxf.
"""

import os
import io
import uuid
import subprocess
import logging

from matplotlib.backends.backend_pdf import FigureCanvasPdf
from matplotlib.figure import Figure
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing import RenderContext, Frontend
import ezdxf
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from werkzeug.utils import secure_filename

# Logger konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# pylint: disable=import-error

app = Flask(__name__)

CONVERT_FOLDER = '/tmp/converted'
UPLOAD_FOLDER = '/tmp/uploads'
os.makedirs(CONVERT_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/')
def index():
    """Render the main frontend interface."""
    return render_template('index.html')


def _handle_dwg_conversion(temp_dwg_path: str, final_dxf_path: str):
    """Convert DWG to DXF via subprocess."""
    logger.info("Starte Konvertierung mit dwg2dxf: %s", temp_dwg_path)
    command = [
        "dwg2dxf",
        "--as",
        "r2010",
        "-y",
        "-o",
        final_dxf_path,
        temp_dwg_path]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=120)
    except subprocess.TimeoutExpired:
        logger.error(
            "dwg2dxf Timeout (120s) überschritten für Datei: %s",
            temp_dwg_path)
        return False

    if result.returncode != 0:
        if not os.path.exists(final_dxf_path) or os.path.getsize(
                final_dxf_path) == 0:
            logger.error(
                "dwg2dxf fehlgeschlagen! Code: %d\nSTDERR: %s",
                result.returncode,
                result.stderr)
            return False

        logger.warning(
            "dwg2dxf warnte (Code %d), aber DXF existiert.\nSTDERR: %s",
            result.returncode,
            result.stderr)

    logger.info("DWG erfolgreich nach %s konvertiert.", final_dxf_path)

    # Workaround für dwg2dxf (LibreDWG) Bug:
    # LibreDWG exportiert Layer häufig fälschlicherweise als "gefroren" oder "aus".
    # Das führt im Frontend dazu, dass alle Layer deaktiviert sind und der automatische Kamera-Zoom fehlschlägt,
    # da dieser nur sichtbare Elemente für die Bounding Box berücksichtigt.
    try:
        doc = ezdxf.readfile(final_dxf_path)
        modified = False
        for layer in doc.layers:
            if not layer.is_on() or layer.is_frozen():
                layer.on()
                layer.thaw()
                modified = True
        
        if modified:
            doc.saveas(final_dxf_path)
            logger.info("Layer-Sichtbarkeit und Freeze-Status in der konvertierten DXF-Datei korrigiert.")
    except Exception as e:
        logger.warning("Konnte Layer in %s nicht anpassen: %s", final_dxf_path, e)

    return True


def _handle_upload_saving(filename: str, req_id: str, file_obj) -> tuple:
    """Save an uploaded file based on its extension."""
    final_dxf_path = os.path.join(CONVERT_FOLDER, f"{req_id}.dxf")

    if filename.endswith('.dxf'):
        file_obj.save(final_dxf_path)
    elif filename.endswith('.dwg'):
        temp_dwg_path = os.path.join(UPLOAD_FOLDER, f"{req_id}.dwg")
        file_obj.save(temp_dwg_path)
        if not _handle_dwg_conversion(temp_dwg_path, final_dxf_path):
            return False, 'DWG Konvertierung fehlgeschlagen.'

    return True, None


@app.route('/upload', methods=['POST'])
def upload_file():
    """Process an endpoint to upload a DWG or DXF file."""
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei gesendet'}), 400

    file = request.files['file']
    filename = secure_filename(file.filename.lower())

    if not file or not filename or not (
            filename.endswith('.dwg') or filename.endswith('.dxf')):
        return jsonify(
            {'error': 'Bitte eine gültige DWG oder DXF Datei hochladen'}), 400

    req_id = str(uuid.uuid4())
    unique_dxf_filename = f"{req_id}.dxf"

    try:
        success, err_msg = _handle_upload_saving(filename, req_id, file)
        if not success:
            return jsonify({'error': err_msg}), 500

    except OSError as e:
        return jsonify({'error': f'Fehler beim Speichern der Datei: {e}'}), 500
    except Exception as e:  # pylint: disable=broad-exception-caught
        return jsonify(
            {'error': f'Unerwarteter Fehler bei der Verarbeitung: {e}'}), 500

    return jsonify({
        'success': True,
        'dxf_file': unique_dxf_filename,
        'original_name': file.filename
    })


@app.route('/dxf/<filename>')
def serve_dxf(filename):
    """Serve uploaded DXF files to the frontend viewer."""
    return send_from_directory(CONVERT_FOLDER, filename)


def _render_pdf_to_bytes(
        doc,
        msp,
        unit_multiplier: float,
        scale_denominator: float) -> io.BytesIO:
    """Render a DXF document's modelspace to a PDF using Matplotlib with exact scale."""
    fig = Figure(figsize=(10, 10), dpi=300)

    # 1. Add an axis that exactly fills the figure (no white borders mapped by
    # plt.margins)
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

    # 2. Extract strictly constrained data dimensions after graphics engine
    # evaluated visible layers
    x_min, y_min, x_max, y_max = ax.dataLim.extents
    if x_min == float('inf') or x_min == x_max:
        x_min, x_max, y_min, y_max = 0.0, 10.0, 0.0, 10.0

    # 3. Compute requested physical page size exactly tracking drawn data extent aspect ratios
    # $INSUNITS multiplier: 1=Inches, 4=mm (Standard), 5=cm, 6=Meters
    w_mm = (x_max - x_min) * {1: 25.4,
                              2: 304.8,
                              4: 1.0,
                              5: 10.0,
                              6: 1000.0}.get(doc.header.get('$INSUNITS',
                                                            4),
                                             1.0) * unit_multiplier / scale_denominator
    h_mm = (y_max - y_min) * {1: 25.4,
                              2: 304.8,
                              4: 1.0,
                              5: 10.0,
                              6: 1000.0}.get(doc.header.get('$INSUNITS',
                                                            4),
                                             1.0) * unit_multiplier / scale_denominator

    # 4. Apply calculated figure constraints strictly bounding the graphic
    fig.set_size_inches(max(1.0, min(w_mm / 25.4, 200.0)),
                        max(1.0, min(h_mm / 25.4, 200.0)))

    # Force the axes strictly again to eliminate Matplotlib's layout padding
    # overrides
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    pdf_bytes = io.BytesIO()
    canvas = FigureCanvasPdf(fig)
    canvas.print_pdf(pdf_bytes)
    return pdf_bytes


def _parse_pdf_request(data: dict):
    """Extract and validate parameters for PDF generation."""
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
    """Generate a PDF from a specified DXF file after filtering layers."""
    data = request.get_json(silent=True) or {}
    layers, unit, scale, dxf_file, is_invalid = _parse_pdf_request(data)

    if is_invalid:
        return jsonify({'error': 'Ungültiger Dateiname'}), 400

    dxf_path = os.path.join(CONVERT_FOLDER, dxf_file)
    if not os.path.exists(dxf_path):
        return jsonify(
            {'error': 'DXF-Datei nicht gefunden oder abgelaufen'}), 404

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
        pdf_download_name = data.get(
            'original_name', 'export').rsplit(
            '.', 1)[0] + '.pdf'

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
    app.run(host='0.0.0.0', port=8062)
