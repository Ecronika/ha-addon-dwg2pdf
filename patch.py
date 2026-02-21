import re
import sys

def patch():
    file_path = 'dwg2pdf/app/static/three-dxf.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # The user posted this patch for the minified code:
    # `let o=new j;if(o.text=t.replaceAll("\\P","\n").replaceAll("\\X","\n"),o.font=s,o.fontSize=r.textHeight,o.maxWidth=n.width,...`
    # However we downloaded the unminified 1.3.1 earlier. 
    # Let's search for how MText is drawn. We can search for `width` near `Text` or `MText`.
    
    # In unminified Troika implementation, it usually looks like:
    # textMesh.maxWidth = entity.width; 
    
    # Let's see if we can just string-replace universally inside drawMtext:
    
    pattern1 = r'(\w+)\.maxWidth\s*=\s*(\w+)\.width(?!.*Infinity)'
    
    def repl1(match):
        return f"{match.group(1)}.maxWidth = {match.group(2)}.width || Infinity"
        
    patched, count = re.subn(pattern1, repl1, code)
    print(f"Patched {count} locations of .maxWidth = .width")
    
    pattern2 = r'o\.maxWidth=n\.width([,;])'
    def repl2(match):
         return f"o.maxWidth=n.width||Infinity{match.group(1)}"
         
    patched, count2 = re.subn(pattern2, repl2, patched)
    print(f"Patched {count2} locations of o.maxWidth=n.width")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(patched)

if __name__ == '__main__':
    patch()
