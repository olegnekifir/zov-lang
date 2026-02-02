import os
try:
    from .ast import ZovCategory, ZovItem, ZovDocument, ZovInclude, ZovVariable, ZovExpression, ZovFunctionCall, ZovInterpolatedString
    from .lexer import lex
except ImportError:
    import ast as ast_module
    import lexer as lexer_module
    ZovCategory = ast_module.ZovCategory
    ZovItem = ast_module.ZovItem
    ZovDocument = ast_module.ZovDocument
    ZovInclude = ast_module.ZovInclude
    ZovVariable = ast_module.ZovVariable
    ZovExpression = ast_module.ZovExpression
    ZovFunctionCall = ast_module.ZovFunctionCall
    ZovInterpolatedString = ast_module.ZovInterpolatedString
    lex = lexer_module.lex


class Parser:
    def __init__(self, tokens, base_path=None, seen_files=None):
        self.tokens = list(tokens)
        self.pos = 0
        self.base_path = base_path or os.getcwd()
        self.seen_files = seen_files if seen_files is not None else set()
    
    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None
    
    def peek_next(self):
        return self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
    
    def advance(self):
        self.pos += 1
    
    def expect(self, token_type):
        tok = self.peek()
        if tok and tok.type == token_type:
            self.advance()
            return tok
        if tok:
            raise SyntaxError(f'Expected {token_type}, got {tok.type} at line {tok.line}, column {tok.column}')
        else:
            raise SyntaxError(f'Expected {token_type}, got end of file')
    
    def _safe_include_path(self, filename, line, column):
        included_path = os.path.join(self.base_path, filename)
        included_abs = os.path.abspath(included_path)
        
        base_abs = os.path.abspath(self.base_path)
        
        if included_abs == base_abs:
            return included_abs
        
        if not included_abs.startswith(base_abs + os.sep):
            raise SecurityError(
                f'Path traversal detected: include path "{filename}" resolves outside base directory '
                f'at line {line}, column {column}'
            )
        
        return included_abs
    
    def parse(self):
        categories = []
        while self.peek():
            tok = self.peek()
            if tok.type == 'VARIABLE':
                categories.append(self.parse_variable())
            elif tok.type == 'INCLUDE':
                self.advance()
                filename_tok = self.expect('STRING')
                self.expect('SEMICOLON')
                
                try:
                    included_abs = self._safe_include_path(
                        filename_tok.value, 
                        filename_tok.line, 
                        filename_tok.column
                    )
                except SecurityError as e:
                    raise SyntaxError(str(e))
                
                if not os.path.exists(included_abs):
                    raise FileNotFoundError(
                        f'Include file not found: {filename_tok.value} '
                        f'at line {filename_tok.line}, column {filename_tok.column}'
                    )
                
                if included_abs in self.seen_files:
                    raise SyntaxError(
                        f'Circular include detected: {filename_tok.value} '
                        f'at line {filename_tok.line}, column {filename_tok.column}'
                    )
                
                with open(included_abs, 'r', encoding='utf-8') as f:
                    included_code = f.read()
                
                new_seen = self.seen_files | {included_abs}
                included_tokens = lex(included_code)
                included_parser = Parser(included_tokens, os.path.dirname(included_abs), new_seen)
                included_ast = included_parser.parse()
                
                categories.extend(included_ast.categories)
            else:
                categories.append(self.parse_category())
        return ZovDocument(categories)
    
    def parse_category(self):
        name_tok = self.expect('ID')
        name = name_tok.value
        self.expect('LBRACE')
        
        items = []
        while self.peek() and self.peek().type != 'RBRACE':
            tok = self.peek()
            if tok.type == 'ID':
                next_tok = self.peek_next()
                if next_tok and next_tok.type == 'LBRACE':
                    items.append(self.parse_category())
                else:
                    items.append(self.parse_item())
            elif tok.type == 'INCLUDE':
                self.advance()
                filename_tok = self.expect('STRING')
                self.expect('SEMICOLON')
                
                try:
                    included_abs = self._safe_include_path(
                        filename_tok.value,
                        filename_tok.line,
                        filename_tok.column
                    )
                except SecurityError as e:
                    raise SyntaxError(str(e))
                
                if not os.path.exists(included_abs):
                    raise FileNotFoundError(
                        f'Include file not found: {filename_tok.value} '
                        f'at line {filename_tok.line}, column {filename_tok.column}'
                    )
                
                if included_abs in self.seen_files:
                    raise SyntaxError(
                        f'Circular include detected: {filename_tok.value} '
                        f'at line {filename_tok.line}, column {filename_tok.column}'
                    )
                
                with open(included_abs, 'r', encoding='utf-8') as f:
                    included_code = f.read()
                
                new_seen = self.seen_files | {included_abs}
                included_tokens = lex(included_code)
                included_parser = Parser(included_tokens, os.path.dirname(included_abs), new_seen)
                included_ast = included_parser.parse()
                
                for included_item in included_ast.categories:
                    if isinstance(included_item, ZovVariable):
                        items.append(included_item)
                    else:
                        items.append(included_item)
            elif tok.type == 'VARIABLE':
                items.append(self.parse_variable())
            else:
                raise SyntaxError(
                    f'Expected ID, VARIABLE or INCLUDE, got {tok.type} '
                    f'at line {tok.line}, column {tok.column}'
                )
        
        self.expect('RBRACE')
        return ZovCategory(name, items, name_tok.line, name_tok.column)
    
    def parse_item(self):
        name_tok = self.expect('ID')
        name = name_tok.value
        self.expect('EQUALS')
        
        values = []
        values.append(self.parse_expression())
        
        while self.peek() and self.peek().type == 'COMMA':
            self.advance()
            tok = self.peek()
            
            if tok and tok.type == 'SEMICOLON':
                break
            
            values.append(self.parse_expression())
        
        self.expect('SEMICOLON')
        return ZovItem(name, values, name_tok.line, name_tok.column)
    
    def parse_variable(self):
        var_tok = self.expect('VARIABLE')
        self.expect('EQUALS')
        value = self.parse_expression()
        self.expect('SEMICOLON')
        return ZovVariable(var_tok.value, value, var_tok.line, var_tok.column)
    
    def parse_expression(self):
        return self.parse_additive()
    
    def parse_additive(self):
        left = self.parse_multiplicative()
        
        while self.peek() and self.peek().type in ('PLUS', 'MINUS'):
            op_tok = self.peek()
            self.advance()
            right = self.parse_multiplicative()
            left = ZovExpression(op_tok.type, left, right, op_tok.line, op_tok.column)
        
        return left
    
    def parse_multiplicative(self):
        left = self.parse_primary()
        
        while self.peek() and self.peek().type in ('MULTIPLY', 'DIVIDE', 'MODULO'):
            op_tok = self.peek()
            self.advance()
            right = self.parse_primary()
            left = ZovExpression(op_tok.type, left, right, op_tok.line, op_tok.column)
        
        return left
    
    def parse_primary(self):
        tok = self.peek()
        
        if not tok:
            raise SyntaxError('Expected value, got end of file')
        
        if tok.type == 'LPAREN':
            self.advance()
            expr = self.parse_expression()
            self.expect('RPAREN')
            return expr
        
        if tok.type == 'FUNCTION':
            func_name = tok.value
            func_line = tok.line
            func_col = tok.column
            self.advance()
            self.expect('LPAREN')
            
            args = []
            while self.peek() and self.peek().type != 'RPAREN':
                args.append(self.parse_expression())
                if self.peek() and self.peek().type == 'COMMA':
                    self.advance()
                elif self.peek() and self.peek().type != 'RPAREN':
                    raise SyntaxError(
                        f'Expected COMMA or RPAREN in function call at line {self.peek().line}, column {self.peek().column}'
                    )
            
            self.expect('RPAREN')
            return ZovFunctionCall(func_name, args, func_line, func_col)
        
        if tok.type == 'INTERPOLATED_STRING':
            self.advance()
            return ZovInterpolatedString(tok.value, tok.line, tok.column)
        
        if tok.type in ('NUMBER', 'STRING', 'BOOL', 'NULL', 'DATE', 'DATETIME', 'TIME', 'DURATION', 'SIZE'):
            self.advance()
            return tok.value
        
        if tok.type == 'VARIABLE':
            self.advance()
            return {'__type__': 'variable_ref', 'name': tok.value}
        
        if tok.type == 'ID':
            self.advance()
            return {'__type__': 'identifier', 'value': tok.value}
        
        raise SyntaxError(
            f'Expected value, got {tok.type} at line {tok.line}, column {tok.column}'
        )


class SecurityError(Exception):
    pass