import re
from collections import namedtuple
from decimal import Decimal

Token = namedtuple('Token', ['type', 'value', 'line', 'column'])

TOKEN_SPECIFICATION = [
    ('COMMENT', r'#[^\n]*'),
    ('NULL', r'\b(null|none)\b'),
    ('BOOL', r'\b(true|false)\b'),
    ('DURATION', r'\d+(\.\d+)?(ms|s|m|h|d|w)'),
    ('SIZE', r'\d+(\.\d+)?(B|KB|MB|GB|TB|KiB|MiB|GiB|TiB)'),
    ('DATETIME', r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
    ('DATE', r'\d{4}-\d{2}-\d{2}'),
    ('TIME', r'\d{2}:\d{2}(:\d{2})?'),
    ('NUMBER', r'-?\d+(\.\d+)?'),
    ('STRING', r'"(?:[^"\\$]|\\.)*"'),
    ('INTERPOLATED_STRING_MARKER', r'"(?:[^"\\]|\\.)*(?:\$(?:[a-zA-Z_\u0400-\u04FF][a-zA-Z_0-9\u0400-\u04FF]*|\{[^}]+\}))+(?:[^"\\]|\\.)*"'),
    ('INCLUDE', r'\binclude\b'),
    ('LBRACE', r'\{'),
    ('RBRACE', r'\}'),
    ('LPAREN', r'\('),
    ('RPAREN', r'\)'),
    ('SEMICOLON', r';'),
    ('COMMA', r','),
    ('EQUALS', r'='),
    ('PLUS', r'\+'),
    ('MINUS', r'-'),
    ('MULTIPLY', r'\*'),
    ('DIVIDE', r'/'),
    ('MODULO', r'%'),
    ('VARIABLE', r'\$[a-zA-Z_\u0400-\u04FF][a-zA-Z_0-9\u0400-\u04FF]*'),
    ('FUNCTION', r'[a-zA-Z_\u0400-\u04FF][a-zA-Z_0-9\u0400-\u04FF]*(?=\()'),
    ('ID', r'[a-zA-Z_\u0400-\u04FF][a-zA-Z_0-9\u0400-\u04FF]*'),
    ('SKIP', r'[ \t]+'),
    ('NEWLINE', r'\n'),
    ('MISMATCH', r'.'),
]

def lex(code):
    tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPECIFICATION)
    line_num = 1
    line_start = 0
    
    for match in re.finditer(tok_regex, code):
        kind = match.lastgroup
        value = match.group()
        column = match.start() - line_start
        
        if kind == 'NEWLINE':
            line_start = match.end()
            line_num += 1
            continue
        elif kind in ('SKIP', 'COMMENT'):
            continue
        elif kind == 'MISMATCH':
            raise SyntaxError(f'Unexpected character: {value!r} at line {line_num}, column {column}')
        elif kind == 'INTERPOLATED_STRING_MARKER':
            parts = []
            current = ''
            i = 1
            while i < len(value) - 1:
                if value[i] == '\\' and i + 1 < len(value) - 1:
                    escape_map = {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}
                    current += escape_map.get(value[i + 1], value[i + 1])
                    i += 2
                elif value[i] == '$':
                    if current:
                        parts.append(('text', current))
                        current = ''
                    if i + 1 < len(value) - 1 and value[i + 1] == '{':
                        end = value.find('}', i + 2)
                        if end != -1:
                            var_expr = value[i + 2:end]
                            parts.append(('expr', var_expr))
                            i = end + 1
                        else:
                            raise SyntaxError(f'Unclosed interpolation at line {line_num}, column {column + i}')
                    else:
                        match_var = re.match(r'\$([a-zA-Z_\u0400-\u04FF][a-zA-Z_0-9\u0400-\u04FF]*)', value[i:])
                        if match_var:
                            parts.append(('var', '$' + match_var.group(1)))
                            i += len(match_var.group(0))
                        else:
                            current += '$'
                            i += 1
                else:
                    current += value[i]
                    i += 1
            if current:
                parts.append(('text', current))
            
            yield Token('INTERPOLATED_STRING', parts, line_num, column)
        elif kind == 'STRING':
            decoded = value[1:-1].replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
            yield Token(kind, decoded, line_num, column)
        elif kind == 'DURATION':
            match_duration = re.match(r'(\d+(?:\.\d+)?)(ms|s|m|h|d|w)', value)
            num = float(match_duration.group(1)) if '.' in match_duration.group(1) else int(match_duration.group(1))
            unit = match_duration.group(2)
            yield Token(kind, {'__type__': 'duration', 'value': num, 'unit': unit}, line_num, column)
        elif kind == 'SIZE':
            match_size = re.match(r'(\d+(?:\.\d+)?)(B|KB|MB|GB|TB|KiB|MiB|GiB|TiB)', value)
            num = float(match_size.group(1)) if '.' in match_size.group(1) else int(match_size.group(1))
            unit = match_size.group(2)
            yield Token(kind, {'__type__': 'size', 'value': num, 'unit': unit}, line_num, column)
        elif kind == 'DATETIME':
            yield Token(kind, {'__type__': 'datetime', 'value': value}, line_num, column)
        elif kind == 'TIME':
            yield Token(kind, {'__type__': 'time', 'value': value}, line_num, column)
        elif kind == 'NUMBER':
            try:
                if '.' in value:
                    num_value = float(value)
                else:
                    num_value = int(value)
                yield Token(kind, num_value, line_num, column)
            except (ValueError, OverflowError) as e:
                raise SyntaxError(f'Invalid number format: {value!r} at line {line_num}, column {column}: {e}')
        elif kind == 'BOOL':
            yield Token(kind, value == 'true', line_num, column)
        elif kind == 'NULL':
            yield Token(kind, None, line_num, column)
        elif kind == 'DATE':
            yield Token(kind, {'__type__': 'date', 'value': value}, line_num, column)
        elif kind == 'VARIABLE':
            yield Token(kind, value, line_num, column)
        elif kind == 'FUNCTION':
            yield Token(kind, value, line_num, column)
        else:
            yield Token(kind, value, line_num, column)