"""Offline documentation and AST inspection."""
import ast
import os
from pathlib import Path
import re

from .phrases import MORTGAGEEXTRACTION, NOMORTGAGEEXTRACTION, GENERIC_NAMES


def normalize(text):
    return ' '.join(text.lower().replace("n't", ' not').replace('-', ' ').split())


def matches(text, phrases):
    found = []
    for phrase in sorted(phrases, key=lambda p: (-len(p), p)):
        pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'
        if re.search(pattern, text):
            found.append(phrase)
            text = re.sub(pattern, ' ', text)
    return found, text


def claims(text):
    lines = []
    fence = None
    for line in text.splitlines():
        opening = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if re.match(r'^ {0,3}' + re.escape(fence[0]) + '{' + str(fence[1]) + r',}\s*$', line):
                fence = None
            lines.append('')
        elif opening and not (opening[1][0] == '`' and '`' in opening[2]):
            fence = (opening[1][0], len(opening[1]))
            lines.append('')
        else:
            lines.append(line)
    positive, negative = [], []
    for paragraph in re.split(r'\n\s*\n', '\n'.join(lines)):
        denied, remaining = matches(normalize(paragraph), NOMORTGAGEEXTRACTION)
        affirmed, _ = matches(remaining, MORTGAGEEXTRACTION)
        positive.extend(affirmed)
        negative.extend(denied)
    return positive, negative


def module_evidence(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    imports = {}
    gate = False
    def azure_import(name):
        return any(name == module or name.startswith(module + '.') for module in
                   ('azure.ai.formrecognizer', 'azure.ai.documentintelligence'))
    shadow = set()
    nodes = list(ast.walk(tree))
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            shadow.add(node.name)
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            targets = [item.optional_vars for item in node.items if item.optional_vars]
        for target in targets:
            shadow.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
                gate |= azure_import(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                full = module + '.' + alias.name
                imports[alias.asname or alias.name] = full
                gate |= azure_import(full)
    def resolve(node):
        if isinstance(node, ast.Name):
            return '' if node.id in shadow else imports.get(node.id, '')
        if isinstance(node, ast.Attribute):
            base = resolve(node.value)
            return base + '.' + node.attr if base else ''
        return ''
    constructors = {'azure.ai.formrecognizer.DocumentAnalysisClient',
                    'azure.ai.documentintelligence.DocumentIntelligenceClient'}
    client, operation = False, False
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            name = func.attr
            if name in GENERIC_NAMES and name not in shadow:
                return True
            if name in ('begin_analyze_document', 'begin_analyze_document_from_url') and name not in shadow:
                values = list(node.args[:1]) + [k.value for k in node.keywords if k.arg == 'model_id']
                operation |= any(isinstance(v, ast.Constant) and v.value in ('prebuilt-mortgage.us.1003', 'prebuilt-mortgage.us.1004', 'prebuilt-mortgage.us.1005', 'prebuilt-mortgage.us.1008', 'prebuilt-mortgage.us.closingDisclosure') for v in values)
            if name in ('DocumentAnalysisClient', 'DocumentIntelligenceClient') and name not in shadow:
                client |= resolve(func).startswith('azure.')
        elif isinstance(func, ast.Name):
            resolved = resolve(func)
            if resolved and resolved.rsplit('.', 1)[-1] in GENERIC_NAMES and resolved.rsplit('.', 1)[-1] not in shadow:
                return True
            client |= resolved in constructors
    return bool(gate and client and operation)


def audit(root, ignore=()):
    root = Path(root)
    if not root.is_dir():
        raise OSError('Repository must be an existing directory')
    ignored = [Path(p).as_posix().strip('/') for p in ignore]
    def excluded(rel):
        return any(p == '.' or rel == p or rel.startswith(p + '/') for p in ignored)
    docs, production, tests = [], [], []
    for directory, dirs, files in os.walk(root, onerror=lambda error: (_ for _ in ()).throw(error)):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink() and not excluded((Path(directory) / d).relative_to(root).as_posix()))
        for filename in sorted(files):
            path = Path(directory) / filename
            relative = path.relative_to(root)
            rel = relative.as_posix()
            if path.is_symlink() or excluded(rel):
                continue
            if rel == 'README.md' or (path.suffix == '.md' and 'docs' in relative.parts[:-1]):
                docs.append((rel, claims(path.read_text(encoding='utf-8'))))
            if path.suffix != '.py' or set(relative.parts[:-1]) & {'fixtures', 'docs', 'examples'}:
                continue
            if module_evidence(path.read_text(encoding='utf-8')):
                is_test = 'tests' in relative.parts[:-1] or filename.startswith('test_') or filename.endswith('_test.py')
                (tests if is_test else production).append(rel)
    positive = [path for path, (p, n) in docs if p]
    negative = [path for path, (p, n) in docs if n]
    findings = []
    if positive and not production:
        severity = 'MEDIUM' if tests else 'HIGH'
        findings.append(dict(rule='documented-mortgage-extraction-claim-false', severity=severity,
                             message='Documented capability has only test evidence.' if tests else 'Documented capability has no production evidence.', locations=positive))
    if negative and production:
        findings.append(dict(rule='documented-no-mortgage-extraction-claim-false', severity='HIGH',
                             message='Documented denial contradicts production evidence.', locations=negative))
    return dict(verdict='FAIL' if findings else 'PASS', findings=findings,
                evidence=dict(production=production, tests=tests))
