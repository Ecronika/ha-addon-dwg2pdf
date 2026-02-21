import re

def patch():
    with open('dwg2pdf/app/static/three-dxf.js', 'r', encoding='utf-8') as f:
        code = f.read()
    
    # 1. We replace `function drawEntity(entity, data, parent) {`
    # or `function drawEntity(entity, data) {` depending on what it is
    
    target_pattern = re.compile(r'function drawEntity\((.*?)\)\s*\{')
    
    hook_code = r'''
    if (arguments[0] && arguments[0].layer) {
        var __entLayer = arguments[0].layer;
        var __origAdd = arguments[2] ? arguments[2].add : scene.add;
        var __hookedAdd = function(obj) { if(obj) obj.userData = {layer: __entLayer}; return __origAdd.call(this, obj); };
        if(arguments[2]) arguments[2].add = __hookedAdd.bind(arguments[2]); else scene.add = __hookedAdd.bind(scene);
    }
'''
    
    def replacement(match):
        return match.group(0) + hook_code

    patched_code = target_pattern.sub(replacement, code)
    
    # Replace the `export default { Viewer }` or `module.exports = { Viewer }`
    # Or inject `window.ThreeDxf = { Viewer }` at the end
    if 'export ' in patched_code:
        pass # Handle export
        
    # We must expose it as window.ThreeDxf to be compatible with CDN
    
    if not 'window.ThreeDxf =' in patched_code:
        patched_code += '\nif (typeof window !== "undefined") { window.ThreeDxf = { Viewer: Viewer }; }\n'
        
    with open('dwg2pdf/app/static/three-dxf.js', 'w', encoding='utf-8') as f:
        f.write(patched_code)
        
    print("Patch successful!")

if __name__ == '__main__':
    patch()
