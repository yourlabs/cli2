from markdown_it import MarkdownIt
import cli2
from cli2.table import Table
from cli2.theme import theme as t
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import Terminal256Formatter
from pygments.util import ClassNotFound

cli2.cfg.defaults['PYGMENTS_STYLE'] = 'monokai'

class TerminalRenderer:
    def __init__(self):
        self.render_methods = {
            'heading_open': self.render_heading,
            'paragraph_open': self.render_paragraph,
            'fence': self.render_code_block,
            'code_block': self.render_code_block,
            'table_open': self.render_table,
            'bullet_list_open': self.render_bullet_list,
            'list_item_open': self.render_list_item,
            'ordered_list_open': self.render_ordered_list,
        }

    def render(self, tokens):
        output = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.type in self.render_methods:
                rendered_lines, i = self.render_methods[token.type](tokens, i, level=0)
                output.extend(rendered_lines)
            else:
                i += 1
        return '\n'.join(output)

    def render_heading(self, tokens, i, level=0):
        token = tokens[i]
        level = int(token.tag[1])
        content_tokens = []
        i += 1
        while i < len(tokens) and tokens[i].type != 'heading_close':
            content_tokens.append(tokens[i])
            i += 1
        i += 1
        content = self.render_inline(content_tokens)
        if level == 1:
            styled_content = f"{t.red.bold}{content}{t.reset}"
        elif level == 2:
            styled_content = f"{t.yellow.bold}{content}{t.reset}"
        elif level == 3:
            styled_content = f"{t.green.bold}{content}{t.reset}"
        else:
            styled_content = f"{t.cyan.bold}{content}{t.reset}"
        return [styled_content], i

    def render_paragraph(self, tokens, i, level=0):
        content_tokens = []
        i += 1  # Skip 'paragraph_open'
        while i < len(tokens) and tokens[i].type != 'paragraph_close':
            content_tokens.append(tokens[i])
            i += 1
        i += 1
        content = self.render_inline(content_tokens).strip()
        indent = "  " * level
        return [f"{indent}{content}"], i

    def render_code_block(self, tokens, i, level=0):
        token = tokens[i]
        if token.type == 'fence':
            lang = token.info.strip()
            code = token.content.rstrip('\n')
        else:  # 'code_block'
            lang = ''
            code = token.content.rstrip('\n')
        try:
            lexer = get_lexer_by_name(lang) if lang else guess_lexer(code)
        except ClassNotFound:
            lexer = get_lexer_by_name('text')
        formatted_code = highlight(code, lexer, Terminal256Formatter()).rstrip('\n')
        indent = "  " * level
        lines = formatted_code.split('\n')
        return [f"{indent}{line}" for line in lines], i + 1

    def render_table(self, tokens, i, level=0):
        table_end = i
        while table_end < len(tokens) and tokens[table_end].type != 'table_close':
            table_end += 1
        table_tokens = tokens[i:table_end + 1]
        i = table_end + 1

        headers = []
        rows = []
        in_thead = False
        in_tbody = False
        current_row = []

        j = 0
        while j < len(table_tokens):
            token = table_tokens[j]
            if token.type == 'thead_open':
                in_thead = True
            elif token.type == 'thead_close':
                in_thead = False
            elif token.type == 'tbody_open':
                in_tbody = True
            elif token.type == 'tbody_close':
                in_tbody = False
            elif token.type == 'tr_open':
                current_row = []
            elif token.type in ('th_open', 'td_open'):
                content_tokens = []
                j += 1
                while j < len(table_tokens) and table_tokens[j].type not in ('th_close', 'td_close'):
                    content_tokens.append(table_tokens[j])
                    j += 1
                content = self.render_inline(content_tokens)
                current_row.append(content)
            elif token.type == 'tr_close':
                if in_thead:
                    headers = current_row
                elif in_tbody:
                    rows.append(current_row)
            j += 1

        table = Table.factory(
            [(t.blue.bold, header) for header in headers],
            *[[('', cell) for cell in row] for row in rows]
        )
        table_lines = []
        table.print(print_function=table_lines.append)
        indent = "  " * level
        return [f"{indent}{line}" for line in table_lines], i

    def render_bullet_list(self, tokens, i, level=0):
        list_items = []
        i += 1  # Skip 'bullet_list_open'
        while i < len(tokens) and tokens[i].type != 'bullet_list_close':
            if tokens[i].type == 'list_item_open':
                item_lines, new_i = self.render_list_item(tokens, i, level=level + 1)
                list_items.extend(item_lines)
                i = new_i
            else:
                i += 1
        i += 1  # Skip 'bullet_list_close'
        return list_items, i

    def render_ordered_list(self, tokens, i, level=0):
        list_items = []
        i += 1  # Skip 'ordered_list_open'
        item_number = 1
        while i < len(tokens) and tokens[i].type != 'ordered_list_close':
            if tokens[i].type == 'list_item_open':
                item_lines, new_i = self.render_list_item(tokens, i, level=level + 1, ordered=True, number=item_number)
                list_items.extend(item_lines)
                i = new_i
                item_number += 1
            else:
                i += 1
        i += 1  # Skip 'ordered_list_close'
        return list_items, i

    def render_list_item(self, tokens, i, level=0, ordered=False, number=None):
        content_blocks = []
        i += 1  # Skip 'list_item_open'
        while i < len(tokens) and tokens[i].type != 'list_item_close':
            token = tokens[i]
            if token.type in self.render_methods:
                rendered_lines, new_i = self.render_methods[token.type](tokens, i, level=level)
                content_blocks.append(rendered_lines)
                i = new_i
            else:
                i += 1
        i += 1  # Skip 'list_item_close'

        indent = "  " * (level - 1)
        prefix = f"{indent}{number}." if ordered else f"{indent}•"
        output_lines = []

        if content_blocks:
            # Flatten content blocks into a single list of lines
            all_lines = []
            for block in content_blocks:
                all_lines.extend(block)

            # First line gets the prefix with a single space
            first_content = all_lines[0].lstrip()
            output_lines.append(f"{prefix} {first_content}")

            # Subsequent lines are indented to align with nesting level
            for line in all_lines[1:]:
                output_lines.append(f"{'  ' * level}{line}")
        else:
            output_lines.append(prefix)

        return output_lines, i

    def render_inline(self, tokens):
        output = []
        for token in tokens:
            if token.type == 'text':
                output.append(token.content or '')
            elif token.type == 'inline':
                output.append(self.render_inline(token.children or []))
            elif token.type == 'strong_open':
                output.append(str(t.bold))
            elif token.type == 'strong_close':
                output.append(str(t.reset))
            elif token.type == 'em_open':
                output.append(str(t.italic))
            elif token.type == 'em_close':
                output.append(str(t.reset))
            elif token.type == 'code':
                output.append(f"{t.gray}{token.content}{t.reset}")
        return ''.join(output)

def md2term(markdown_text):
    md = MarkdownIt().enable('table')
    tokens = md.parse(markdown_text)
    renderer = TerminalRenderer()
    result = renderer.render(tokens)
    return result


def mdprint(markdown_text):
    print(md2term(markdown_text))
