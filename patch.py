import sys

def patch():
    file_path = 'dwg2pdf/app/static/three-dxf.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # The user suggested:
    # `this.render=function(){U.render(f,k)}` -> `this.scene=f,this.render=function(){U.render(f,k)}`
    # Let's check what exactly is in the minified code.
    
    target1 = 'this.render=function(){U.render(f,k)}'
    replacement1 = 'this.scene=f,this.render=function(){U.render(f,k)}'
    
    # Just in case variable names are different:
    # let's write a regex fallback if target1 is not found.
    import re
    if target1 in code:
        code = code.replace(target1, replacement1)
        print("Patched exactly with target1!")
    else:
        # search for `this.render=function(){`
        match = re.search(r'this\.render=function\(\)\{(\w+)\.render\((\w+),(\w+)\)\}', code)
        if match:
            u_var = match.group(1)
            f_var = match.group(2)
            k_var = match.group(3)
            print(f"Found dynamic variables: Renderer={u_var}, Scene={f_var}, Camera={k_var}")
            target2 = f'this.render=function(){{{u_var}.render({f_var},{k_var})}}'
            replacement2 = f'this.scene={f_var},this.render=function(){{{u_var}.render({f_var},{k_var})}}'
            code = code.replace(target2, replacement2)
            print("Patched dynamically!")
        else:
            print("Could not find render assignment.")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)

if __name__ == '__main__':
    patch()
