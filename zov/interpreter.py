import os
try:
    from .ast import ZovDocument, ZovCategory, ZovItem, ZovVariable, ZovExpression, ZovFunctionCall, ZovInterpolatedString
    from .lexer import lex
    from .parser import Parser
except ImportError:
    import ast as ast_module
    import lexer as lexer_module
    import parser as parser_module
    ZovDocument = ast_module.ZovDocument
    ZovCategory = ast_module.ZovCategory
    ZovItem = ast_module.ZovItem
    ZovVariable = ast_module.ZovVariable
    ZovExpression = ast_module.ZovExpression
    ZovFunctionCall = ast_module.ZovFunctionCall
    ZovInterpolatedString = ast_module.ZovInterpolatedString
    lex = lexer_module.lex
    Parser = parser_module.Parser


class ZovInterpreter:
    def __init__(self, use_decimal=False):
        self.data = {}
        self.variables = {}
        self.use_decimal = use_decimal
        
        if use_decimal:
            from decimal import Decimal
            self.Decimal = Decimal
    
    def eval(self, node, parent_path=None):
        if isinstance(node, ZovDocument):
            for item in node.categories:
                if isinstance(item, ZovVariable):
                    self.eval_variable(item)
                else:
                    self.eval(item)
        elif isinstance(node, ZovCategory):
            path = f"{parent_path}.{node.name}" if parent_path else node.name
            if path not in self.data:
                self.data[path] = {'__items__': {}, '__categories__': set()}
            
            for item in node.items:
                if isinstance(item, ZovVariable):
                    self.eval_variable(item)
                elif isinstance(item, ZovCategory):
                    self.data[path]['__categories__'].add(item.name)
                    self.eval(item, path)
                elif isinstance(item, ZovItem):
                    if item.name in self.data[path]['__items__']:
                        line_info = f" at line {item.line}, column {item.column}" if item.line else ""
                        raise ValueError(f"Duplicate item '{item.name}' in category '{path}'{line_info}")
                    if item.name in self.data[path]['__categories__']:
                        line_info = f" at line {item.line}, column {item.column}" if item.line else ""
                        raise ValueError(f"Name collision: '{item.name}' is both a category and an item in '{path}'{line_info}")
                    
                    evaluated_values = [self.eval_value(v) for v in item.values]
                    self.data[path]['__items__'][item.name] = evaluated_values
    
    def get_category(self, category_name):
        if category_name in self.data:
            return self.data[category_name]['__items__']
        return {}
    
    def get_item(self, category_name, item_name):
        category = self.get_category(category_name)
        return category.get(item_name, [])
    
    def eval_variable(self, var_node):
        value = self.eval_value(var_node.value)
        self.variables[var_node.name] = value
    
    def eval_value(self, value):
        if isinstance(value, ZovExpression):
            return self.eval_expression(value)
        
        if isinstance(value, ZovFunctionCall):
            return self.eval_function(value)
        
        if isinstance(value, ZovInterpolatedString):
            return self.eval_interpolated_string(value)
        
        if isinstance(value, dict):
            if value.get('__type__') == 'variable_ref':
                var_name = value['name']
                if var_name not in self.variables:
                    raise ValueError(f"Undefined variable: {var_name}")
                return self.variables[var_name]
            return value
        
        return value
    
    def eval_function(self, func_call):
        func_name = func_call.name
        args = [self.eval_value(arg) for arg in func_call.args]
        
        if func_name == 'env':
            if len(args) < 1 or len(args) > 2:
                raise ValueError(f"env() expects 1 or 2 arguments, got {len(args)} at line {func_call.line}, column {func_call.column}")
            
            env_var = str(args[0])
            default = args[1] if len(args) > 1 else None
            
            value = os.environ.get(env_var, default)
            if value is None:
                raise ValueError(f"Environment variable '{env_var}' not found and no default provided at line {func_call.line}, column {func_call.column}")
            
            return value
        
        elif func_name == 'concat':
            return ''.join(str(self._simplify_value(arg)) for arg in args)
        
        elif func_name == 'join':
            if len(args) < 2:
                raise ValueError(f"join() expects at least 2 arguments (separator, ...items), got {len(args)} at line {func_call.line}, column {func_call.column}")
            
            separator = str(args[0])
            items = [str(self._simplify_value(arg)) for arg in args[1:]]
            return separator.join(items)
        
        elif func_name == 'upper':
            if len(args) != 1:
                raise ValueError(f"upper() expects 1 argument, got {len(args)} at line {func_call.line}, column {func_call.column}")
            return str(args[0]).upper()
        
        elif func_name == 'lower':
            if len(args) != 1:
                raise ValueError(f"lower() expects 1 argument, got {len(args)} at line {func_call.line}, column {func_call.column}")
            return str(args[0]).lower()
        
        else:
            raise ValueError(f"Unknown function: {func_name} at line {func_call.line}, column {func_call.column}")
    
    def eval_interpolated_string(self, interp_str):
        result = []
        
        for part_type, part_value in interp_str.parts:
            if part_type == 'text':
                result.append(part_value)
            elif part_type == 'var':
                if part_value not in self.variables:
                    raise ValueError(f"Undefined variable: {part_value} in interpolated string at line {interp_str.line}, column {interp_str.column}")
                result.append(str(self._simplify_value(self.variables[part_value])))
            elif part_type == 'expr':
                tokens = list(lex(part_value))
                p = Parser(tokens)
                expr_ast = p.parse_expression()
                value = self.eval_value(expr_ast)
                
                if isinstance(value, dict) and value.get('__type__') == 'identifier':
                    var_name = '$' + value['value']
                    if var_name in self.variables:
                        result.append(str(self._simplify_value(self.variables[var_name])))
                    else:
                        result.append(value['value'])
                else:
                    result.append(str(self._simplify_value(value)))
        
        return ''.join(result)
    
    def eval_expression(self, expr):
        left = self.eval_value(expr.left)
        right = self.eval_value(expr.right)
        
        if expr.operator == 'PLUS':
            if isinstance(left, str) or isinstance(right, str):
                return str(self._simplify_value(left)) + str(self._simplify_value(right))
        
        if isinstance(left, dict) and '__type__' in left:
            if left['__type__'] == 'identifier':
                raise ValueError(f"Cannot perform arithmetic on identifier '{left['value']}' at line {expr.line}, column {expr.column}")
        if isinstance(right, dict) and '__type__' in right:
            if right['__type__'] == 'identifier':
                raise ValueError(f"Cannot perform arithmetic on identifier '{right['value']}' at line {expr.line}, column {expr.column}")
        
        if self.use_decimal:
            from decimal import Decimal
            if not isinstance(left, Decimal):
                left = Decimal(str(left))
            if not isinstance(right, Decimal):
                right = Decimal(str(right))
        
        if not isinstance(left, (int, float)) and not (self.use_decimal and isinstance(left, self.Decimal)):
            raise ValueError(f"Cannot perform arithmetic on non-numeric values at line {expr.line}, column {expr.column}")
        if not isinstance(right, (int, float)) and not (self.use_decimal and isinstance(right, self.Decimal)):
            raise ValueError(f"Cannot perform arithmetic on non-numeric values at line {expr.line}, column {expr.column}")
        
        if expr.operator == 'PLUS':
            return left + right
        elif expr.operator == 'MINUS':
            return left - right
        elif expr.operator == 'MULTIPLY':
            return left * right
        elif expr.operator == 'DIVIDE':
            if right == 0:
                raise ValueError(f"Division by zero at line {expr.line}, column {expr.column}")
            result = left / right
            if self.use_decimal:
                return result
            if isinstance(result, float) and result.is_integer():
                return int(result)
            return result
        elif expr.operator == 'MODULO':
            if right == 0:
                raise ValueError(f"Modulo by zero at line {expr.line}, column {expr.column}")
            return left % right
        
        raise ValueError(f"Unknown operator: {expr.operator}")
    
    def _simplify_value(self, value):
        if self.use_decimal:
            from decimal import Decimal
            if isinstance(value, Decimal):
                return float(value)
        
        if isinstance(value, dict) and '__type__' in value:
            if value['__type__'] == 'identifier':
                return value['value']
            elif value['__type__'] in ('date', 'datetime', 'time'):
                return value['value']
            elif value['__type__'] == 'duration':
                return f"{value['value']}{value['unit']}"
            elif value['__type__'] == 'size':
                return f"{value['value']}{value['unit']}"
        
        return value
    
    def _simplify_values(self, values):
        return [self._simplify_value(v) for v in values]
    
    def _deep_merge(self, target, source):
        for key, value in source.items():
            if key in target:
                if isinstance(target[key], dict) and isinstance(value, dict):
                    self._deep_merge(target[key], value)
                else:
                    target[key] = value
            else:
                target[key] = value
    
    def to_dict(self):
        result = {}
        
        for path, content in sorted(self.data.items()):
            parts = path.split('.')
            current = result
            
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    raise ValueError(f"Cannot create nested structure: '{part}' is already a value, not a category")
                current = current[part]
            
            final_key = parts[-1]
            if final_key not in current:
                current[final_key] = {}
            elif not isinstance(current[final_key], dict):
                raise ValueError(f"Cannot create category '{final_key}': name already used as an item")
            
            simplified_items = {
                key: self._simplify_values(val) 
                for key, val in content['__items__'].items()
            }
            
            self._deep_merge(current[final_key], simplified_items)
        
        return result