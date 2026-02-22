import io
import sys
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
import ezdxf.bbox as bbox
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import FigureCanvasPdf

def test_render():
    # create a simple dxf
    doc = ezdxf.new()
    doc.header['$INSUNITS'] = 4 # mm
    msp = doc.modelspace()
    
    # draw a square 100x50 units
    msp.add_lwpolyline([(0,0), (100,0), (100,50), (0,50), (0,0)])
    
    # User parameters:
    # 1 DXF unit = 10 mm (1 cm)
    unit_multiplier = 10
    # Scale 1:1
    scale_denominator = 1
    
    # Using ezdxf.bbox
    extents = bbox.extents(msp, fast=True)
    if not extents.has_data:
        print("No data")
        return
        
    x_min, y_min = extents.extmin.x, extents.extmin.y
    x_max, y_max = extents.extmax.x, extents.extmax.y
    
    width_units = x_max - x_min
    height_units = y_max - y_min
    
    print(f"DXF Size: {width_units}x{height_units} units")
    
    insunits = doc.header.get('$INSUNITS', 4)
    unit_to_mm = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}.get(insunits, 1.0)
    
    final_width_mm = (width_units * unit_to_mm * unit_multiplier) / scale_denominator
    final_height_mm = (height_units * unit_to_mm * unit_multiplier) / scale_denominator
    print(f"Paper Size: {final_width_mm}x{final_height_mm} mm")
    
    w_in = final_width_mm / 25.4
    h_in = final_height_mm / 25.4
    
    fig = Figure(figsize=(w_in, h_in), dpi=300)
    
    # Important: Set limits BEFORE drawing to prevent Matplotlib aspect/autoscale from adding padding
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor('white')
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    config = Configuration(
        background_policy=BackgroundPolicy.WHITE,
        color_policy=ColorPolicy.COLOR
    )
    
    # Frontend scales the layout automatically to the ax. But we want to preserve our tight limits
    df = Frontend(ctx, out, config=config)
    df.draw_layout(msp, finalize=True)
    
    # Ezdxf frontend might override limits in draw_layout! 
    # Force them strictly again to crop any whitespace padding the frontend might have appended
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    
    canvas = FigureCanvasPdf(fig)
    with open('test_scale2.pdf', 'wb') as f:
        canvas.print_pdf(f)
    print("Exported to test_scale2.pdf")
    print(f"Final Matplotlib limits: {ax.get_xlim()}, {ax.get_ylim()}")

if __name__ == '__main__':
    test_render()
