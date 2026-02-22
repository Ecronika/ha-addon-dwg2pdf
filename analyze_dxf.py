import re
import sys

def analyze():
    with open('dwg2pdf/app/static/three-dxf.js', 'r', encoding='utf-8') as f:
        code = f.read()

    # Find where `drawEntity` is called and meshes are added to the scene.
    # In unminified 1.3.1, it's roughly:
    # obj = drawEntity(entity, data);
    # if (obj) { 
    #     ... bbox stuff ...
    #     scene.add(obj);
    # }
    
    match = re.search(r'(\w+)\s*=\s*\w+\(([^,]+),\s*[^)]+\);?\s*if\(\s*\1\s*\)\{', code)
    if match:
        print("Caller matching obj = drawEntity():", code[match.start():match.end()+150])

if __name__ == '__main__':
    analyze()
