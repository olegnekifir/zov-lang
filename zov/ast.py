class ZovCategory:
    def __init__(self, name, items, line=None, column=None):
        self.name = name
        self.items = items
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f'ZovCategory({self.name}, {self.items})'


class ZovItem:
    def __init__(self, name, values, line=None, column=None):
        self.name = name
        self.values = values
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f'ZovItem({self.name}, {self.values})'


class ZovDocument:
    def __init__(self, categories):
        self.categories = categories
    
    def __repr__(self):
        return f'ZovDocument({self.categories})'


class ZovInclude:
    def __init__(self, filename, line=None, column=None):
        self.filename = filename
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f'ZovInclude({self.filename})'


class ZovVariable:
    def __init__(self, name, value, line=None, column=None):
        self.name = name
        self.value = value
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f'ZovVariable({self.name}, {self.value})'


class ZovExpression:
    def __init__(self, operator, left, right, line=None, column=None):
        self.operator = operator
        self.left = left
        self.right = right
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f'ZovExpression({self.operator}, {self.left}, {self.right})'


class ZovFunctionCall:
    def __init__(self, name, args, line=None, column=None):
        self.name = name
        self.args = args
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f'ZovFunctionCall({self.name}, {self.args})'


class ZovInterpolatedString:
    def __init__(self, parts, line=None, column=None):
        self.parts = parts
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f'ZovInterpolatedString({self.parts})'