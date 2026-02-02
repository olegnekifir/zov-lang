import sys
import json
import argparse
from zov import load_zov, parse_file
from zov.ast import ZovDocument, ZovCategory, ZovItem


def print_ast(node, indent=0):
    prefix = '  ' * indent
    
    if isinstance(node, ZovDocument):
        print(f'{prefix}ZovDocument')
        for cat in node.categories:
            print_ast(cat, indent + 1)
    elif isinstance(node, ZovCategory):
        print(f'{prefix}Category: {node.name} {{')
        for item in node.items:
            print_ast(item, indent + 1)
        print(f'{prefix}}}')
    elif isinstance(node, ZovItem):
        formatted_values = []
        for v in node.values:
            if isinstance(v, dict) and '__type__' in v:
                if v['__type__'] == 'identifier':
                    formatted_values.append(v['value'])
            elif isinstance(v, str) and (' ' in v or any(c in v for c in ',.;{}="')):
                formatted_values.append(f'"{v}"')
            elif isinstance(v, bool):
                formatted_values.append('true' if v else 'false')
            elif v is None:
                formatted_values.append('null')
            else:
                formatted_values.append(str(v))
        values_str = ', '.join(formatted_values)
        print(f'{prefix}Item: {node.name} = {values_str};')


def format_error(error, filename):
    import re
    line_match = re.search(r'line (\d+)', str(error))
    col_match = re.search(r'column (\d+)', str(error))
    
    if line_match and col_match:
        line = int(line_match.group(1))
        col = int(col_match.group(1))
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if 0 < line <= len(lines):
                error_line = lines[line - 1].rstrip()
                pointer = ' ' * col + '^'
                
                context = []
                if line > 1:
                    context.append(f"{line-1:4d} | {lines[line-2].rstrip()}")
                context.append(f"{line:4d} | {error_line}")
                context.append(f"     | {pointer}")
                if line < len(lines):
                    context.append(f"{line+1:4d} | {lines[line].rstrip()}")
                
                return '\n'.join(context)
        except:
            pass
    
    return None


def main():
    parser = argparse.ArgumentParser(description='ZOV Language CLI')
    parser.add_argument('file', help='ZOV file to process')
    parser.add_argument('--ast', action='store_true', help='Print AST tree')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--decimal', action='store_true', help='Use Decimal for precise calculations')
    
    args = parser.parse_args()
    
    try:
        if args.ast:
            ast = parse_file(args.file)
            print_ast(ast)
        else:
            data = load_zov(args.file, use_decimal=args.decimal)
            output = json.dumps(data, indent=2, ensure_ascii=False)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"✓ Saved to {args.output}")
            else:
                print(output)
    
    except FileNotFoundError as e:
        print(f"\n❌ File Error: {e}\n", file=sys.stderr)
        sys.exit(1)
    except SyntaxError as e:
        print(f"\n❌ Syntax Error in '{args.file}':", file=sys.stderr)
        print(f"   {e}\n", file=sys.stderr)
        context = format_error(e, args.file)
        if context:
            print(context, file=sys.stderr)
            print("", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Logic Error in '{args.file}':", file=sys.stderr)
        print(f"   {e}\n", file=sys.stderr)
        context = format_error(e, args.file)
        if context:
            print(context, file=sys.stderr)
            print("", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()