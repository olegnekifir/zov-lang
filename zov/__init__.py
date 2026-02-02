import os
from .lexer import lex
from .parser import Parser
from .interpreter import ZovInterpreter
from .ast import ZovDocument, ZovCategory, ZovItem, ZovVariable, ZovExpression, ZovFunctionCall, ZovInterpolatedString

__version__ = "1.0.0"
__all__ = ['lex', 'Parser', 'ZovInterpreter', 'ZovDocument', 'ZovCategory', 'ZovItem', 'ZovVariable', 'ZovExpression', 'ZovFunctionCall', 'ZovInterpolatedString']


def parse_file(filename):
    abs_path = os.path.abspath(filename)
    base_path = os.path.dirname(abs_path)
    
    with open(abs_path, 'r', encoding='utf-8') as f:
        code = f.read()
    tokens = lex(code)
    parser = Parser(tokens, base_path, {abs_path})
    return parser.parse()


def load_zov(filename, use_decimal=False):
    ast = parse_file(filename)
    interpreter = ZovInterpreter(use_decimal=use_decimal)
    interpreter.eval(ast)
    return interpreter.to_dict()
