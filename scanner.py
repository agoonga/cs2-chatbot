import ast
import os
import re

def is_likely_user_facing(node, source_code):
    if not isinstance(node, (ast.Str, ast.JoinedStr)):
        return False
    
    # Exclude docstrings
    parent = None
    for p in ast.walk(ast.parse(source_code)):
        for child in ast.iter_child_nodes(p):
            if child == node:
                parent = p
                break
        if parent: break
        
    if isinstance(parent, (ast.FunctionDef, ast.ClassDef, ast.Module)):
        if ast.get_docstring(parent) and node.s in ast.get_docstring(parent):
            return False

    # Heuristics for exclusion
    val = ""
    if isinstance(node, ast.Str):
        val = node.s
    elif isinstance(node, ast.JoinedStr):
        val = "f-string"

    if isinstance(val, str):
        # Exclude common non-user patterns
        if re.search(r'SELECT|INSERT|UPDATE|DELETE|FROM|WHERE', val, re.I): return False
        if re.search(r'\.(log|jpg|png|json|py|txt|csv)$', val, re.I): return False
        if re.search(r'^[a-z0-9_]+$', val) and len(val) > 1: return False # Likely keys/internal names
        if val.startswith(('http', 'C:\\', '/')): return False

    return True

def scan_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    matches = []
    
    for node in ast.walk(tree):
        # Case 1: return statement
        if isinstance(node, ast.Return) and node.value:
            for subnode in ast.walk(node.value):
                if isinstance(subnode, (ast.Str, ast.JoinedStr)) and is_likely_user_facing(subnode, content):
                    matches.append((subnode.lineno, content.splitlines()[subnode.lineno-1].strip()))
        
        # Case 2: bot.add_to_chat_queue(...)
        if isinstance(node, ast.Call):
            func = node.func
            is_chat_queue = False
            if isinstance(func, ast.Attribute) and func.attr == 'add_to_chat_queue':
                is_chat_queue = True
            
            if is_chat_queue:
                for arg in node.args:
                    for subnode in ast.walk(arg):
                        if isinstance(subnode, (ast.Str, ast.JoinedStr)) and is_likely_user_facing(subnode, content):
                            matches.append((subnode.lineno, content.splitlines()[subnode.lineno-1].strip()))

    return matches

total_count = 0
results = {}

for folder in ['cmds', 'modules']:
    if not os.path.exists(folder): continue
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                file_matches = scan_file(path)
                if file_matches:
                    results[path] = file_matches
                    total_count += len(file_matches)

for path, matches in results.items():
    print(f"\n[{path}]")
    for line, snippet in matches:
        print(f"  Line {line}: {snippet}")

print(f"\nTotal likely user-facing strings: {total_count}")
