import sys
import re
import math
import random
import os
import sqlite3
import duckdb
import csv
import io
import json
import glob
import subprocess
import requests
from datetime import datetime, timedelta
import webbrowser
import zipfile
import xlrd3
from tui_runner import FormRunner

csv.field_size_limit(1024 * 1024)

class SqliteStringFunctions:
    """
    A class to encapsulate custom string functions for SQLite.
    All methods are static as they don't depend on instance state.
    """
    @staticmethod
    def reverse(s):
      if not isinstance(s, str): return None
      return s[::-1]

    @staticmethod
    def stuff(s, start, length, insert_str):
      if not all(isinstance(arg, (str, int)) for arg in [s, start, length, insert_str]):
          if not isinstance(s, str) or not isinstance(insert_str, str) or \
             not isinstance(start, int) or not isinstance(length, int):
              return None
      start_index = start - 1
      if start_index < 0 or start_index > len(s): return s
      part1 = s[:start_index]
      part2 = s[start_index + length:]
      return part1 + insert_str + part2

    @staticmethod
    def left(s, num_chars):
      if not isinstance(s, str) or not isinstance(num_chars, int): return None
      return s[:num_chars]

    @staticmethod
    def right(s, num_chars):
      if not isinstance(s, str) or not isinstance(num_chars, int): return None
      if num_chars <= 0: return ""
      return s[-num_chars:]

    @staticmethod
    def lpad(s, length, pad_str):
      if not isinstance(s, str) or not isinstance(length, int) or not isinstance(pad_str, str): return None
      if len(s) >= length: return s[:length]
      return (pad_str * (length - len(s) + len(pad_str) -1))[:length - len(s)] + s

    @staticmethod
    def rpad(s, length, pad_str):
      if not isinstance(s, str) or not isinstance(length, int) or not isinstance(pad_str, str): return None
      if len(s) >= length: return s[:length]
      return (s + pad_str * (length - len(s) + len(pad_str) -1))[:length]

    @staticmethod
    def replicate(s, count):
      if not isinstance(s, str) or not isinstance(count, int): return None
      return s * count

    @staticmethod
    def charindex(substring, s):
      if not isinstance(s, str) or not isinstance(substring, str): return None
      try:
        return s.find(substring) + 1
      except:
        return 0

    @classmethod
    def register_all(cls, conn):
        functions_to_register = {
            "REVERSE": (1, cls.reverse), "STUFF": (4, cls.stuff), "LEFT$": (2, cls.left),
            "RIGHT$": (2, cls.right), "LPAD": (3, cls.lpad), "RPAD": (3, cls.rpad),
            "REPLICATE": (2, cls.replicate), "CHARINDEX": (2, cls.charindex),
        }
        for name, (num_params, func) in functions_to_register.items():
            conn.create_function(name, num_params, func)

# =================================================================
# GLOBAL STATE AND CONFIGURATION
# =================================================================
class OutputConfig:
    def __init__(self):
        self.mode = "CONSOLE"
        self.format = "TEXT"
        self.file_path = ""

g_output_config = OutputConfig()

# =================================================================
# Exception class for loop exits
# =================================================================
class LoopExit(Exception):
    """Exception raised to exit from a loop early."""
    pass

class ProgramEnd(Exception):
    """Exception raised to signal the END of the program."""
    pass
    
# =================================================================
# APPLICATION LOGIC
# =================================================================
def preprocess_continuations(source_code):
    result, i, in_string, in_comment, string_char = [], 0, False, False, None
    while i < len(source_code):
        char = source_code[i]
        if not in_string and not in_comment:
            if char.upper() == 'R' and source_code[i:i+3].upper() == 'REM': in_comment = True
            elif char == "'": in_comment = True
            elif char in ['"', '`']: in_string, string_char = True, char
        elif in_string and char == string_char:
            if char == '"' and i + 1 < len(source_code) and source_code[i + 1] == '"':
                result.append(char); i += 1; result.append(source_code[i]); i += 1; continue
            else: in_string, string_char = False, None
        elif char == '\n': in_comment = False
        if (char == '_' and not in_string and not in_comment and i + 1 < len(source_code) and source_code[i + 1] == '\n'):
            result.append(' '); i += 2; continue
        result.append(char); i += 1
    return ''.join(result)

class Lexer:
    def __init__(self, source_code):
        lines = source_code.splitlines()
        numbered = [f"{i+1}: {line}" for i, line in enumerate(lines)]
        self.raw_source_code = source_code # "\n".join(numbered)
        self.line_starts = [0]
        for match in re.finditer(r"\n", source_code):
            self.line_starts.append(match.end())
        self.tokens = self._tokenize()

    def get_line_col(self, pos):
        line = 1
        for i, start in enumerate(self.line_starts):
            if start > pos: break
            line = i + 1
        col = pos - self.line_starts[line-1] + 1
        return line, col

    def _tokenize(self):
        replacements = {r'\bEND\s+IF\b': 'ENDIF', r'\bLINE\s+INPUT\b': 'LINEINPUT', r'\bEND\s+LOOP\b': 'ENDLOOP',
                        r'\bFOR\s+EACH\b': 'FOREACH', r'\bEND\s+TRANSACTION\b': 'ENDTRANSACTION', r'\bREAD\s+FILE\b': 'READFILE',
                        r'\bTO\s+FILE\b': 'TOFILE', r'\bINTO\s+FILE\b': 'INTOFILE', 
                        r'\bANALYZE\s+CSV\b': 'ANALYZECSV',r'\bANALYZE\s+FIXED\b': 'ANALYZEFIXED',
                        r'\bANALYZE\s+JSON\b': 'ANALYZEJSON', r'\bANALYZE\s+FILE\b': 'ANALYZEFILE',
                        r'\bON\s+ERROR\s+GOTO\b': 'ONERRORGOTO',
                        r'\bEND\s+FORM\b': 'ENDFORM',r'\bOPEN\s+FORM\b': 'OPENFORM',
                        r'\bLIST\s+FIELDS\b': 'LISTFIELDS'}
        code = self.raw_source_code
        for pattern, repl in replacements.items():
            code = re.sub(pattern, repl, code, flags=re.IGNORECASE)
        self.modified_source_code = code

        token_specification = [
            # For giggles
            ('FORM', r'\bFORM\b(?!\$)'),  
            ('ENDFORM', r'\bENDFORM\b(?!\$)'),
            ('FIELD', r'\bFIELD\b(?!\$)'),
            ('BUTTON', r'\bBUTTON\b(?!\$)'),
            ('TITLE', r'\bTITLE\b(?!\$)'),
            ('TYPE', r'\bTYPE\b(?!\$)'),
            ('SIZE', r'\bSIZE\b(?!\$)'),
            ('CHOICE', r'\bCHOICE\b(?!\$)'),
            ('ACTION', r'\bACTION\b(?!\$)'),
            ('SOURCE', r'\bSOURCE\b(?!\$)'),
            ('LISTFIELDS', r'\bLISTFIELDS\b(?!\$)'),
            ('OPENFORM', r'\bOPENFORM\b(?!\$)'),
            ('HEADING', r'\bHEADING\b(?!\$)'),
            ('TEXTBLOCK', r'\bTEXTBLOCK\b(?!\$)'),
            ('LABEL', r'\bLABEL\b(?!\$)'),
            ('REQUIRED', r'\bREQUIRED\b(?!\$)'),
            ('READONLY', r'\bREADONLY\b(?!\$)'),
            ('MESSAGE', r'\bMESSAGE\b(?!\$)'),
            ('MINLENGTH', r'\bMINLENGTH\b(?!\$)'),
            ('MAXLENGTH', r'\bMAXLENGTH\b(?!\$)'),
            ('MINVALUE', r'\bMINVALUE\b(?!\$)'),
            ('PATTERN', r'\bPATTERN\b(?!\$)'),
            ('SEPARATOR', r'\bSEPARATOR\b(?!\$)'),
            ('PLACEHOLDER', r'\bPLACEHOLDER\b(?!\$)'),
            ('MATCHES', r'\bMATCHES\b(?!\$)'),
            ('DISPLAY', r'\bDISPLAY\b(?!\$)'),
            # ---------------------------
            ('STRING', r'"([^"]|"")*"'), ('BACKTICK_STRING', r'`[^`]*`'), ('ASSIGN', r'='),('NUMBER', r'\d+(\.\d*)?'),
            ('REM', r'REM[^\n]*'), ('AND', r'\bAND\b(?!\$)'), ('OR', r'\bOR\b(?!\$)'), ('FOREACH', r'\bFOREACH\b(?!\$)'),
            ('ANALYZECSV', r'\bANALYZECSV\b'), ('ANALYZEJSON', r'\bANALYZEJSON\b'), ('ANALYZEFILE', r'\bANALYZEFILE\b'),
            ('LINEINPUT', r'\bLINEINPUT\b(?!\$)'), ('TOFILE', r'\bTOFILE\b(?!\$)'), ('READFILE', r'\bREADFILE\b(?!\$)'),
            ('ENDLOOP', r'\bENDLOOP\b(?!\$)'), ('DATABASE', r'\bDATABASE\b(?!\$)'), ('SELECT', r'\bSELECT\b(?!\$)'),
            ('INSERT', r'\bINSERT\b(?!\$)'), ('DELETE', r'\bDELETE\b(?!\$)'), ('DESCRIBE', r'\bDESCRIBE\b(?!\$)'),
            ('UPDATE', r'\bUPDATE\b(?!\$)'), ('CREATE', r'\bCREATE\b(?!\$)'), ('DROP', r'\bDROP\b(?!\$)'),
            ('BEGIN', r'\bBEGIN\b(?!\$)'), ('COMMIT', r'\bCOMMIT\b(?!\$)'), ('ROLLBACK', r'\bROLLBACK\b(?!\$)'),
            ('ENDTRANSACTION', r'\bENDTRANSACTION\b(?!\$)'), ('WITH', r'\bWITH\b(?!\$)'), ('FETCH', r'\bFETCH\b(?!\$)'),
            ('POST', r'\bPOST\b(?!\$)'), ('EXISTS', r'\bEXISTS\b(?!\$)'), ('ERROR', r'\bERROR\b(?!\$)'),
            ('XML', r'\bXML\b(?!\$)'), ('JSON', r'\bJSON\b(?!\$)'), ('JSONL', r'\bJSONL\b(?!\$)'),
            ('PARSE', r'\bPARSE\b(?!\$)'), ('INTO', r'\bINTO\b(?!\$)'),('DUMP', r'\bDUMP\b(?!\$)'), 
            ('HASH', r'\bHASH\b(?!\$)'),('SORT', r'\bSORT\b(?!\$)'),('FIXED', r'\bFIXED\b(?!\$)'),
            ('ARRAY', r'\bARRAY\b(?!\$)'), ('GOSUB', r'\bGOSUB\b(?!\$)'), ('RETURN', r'\bRETURN\b(?!\$)'),
            ('SHELL', r'\bSHELL\b(?!\$)'), ('BROWSER', r'\bBROWSER\b(?!\$)'),('RUN', r'\bRUN\b(?!\$)'),
            ('DIM', r'\bDIM\b(?!\$)'), ('REDIM', r'\bREDIM\b(?!\$)'),('CHAIN', r'\bCHAIN\b(?!\$)'),
            ('OPTIONS', r'\bOPTIONS\b(?!\$)'), ('CSV', r'\bCSV\b(?!\$)'), ('HTML', r'\bHTML\b(?!\$)'), ('TABLE', r'\bTABLE\b(?!\$)'),
            ('LOAD', r'\bLOAD\b(?!\$)'), ('APPEND', r'\bAPPEND\b(?!\$)'), ('REPLACE', r'\bREPLACE\b(?!\$)'),
            ('EXCEL', r'\bEXCEL\b(?!\$)'), ('WRITE', r'\bWRITE\b(?!\$)'), ('USING', r'\bUSING\b(?!\$)'),
            ('OPEN', r'\bOPEN\b(?!\$)'), ('CLOSE', r'\bCLOSE\b(?!\$)'), ('INPUT', r'\bINPUT\b(?!\$)'),
            ('SET', r'\bSET\b(?!\$)'), ('OUTPUT', r'\bOUTPUT\b(?!\$)'), ('AS', r'\bAS\b(?!\$)'),
            ('PRINT', r'\bPRINT\b(?!\$)'), ('LET', r'\bLET\b(?!\$)'), ('IF', r'\bIF\b(?!\$)'), ('THEN', r'\bTHEN\b(?!\$)'),
            ('ELSEIF', r'\bELSEIF\b(?!\$)'),('ELSE', r'\bELSE\b(?!\$)'), ('ENDIF', r'\bENDIF\b(?!\$)'), 
            ('FOR', r'\bFOR\b(?!\$)'), ('TO', r'\bTO\b(?!\$)'),
            ('ZIP', r'\bZIP\b(?!\$)'),('UNZIP', r'\bUNZIP\b(?!\$)'),
            ('DO', r'\bDO\b(?!\$)'),('UNTIL', r'\bUNTIL\b(?!\$)'),
            ('STEP', r'\bSTEP\b(?!\$)'), ('NEXT', r'\bNEXT\b(?!\$)'), ('IN', r'\bIN\b(?!\$)'), ('LOOP', r'\bLOOP\b(?!\$)'),
            ('WHILE', r'\bWHILE\b(?!\$)'), ('WEND', r'\bWEND\b(?!\$)'), ('NOT', r'\bNOT\b(?!\$)'), ('END', r'\bEND\b(?!\$)'),
            ('EXIT', r'\bEXIT\b(?!\$)'), ('FILES', r'\bFILES\b(?!\$)'), ('CHDIR', r'\bCHDIR\b(?!\$)'),
            ('MKDIR', r'\bMKDIR\b(?!\$)'), ('RMDIR', r'\bRMDIR\b(?!\$)'), ('KILL', r'\bKILL\b(?!\$)'),
            ('ONERRORGOTO', r'\bONERRORGOTO\b'),('RESUME', r'\bRESUME\b(?!\$)'),
            ('TRON', r'\bTRON\b(?!\$)'), ('TROFF', r'\bTROFF\b(?!\$)'),('GOTO', r'\bGOTO\b(?!\$)'), 
            ('DETAILS', r'\bDETAILS\b(?!\$)'), 
            ('PUSH', r'\bPUSH\b(?!\$)'),
            ('POP', r'\bPOP\b(?!\$)'),
            ('SHIFT', r'\bSHIFT\b(?!\$)'),
            ('UNSHIFT', r'\bUNSHIFT\b(?!\$)'),
            ('SPLICE', r'\bSPLICE\b(?!\$)'),
            ('REVERSE', r'\bREVERSE\b(?!\$)'),
            ('ID', r'(?!INTO\b)[a-zA-Z][a-zA-Z0-9_]*\$?'), ('OP', r"[+\-*/]"),
            ('RELOP', r'<>|<=|>=|<|>'), ('HASH_SYM', r'#'), ('LPAREN', r'\('), ('RPAREN', r'\)'), ('COMMA', r','),
            ('SEMICOLON', r';'), ('COLON', r':'), ('DOT', r'\.'), ('COMMENT', r"'[^\n]*"), ('NEWLINE', r'\n'),
            ('SKIP', r'[ \t\u00A0]+'), ('MISMATCH', r'.'),
        ]
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
        raw_tokens, tokens, is_start_of_line = [], [], True
        for mo in re.finditer(tok_regex, code, re.IGNORECASE):
            kind, value, pos = mo.lastgroup, mo.group(), mo.start()
            if kind in ['SKIP', 'REM', 'COMMENT']: continue
            if kind == 'MISMATCH':
                line, col = self.get_line_col(pos); raise RuntimeError(f"Unexpected character '{value}' at line {line}, col {col}")
            raw_tokens.append((kind, value, pos))
        i = 0
        while i < len(raw_tokens):
            kind, value, pos = raw_tokens[i]
            if kind == 'NEWLINE': 
                is_start_of_line = True 
                tokens.append((kind, value, pos))
                i += 1
                continue
            if is_start_of_line and kind in Interpreter.SQL_KEYWORDS:
                semicolon_pos = self.modified_source_code.find(';', pos)
                if semicolon_pos != -1:
                    sql_end_pos = semicolon_pos + 1
                    sql_text = self.modified_source_code[pos:sql_end_pos].strip()
                    tokens.append(('SQL_STRING', sql_text, pos))
                    while i < len(raw_tokens) and raw_tokens[i][2] < sql_end_pos: i += 1
                    is_start_of_line = False; continue
            # General rule: If we see `( SELECT ... )`, bundle it as a subquery.
            if kind == 'LPAREN' and i + 1 < len(raw_tokens) and raw_tokens[i+1][0] in Interpreter.SQL_KEYWORDS:
                lp_pos = pos
                nesting, search_pos, end_paren_pos, in_string = 1, lp_pos + 1, -1, False
                
                # Scan the raw source code to find the matching closing parenthesis
                while search_pos < len(self.modified_source_code):
                    char = self.modified_source_code[search_pos]
                    if char == "'": in_string = not in_string
                    elif not in_string and char == '(': nesting += 1
                    elif not in_string and char == ')':
                        nesting -= 1
                        if nesting == 0:
                            end_paren_pos = search_pos; break
                    search_pos += 1
                
                if nesting != 0: self._error("Unmatched parenthesis in SQL subquery.")
                
                # Create the new token sequence: ( SQL_STRING )
                sql_text = self.modified_source_code[lp_pos + 1 : end_paren_pos]
                tokens.append(('LPAREN', '(', lp_pos))
                tokens.append(('SQL_STRING', sql_text.strip(), lp_pos + 1))
                tokens.append(('RPAREN', ')', end_paren_pos))
                
                # Advance the main loop past all the tokens we just consumed.
                while i < len(raw_tokens) and raw_tokens[i][2] <= end_paren_pos:
                    i += 1
                is_start_of_line = False
                continue
            if (kind in ('IN', 'EXISTS', 'ASSIGN')) and i + 1 < len(raw_tokens) and raw_tokens[i+1][0] == 'LPAREN':
                if i + 2 < len(raw_tokens) and raw_tokens[i+2][0] in Interpreter.SQL_KEYWORDS:
                    tokens.append((kind, value, pos)); lp_pos = raw_tokens[i+1][2]; nesting, search_pos, end_paren_pos, in_string = 1, lp_pos + 1, -1, False
                    while search_pos < len(self.modified_source_code):
                        char = self.modified_source_code[search_pos]
                        if char == "'": in_string = not in_string
                        elif not in_string and char == '(': nesting += 1
                        elif not in_string and char == ')': nesting -= 1
                        if nesting == 0: end_paren_pos = search_pos; break
                        search_pos += 1
                    if nesting != 0: raise RuntimeError("Unmatched parens in SQL expression")
                    sql_text = self.modified_source_code[lp_pos + 1 : end_paren_pos]
                    tokens.extend([('LPAREN', '(', lp_pos), ('SQL_STRING', sql_text.strip(), lp_pos + 1), ('RPAREN', ')', end_paren_pos)])
                    while i < len(raw_tokens) and raw_tokens[i][2] <= end_paren_pos: i += 1
                    is_start_of_line = False
                    if kind == 'EXISTS':
                        text_after_paren = self.modified_source_code[end_paren_pos + 1:].lstrip()
                        next_token_is_then = (i < len(raw_tokens) and raw_tokens[i][0] == 'THEN')
                        if text_after_paren.upper().startswith('THEN') and not next_token_is_then:
                            tokens.append(('THEN', 'THEN', end_paren_pos + 1))
                    continue
            u_value = value.upper()
            #if kind != 'STRING': value = u_value
            if kind == 'BACKTICK_STRING': kind = 'STRING'
            if u_value == 'ENDIF': kind, value = 'END IF', 'END IF'
            elif u_value == 'LINEINPUT': kind, value = 'LINE INPUT', 'LINE INPUT'
            elif u_value == 'READFILE': kind, value = 'READ FILE', 'READ FILE' 
            elif u_value == 'TOFILE': kind, value = 'TO FILE', 'TO FILE'
            elif u_value == 'ENDFORM': kind, value = 'ENDFORM', 'END FORM'
            #elif u_value == 'ENDLOOP': kind, value = 'END LOOP', 'END LOOP'
            elif u_value == 'FOREACH': kind, value = 'FOR EACH', 'FOR EACH'
            elif u_value == 'ENDTRANSACTION': kind, value = 'END TRANSACTION', 'END TRANSACTION'
            elif u_value == 'ANALYZECSV': kind, value = 'ANALYZE CSV', 'ANALYZE CSV'
            elif u_value == 'ANALYZEJSON': kind, value = 'ANALYZE JSON', 'ANALYZE JSON'
            elif u_value == 'ANALYZEFILE': kind, value = 'ANALYZE FILE', 'ANALYZE FILE'
            elif u_value == 'ANALYZEFIXED': kind, value = 'ANALYZE FIXED', 'ANALYZE FIXED'
            elif u_value == 'ONERRORGOTO': kind, value = 'ON ERROR GOTO', 'ON ERROR GOTO'
            tokens.append((kind, value, pos)); is_start_of_line = False; i += 1
        return tokens
        
class Formatter:
    @staticmethod
    def format(format_string, values):
        output, val_idx, fmt_idx = "", 0, 0
        while val_idx < len(values):
            if fmt_idx >= len(format_string): break
            char = format_string[fmt_idx]
            if char in '#0*!&\\' or (char in '<>^' and format_string[fmt_idx+1:fmt_idx+2] == '\\'):
                mask_regex = re.compile(r"([<>^]?\\ *\\[\s]*|!|&+|[#0\*,]+\.?[#0]*\^*)")
                match = mask_regex.match(format_string, fmt_idx)
                if match:
                    mask = match.group(0)
                    output += Formatter._format_value(values[val_idx], mask)
                    val_idx += 1; fmt_idx += len(mask)
                else: output += char; fmt_idx += 1
            else: output += char; fmt_idx += 1
        return output
    @staticmethod
    def _format_value(value, mask):
        return Formatter._format_numeric(value, mask) if isinstance(value, (int, float)) else Formatter._format_string(str(value), mask)
    @staticmethod
    def _format_scientific(value, mask, is_negative):
        caret_pos = mask.find('^^^^')
        before_caret = mask[:caret_pos]
        mantissa_str, exponent_str = f"{value:e}".split('e')
        mantissa, exponent = float(mantissa_str), int(exponent_str)
        mantissa_formatted = Formatter._format_numeric(mantissa, before_caret, force_positive=True)
        exp_sign = '+' if exponent >= 0 else ''
        result = f"{mantissa_formatted}E{exp_sign}{exponent:02d}"
        if is_negative:
            if ' ' in result: return result.replace(' ', '-', 1)
            else: return '-' + result
        return result
    @staticmethod
    def _format_numeric(value, mask, force_positive=False):
        is_negative = value < 0 and not force_positive
        if is_negative: value = abs(value)
        if '^^^^' in mask: return Formatter._format_scientific(value, mask, is_negative)
        decimal_pos = mask.find('.')
        decimals = 0
        integer_mask = mask
        if decimal_pos != -1:
            decimals = len(re.findall(r'[#0]', mask[decimal_pos+1:]))
            integer_mask = mask[:decimal_pos]
        formatted_num = f"{value:.{decimals}f}"
        int_part, dec_part = formatted_num.split('.') if '.' in formatted_num else (formatted_num, "")
        result, int_idx, digit_count = "", len(int_part) - 1, 0
        has_leading_asterisk = integer_mask.strip().startswith('*')
        for i in range(len(integer_mask) - 1, -1, -1):
            mask_char = integer_mask[i]
            if mask_char in '#0*':
                if int_idx >= 0: result, int_idx, digit_count = int_part[int_idx] + result, int_idx - 1, digit_count + 1
                elif mask_char == '0': result, digit_count = '0' + result, digit_count + 1
                elif mask_char == '*' and has_leading_asterisk: result = '*' + result
                else: result = ' ' + result
            elif mask_char == ',':
                if digit_count > 0 and int_idx >= 0: result = ',' + result
                elif has_leading_asterisk: result = '*' + result
                else: result = ' ' + result
            else: result = mask_char + result
        if int_idx >= 0: result = int_part[:int_idx+1] + result
        if decimal_pos != -1: result += '.' + dec_part
        if is_negative:
            if ' ' in result: return result.replace(' ', '-', 1)
            elif '*' in result: return result.replace('*', '-', 1)
            else: return '-' + result
        return result
    @staticmethod
    def _format_string(value, mask):
        backslash_match = re.match(r'([<>^]?)\\(\s*)\\', mask)
        if backslash_match:
            justify, field_width = backslash_match.group(1) or '<', len(backslash_match.group(2)) + 2
            truncated_str = value[:field_width]
            if justify == '<': return truncated_str.ljust(field_width)
            if justify == '>': return truncated_str.rjust(field_width)
            if justify == '^': return truncated_str.center(field_width)
        if mask == '!': return value[0] if value else ' '
        if '&' in mask: return value.ljust(len(mask))
        return value

class Interpreter:
    SQL_KEYWORDS = {'SELECT', 'INSERT', 'DELETE', 'UPDATE', 'CREATE', 'DROP', 'WITH', 'BEGIN', 'COMMIT', 'ROLLBACK', 'END TRANSACTION'}

    def __init__(self, lexer, cmd_args=None, debug=False):
        self.lexer = lexer
        self.tokens = self.lexer.tokens
        self.token_index = 0
        self.variables = {}
        lines = self.lexer.raw_source_code.splitlines()
        numbered = [f"{i+1}: {line}" for i, line in enumerate(lines)]
        # Pre-define the PROGRAM$ system variable with the raw source code.
        #self.variables['PROGRAM$'] = "\n".join(numbered)
        self.file_handles = {}
        self.command_args = cmd_args if cmd_args is not None else []
        self.gosub_stack = []
        self.labels = {}
        self.form_definitions = {}
        self.db_engine = 'sqlite' # Set SQLite as the default engine
        self.db_connection = None
        self.sql_fatal_errors = True
        self.trace_mode = False   # FOR TRON AND TROFF
        self.program_terminated = False # Termination flag
        self.hash_keys_mode = 'PRESERVE_CASE'  # Default to preserve case
        self.run_stack = []
                
        # --- NEW: Error handling state ---
        self.error_handler_label = None
        self.in_error_handler = False
        self.error_resume_index = None
        
        self.debug_mode = debug # <-- And add this line
        self.jump_map = {}
        self._pre_scan_for_jumps()
        self._init_db()
        self._scan_for_labels()

    def _pre_scan_for_jumps(self):
        """
        Scans the token list to map all control structures.
        """
        stack = []
        
        for index, token in enumerate(self.tokens):
            token_type = token[0]

            if token_type == 'IF':
                # Check if it's a multi-line IF
                is_multi_line = False
                temp_index = index + 1
                while temp_index < len(self.tokens):
                    if self.tokens[temp_index][0] == 'THEN':
                        if (temp_index + 1) < len(self.tokens) and self.tokens[temp_index + 1][0] == 'NEWLINE':
                            is_multi_line = True
                        break
                    if self.tokens[temp_index][0] == 'NEWLINE':
                        break
                    temp_index += 1

                if is_multi_line:
                    stack.append(('IF', index))
                    self.jump_map[index] = {'elseifs': [], 'else': None, 'endif': None}

            elif token_type == 'DO':
                # Check if the previous token was EXIT. If so, this is not a loop start.
                if index > 0 and self.tokens[index - 1][0] == 'EXIT':
                    continue
                stack.append(('DO', index))
                self.jump_map[index] = {'loop': None}

            elif token_type == 'LOOP':
                # LOOP should only match with DO
                if not stack or stack[-1][0] != 'DO':
                    # This might be an error in the source, but let the parser handle it
                    continue
                do_type, do_index = stack.pop()
                self.jump_map[do_index]['loop'] = index

            elif token_type == 'ELSEIF':
                if stack and stack[-1][0] == 'IF':
                    if_index = stack[-1][1]
                    self.jump_map[if_index]['elseifs'].append(index)

            elif token_type == 'ELSE':
                if stack and stack[-1][0] == 'IF':
                    if_index = stack[-1][1]
                    self.jump_map[if_index]['else'] = index

            elif token_type == 'END IF':
                if not stack or stack[-1][0] != 'IF':
                    continue  # Let parser handle the error
                if_type, if_index = stack.pop()
                self.jump_map[if_index]['endif'] = index
            
        if stack:
            start_type, start_index = stack[-1]
            line, _ = self.lexer.get_line_col(self.tokens[start_index][2])
            self._error(f"Mismatched '{start_type}' on line {line} without a corresponding closing statement.")


    def _find_next_statement_index(self, start_index):
        """Find the index of the next statement (after a COLON or NEWLINE token)"""
        index = start_index
        # Skip to the end of the current statement
        while index < len(self.tokens):
            if self.tokens[index][0] in ['COLON', 'NEWLINE']:
                index += 1  # Skip the separator itself
                break
            index += 1
        return index
    
    def _parse_tron_statement(self):
        self._expect('TRON')
        self.trace_mode = True

    def _parse_troff_statement(self):
        self._expect('TROFF')
        self.trace_mode = False
    
    def _parse_goto_statement(self):
        """Parse and execute a GOTO statement."""
        self._expect('GOTO')
        label_name = self._expect('ID')[1]
        if label_name not in self.labels:
            self._error(f"Label '{label_name}' not found for GOTO.")
        self.token_index = self.labels[label_name]
    
    def _debug_state(self, message):
        """A helper function to print the current parser state."""
        if not self.debug_mode:
            return

        token = self._current_token()
        if token:
            line, col = self.lexer.get_line_col(token[2])
            print(f"DEBUG | {message:<40} | Token: {str(token[0]):<15} | Value: {str(token[1]):<15} | Line: {line}")
        else:
            print(f"DEBUG | {message:<40} | Token: None")

    def _error(self, message):
        """Raises a RuntimeError with enhanced token context."""
        idx = self.token_index
        
        # Get previous token, handling the start of the file
        prev_tok = self.tokens[idx - 1] if idx > 0 else None
        prev_tok_str = f"'{prev_tok[1]}'" if prev_tok else "(start)"
        
        # Get current token
        current_tok = self._current_token()
        
        # Get next token, handling the end of the file
        next_tok = self.tokens[idx + 1] if idx + 1 < len(self.tokens) else None
        next_tok_str = f"'{next_tok[1]}'" if next_tok else "(end)"

        if current_tok:
            line, col = self.lexer.get_line_col(current_tok[2])
            current_tok_str = f"'{current_tok[1]}' ({current_tok[0]})"
            
            # Construct the detailed error message
            error_context = f"\n  Context: {prev_tok_str} -> [{current_tok_str}] <- {next_tok_str}"
            raise RuntimeError(f"{message} at line {line}, col {col}.{error_context}")
        else:
            # Error at the very end of the file where there is no current token
            error_context = f"\n  Context: Reached unexpected end of file after {prev_tok_str}."
            raise RuntimeError(f"{message}.{error_context}")

    def _parse_database_statement(self):
        self._expect('DATABASE')
        token = self._current_token()

        if token and token[0] == 'OPEN':
            self._next_token()
            filename = self._parse_expression()
            self._init_db(filename)
        elif token and token[0] == 'CLOSE':
            self._next_token()
            self._init_db() # Re-initializes a new in-memory database
        elif token and token[0] == 'ID' and token[1].upper() == 'ENGINE':
            # --- ADD THIS LOGIC ---
            self._next_token() # Consume ENGINE
            engine_token = self._expect('ID')
            engine_name = engine_token[1].lower()
            if engine_name in ['sqlite', 'duckdb']:
                self.db_engine = engine_name
                print(f"Database engine set to {self.db_engine}.")
                # Close any existing connection when switching engines
                if self.db_connection:
                    self.db_connection.close()
                    self.db_connection = None
            else:
                self._error("Unsupported engine. Use SQLITE or DUCKDB.")
        else:
            self._error("Expected OPEN, CLOSE, or ENGINE after DATABASE")
            
    def _init_db(self, filename=":memory:"):
        if self.db_connection: 
            self.db_connection.close()
        #print(f"(Connecting using {self.db_engine} engine...)") # Optional debug message
        if self.db_engine == 'duckdb':
            self.db_connection = duckdb.connect(database=filename, read_only=False)
        else:
            self.db_connection = sqlite3.connect(filename, isolation_level=None)
            SqliteStringFunctions.register_all(self.db_connection)
        self.db_cursor = self.db_connection.cursor()

    def _scan_for_labels(self):
        for i, token in enumerate(self.tokens):
            if token[0] == 'ID' and i + 1 < len(self.tokens) and self.tokens[i+1][0] == 'COLON':
                label_name = token[1]
                if label_name in self.labels: self._error(f"Duplicate label found: {label_name}")
                self.labels[label_name] = i + 2

    def close(self):
        self._close_all_files()
        if self.db_connection: self.db_connection.close(); self.db_connection = None

    def __del__(self): self.close()

    def _close_all_files(self):
        for handle_info in self.file_handles.values(): handle_info['handle'].close()
        self.file_handles = {}

    def _current_token(self): return self.tokens[self.token_index] if self.token_index < len(self.tokens) else None
    def _peek_token(self): return self.tokens[self.token_index + 1] if self.token_index + 1 < len(self.tokens) else None
    
    def _next_token(self):
        if self.token_index < len(self.tokens): self.token_index += 1
        return self._current_token()
    
    def _expect(self, kind):
        token = self._current_token()
        if token and token[0] == kind: self._next_token(); return token
        self._error(f'Expected token {kind} but got {token[0] if token else "None"}')

    def _extract_sql_from_parens(self):
        self._expect('LPAREN'); sql_token = self._expect('SQL_STRING'); self._expect('RPAREN'); return sql_token[1]

    def _execute_sql(self, sql_string, is_query=False):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': "", 'SQL_ROWCOUNT': 0.0, 'SQL_FOUND': 0.0, 'SQL_NOTFOUND': -1.0})
        bind_vars = re.findall(r':([a-zA-Z][a-zA-Z0-9_]*\$?)', sql_string)
        params = [self.variables[var.upper()] for var in bind_vars if var.upper() in self.variables or self._error(f"Bind variable ':{var}' not found.")]
        final_sql = re.sub(r':([a-zA-Z][a-zA-Z0-9_]*\$?)', '?', sql_string)
        try:
            result = self.db_cursor.execute(final_sql, params)
            if not is_query:
                row_count = self.db_cursor.rowcount
                self.variables['SQL_ROWCOUNT'] = float(row_count if row_count != -1 else 0)
                if row_count > 0: self.variables['SQL_FOUND'], self.variables['SQL_NOTFOUND'] = -1.0, 0.0
                else: self.variables['SQL_FOUND'], self.variables['SQL_NOTFOUND'] = 0.0, -1.0
            
            if is_query:
                # DuckDB returns a relation object, SQLite's cursor is the iterable
                return result.fetchall() if self.db_engine == 'duckdb' else self.db_cursor.fetchall()
            return None
        except (sqlite3.Error, duckdb.Error) as e: # Catch errors from either library
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            if self.sql_fatal_errors:
                self._error(f"Fatal DB Error: {e}")
            return None

    def run_block(self, end_tokens):
        while True:
            token = self._current_token()
            if not token or token[0] in end_tokens:
                break
            if not self._parse_line():
                break
            if self.program_terminated: break

    def _skip_block(self, start_token, end_token):
        level = 1
        while self._current_token() and level > 0:
            current_token = self._current_token()
            self._next_token()
            if not current_token: break
            if current_token[0] == start_token: level += 1
            elif current_token[0] == end_token: level -= 1

    def _find_next_line_index(self, start_index):
        """Finds the index of the token that starts the next line."""
        idx = start_index
        # First, advance past the current line's tokens
        while idx < len(self.tokens) and self.tokens[idx][0] != 'NEWLINE':
            idx += 1
        # Then, advance past the NEWLINE token itself to the start of the next line
        if idx < len(self.tokens) and self.tokens[idx][0] == 'NEWLINE':
            idx += 1
        return idx
        
    def _parse_line(self):
        """Parse a line which may contain multiple colon-separated statements."""
        # --- START OF TRACING LOGIC ---
        if self.trace_mode:
            token = self._current_token()
            if token and token[0] != 'NEWLINE':
                line_num, _ = self.lexer.get_line_col(token[2])
                
                # Look up the actual source line text
                start_pos = self.lexer.line_starts[line_num - 1]
                end_pos = self.lexer.line_starts[line_num] if line_num < len(self.lexer.line_starts) else len(self.lexer.raw_source_code)
                source_line = self.lexer.raw_source_code[start_pos:end_pos].strip()
                
                # Don't trace the TROFF command itself
                if token[0] != 'TROFF':
                    print(f"[{line_num}]> {source_line}")
        # --- END OF TRACING LOGIC ---
        
        if not self._current_token():
            return False
            
        if self._current_token()[0] == 'NEWLINE':
            self._next_token()
            return True
        
        # Parse statements until we hit a NEWLINE or END
        while self._current_token() and self._current_token()[0] not in ['NEWLINE']:
            # Store the resume point BEFORE parsing the statement
            resume_point = self._find_next_statement_index(self.token_index)
            
            try:
                self._parse_statement()
            except (LoopExit):
                raise # Re-raise control-flow exceptions so loop parsers can catch them
            except Exception as e:
                if not self.error_handler_label or self.in_error_handler:
                    raise e
                    
                # Set error state with the saved resume point
                self.in_error_handler = True
                self.error_resume_index = resume_point
                if self.variables.get('ERR', 0.0) == 0.0:
                    self.variables['ERR'] = 1.0
                self.variables['ERRMSG$'] = str(e)
                self.token_index = self.labels[self.error_handler_label]
            
            if self._current_token() and self._current_token()[0] == 'COLON':
                self._next_token()
            elif self._current_token() and self._current_token()[0] not in ['NEWLINE']:
                break
        
        if self._current_token() and self._current_token()[0] == 'NEWLINE':
            self._next_token()
        return True

    def _parse_end_statement(self):
        self._expect('END')
        self.program_terminated = True
        sys.exit(0)

    def _parse_statement(self):
        token = self._current_token()
        # Skip label
        if token and token[0] == 'ID' and self._peek_token() and self._peek_token()[0] == 'COLON':
            self._next_token()
            self._next_token()
            if not self._current_token() or self._current_token()[0] in ['NEWLINE', 'END']:
                return

        token = self._current_token()
        if not token: return

        if token[0] == 'SQL_STRING':
            sql_text = token[1].strip()
            self._next_token()
            is_select = sql_text.upper().startswith(('SELECT', 'WITH'))
            if is_select:
                if g_output_config.mode == "OFF": return
                results = self._execute_sql(sql_text, is_query=True)
                column_names = [desc[0] for desc in self.db_cursor.description] if self.db_cursor.description else []
                self._handle_output(results, column_names)
            else:
                self._execute_sql(sql_text)  
        elif token[0] == 'END':
            self._parse_end_statement()
        elif token[0] == 'ON ERROR GOTO':
            self._parse_on_error_statement()
        elif token[0] == 'GOTO':
            self._parse_goto_statement()
        elif token[0] == 'RESUME':
            self._parse_resume_statement()
        elif token[0] == 'SET':
            self._parse_set_statement()
        elif token[0] == 'IF':
            self._parse_if_statement()
        elif token[0] == 'DO':
            self._parse_do_loop_statement()
        elif token[0] == 'FOR EACH': 
            self._parse_for_each_statement()
        elif token[0] == 'FOR':
             # Look ahead to see if there's an 'IN' before an '='.
            is_in_loop = False
            temp_index = self.token_index + 1
            while temp_index < len(self.tokens) and self.tokens[temp_index][0] != 'NEWLINE':
                if self.tokens[temp_index][0] == 'IN':
                    is_in_loop = True
                    break
                if self.tokens[temp_index][0] == 'ASSIGN':
                    break # This is a FOR i = 1 TO 10 loop
                temp_index += 1
            
            if is_in_loop:
                # It's a FOR...IN loop. Now, is it SQL or CSV?
                # We need to find the 'IN' token again to check what follows it.
                in_index = self.token_index + 1
                while self.tokens[in_index][0] != 'IN':
                    in_index += 1
                
                # Check the token right after 'IN'
                if (in_index + 1) < len(self.tokens) and self.tokens[in_index + 1][0] == 'CSV':
                    self._parse_for_in_csv_loop()
                elif (in_index + 1) < len(self.tokens) and self.tokens[in_index + 1][0] == 'JSONL':
                    self._parse_for_in_jsonl_loop()
                elif (in_index + 1) < len(self.tokens) and self.tokens[in_index + 1][0] == 'JSON':
                    self._parse_for_in_json_loop()
                else:  # Otherwise, assume it's a SQL loop that expects parentheses.
                    self._parse_for_in_sql_loop()
            else:   # It's a standard FOR i = 1 TO 10 loop.
                self._parse_for_statement()
        elif token[0] == 'SORT':
            self._parse_sort_statement()
        elif token[0] == 'FILES':
            self._parse_files_statement()
        elif token[0] == 'ID' and token[1].upper() == 'NAME':
            self._parse_name_statement()
        elif token[0] == 'DUMP':           
            self._parse_dump_statement()
        elif token[0] == 'CHDIR':           
            self._parse_chdir_statement()
        elif token[0] == 'MKDIR':           
            self._parse_mkdir_statement()
        elif token[0] == 'RMDIR':           
            self._parse_rmdir_statement()
        elif token[0] == 'KILL':           
            self._parse_kill_statement()
        elif token[0] == 'SHELL':
            self._parse_shell_statement() 
        elif token[0] == 'CHAIN':   # Replace current script with another DbBASIC script
            self._parse_chain_statement()
        elif token[0] == 'RUN':   # Run another script and come back
            self._parse_run_statement()
        elif token[0] == 'ZIP':
            self._parse_zip_statement()
        elif token[0] == 'UNZIP':
            self._parse_unzip_statement()
        elif token[0] == 'BROWSER':
            self._parse_browser_statement()
        elif token[0] == 'EXIT':
            self._parse_exit_statement()
        elif token[0] == 'ERROR':
            self._parse_error_statement()
        elif token[0] == 'FETCH':
            self._parse_fetch_statement()
        elif token[0] == 'PARSE': 
            self._parse_json_statement()
        elif token[0] == 'LOAD':
            self._parse_load_statement()
        elif token[0] == 'ANALYZE FILE':
            self._parse_analyze_file_statement()
        elif token[0] == 'ANALYZE CSV':
            self._parse_analyze_csv_statement()
        elif token[0] == 'ANALYZE FIXED':
            self._parse_analyze_fixed_statement()
        elif token[0] == 'ANALYZE JSON':
            self._parse_analyze_json_statement()
        elif token[0] == 'PRINT':
            self._parse_print_statement()
        elif token[0] == 'DESCRIBE':
            self._parse_describe_statement()
        elif token[0] == 'WRITE':
            self._parse_write_statement()
        elif token[0] == 'DATABASE':
            self._parse_database_statement()
        elif token[0] == 'LET' or token[0] == 'ID':
             self._parse_assignment_statement()
        elif token[0] == 'DIM':
            self._parse_dim_statement()
        elif token[0] == 'REDIM':
            self._parse_redim_statement()
        elif token[0] == 'WHILE':
            self._parse_while_statement()
        elif token[0] == 'OPEN':
            self._parse_open_statement()
        elif token[0] == 'CLOSE':
            self._parse_close_statement()
        elif token[0] == 'READ FILE':
            self._parse_read_file_statement()
        elif token[0] == 'LINE INPUT':
            self._parse_line_input_statement()
        elif token[0] == 'INPUT':
            self._parse_input_statement()
        elif token[0] == 'GOSUB':
            self._parse_gosub_statement()
        elif token[0] == 'RETURN':
            self._parse_return_statement()
        elif token[0] == 'PUSH':
            self._parse_push_statement()
        elif token[0] == 'POP':
            self._parse_pop_statement()
        elif token[0] == 'UNSHIFT':
            self._parse_unshift_statement()
        elif token[0] == 'SHIFT':
            self._parse_shift_statement()
        elif token[0] == 'SPLICE':
            self._parse_splice_statement()
        elif token[0] == 'REVERSE':
            self._parse_reverse_statement()
        elif token[0] == 'TRON':
            self._parse_tron_statement()
        elif token[0] == 'TROFF':
            self._parse_troff_statement()
        elif token[0] in ['ELSE', 'ELSEIF', 'END IF', 'NEXT', 'WEND', 'END LOOP', 'LOOP']:
            self._error(f"Unexpected '{token[0]}'")
        elif token[0] == 'ID' and token[1].upper() == 'COPY':
            self._parse_copy_statement()
        
        elif token[0] == 'FORM':
            self._parse_form_statement()
        elif token[0] == 'OPENFORM':
            self._parse_open_form_statement()
        else:
            self._error(f"Unknown statement: {token[0]}")

    def run(self):
        try:
            while self._current_token() and self._current_token()[0] != 'END':
                if not self._parse_line():
                    break
                if self.program_terminated:
                    break
        except ProgramEnd:
            return
        except LoopExit as e:
            self._error(f"'{e.args[0]}' without matching loop structure")
        except Exception as e:
            # If we get here and there's an error handler but we're not in it, jump to it
            if self.error_handler_label and not self.in_error_handler:
                self.in_error_handler = True
                self.variables['ERR'] = 1.0
                self.variables['ERRMSG$'] = str(e)
                self.token_index = self.labels[self.error_handler_label]
                # Continue execution from error handler
                try:
                    while self._current_token() and self._current_token()[0] != 'END':
                        if not self._parse_line():
                            break
                        if self.program_terminated:
                            break
                except ProgramEnd:
                    pass
            else:
                print(f"Runtime Error: {e}", file=sys.stderr)

    def _parse_on_error_statement(self):
        self._expect('ON ERROR GOTO')
        target = self._current_token()
        if target[0] == 'NUMBER' and target[1] == '0':
            self._next_token()
            self.error_handler_label = None
        elif target[0] == 'ID':
            label_name = target[1]
            self._next_token()
            if label_name not in self.labels:
                self._error(f"Label '{label_name}' not found for ON ERROR GOTO.")
            self.error_handler_label = label_name
        else:
            self._error("Expected label name or 0 after ON ERROR GOTO.")
    
    def _parse_resume_statement(self):
        self._expect('RESUME')
        #print(f"DEBUG: In _parse_resume_statement")
        #print(f"DEBUG: error_resume_index = {self.error_resume_index}")
        #print(f"DEBUG: in_error_handler = {self.in_error_handler}")
        
        if self._current_token() and self._current_token()[0] == 'NEXT':
            self._next_token()
            if not self.in_error_handler:
                self._error("RESUME NEXT without an active error.")
            if self.error_resume_index is None:
                self._error("Cannot RESUME; program location lost.")
            
            #print(f"DEBUG: Resuming at token index {self.error_resume_index}")
            #print(f"DEBUG: Token at resume index: {self.tokens[self.error_resume_index] if self.error_resume_index < len(self.tokens) else 'END'}")
            
            self.token_index = self.error_resume_index
            self.in_error_handler = False
        elif self._current_token() and self._current_token()[0] == 'ID':
            # Resume at a specific label
            label_name = self._current_token()[1]
            self._next_token()
            
            if not self.in_error_handler:
                self._error("RESUME without an active error.")
            if label_name not in self.labels:
                self._error(f"Label '{label_name}' not found for RESUME.")
            
            self.token_index = self.labels[label_name]
            self.in_error_handler = False
        else:
            self._error("Expected NEXT after RESUME.")
            
    def _parse_condition(self): return self._parse_or_condition()
    def _parse_or_condition(self):
        left = self._parse_and_condition()
        while self._current_token() and self._current_token()[0] == 'OR':
            self._next_token(); right = self._parse_and_condition(); left = (-1.0 if left != 0 or right != 0 else 0.0)
        return left
    def _parse_and_condition(self):
        left = self._parse_comparison()
        while self._current_token() and self._current_token()[0] == 'AND':
            self._next_token(); right = self._parse_comparison(); left = (-1.0 if left != 0 and right != 0 else 0.0)
        return left

    def _parse_comparison(self):
        token = self._current_token()
        if self._current_token() and self._current_token()[0] == 'NOT':
            self._next_token(); result = self._parse_comparison(); return -1.0 if result == 0 else 0.0
        if self._current_token() and self._current_token()[0] == 'EXISTS':
            self._next_token() # Consume EXISTS
            sql_query = self._extract_sql_from_parens()
            results = self._execute_sql(sql_query, is_query=True)
            # EXISTS is true if the query returns one or more rows.
            return -1.0 if results else 0.0
        left = self._parse_expression()
        token = self._current_token()
        if token and token[0] in ['RELOP', 'ASSIGN']:
            op_token = token; self._next_token(); op = op_token[1]; right = self._parse_expression()
            if op == '=': return -1.0 if left == right else 0.0
            if op == '<>': return -1.0 if left != right else 0.0
            if op == '<': return -1.0 if left < right else 0.0
            if op == '>': return -1.0 if left > right else 0.0
            if op == '<=': return -1.0 if left <= right else 0.0
            if op == '>=': return -1.0 if left >= right else 0.0
            self._error(f"Unknown relational operator: {op}")
        else:
            if token and token[0] == 'RPAREN': return left
            return -1.0 if left != 0 else 0.0

    def _parse_set_statement(self):
        self._expect('SET')
        token = self._current_token()
        if token[0] == 'ID' and token[1].upper() == 'SQL_FATAL_ERRORS':
            self._next_token(); setting_token = self._current_token()
            if not setting_token or setting_token[0] != 'ID' or setting_token[1] not in ['ON', 'OFF']:
                self._error("Expected ON or OFF after SET SQL_FATAL_ERRORS")
            self.sql_fatal_errors = (setting_token[1] == 'ON'); self._next_token()
        elif token[0] == 'ID' and token[1].upper() == 'HASH_KEYS':
            self._next_token()
            mode_token = self._current_token()
            if not mode_token or mode_token[0] != 'ID' or mode_token[1] not in ['PRESERVE_CASE', 'IGNORE_CASE']:
                self._error("Expected PRESERVE_CASE or IGNORE_CASE after SET HASH_KEYS")
            self.hash_keys_mode = mode_token[1]
            self._next_token()
            #print(f"DEBUG: Hash key mode set to {self.hash_keys_mode}", file=sys.stderr)
        elif token[0] == 'OUTPUT':
            self._next_token()
            token = self._current_token()
            
            # Check if the next token is FORMAT (shorthand syntax)
            if token and token[0] == 'ID' and token[1].upper() == 'FORMAT':
                # Default to CONSOLE when FORMAT is specified without destination
                g_output_config.mode = "CONSOLE"
                # Don't consume the FORMAT token yet - let it fall through to FORMAT handling below
            elif not token or token[0] not in ['ID']:
                g_output_config.mode = "CONSOLE"
            elif token[0] == 'ID':
                mode_value = token[1].upper()
                if mode_value == 'CONSOLE': 
                    self._next_token()
                    g_output_config.mode = "CONSOLE"
                elif mode_value == 'FILE':
                    self._next_token()
                    filename = self._parse_expression()
                    g_output_config.mode, g_output_config.file_path = "FILE", str(filename)
                elif mode_value == 'OFF': 
                    self._next_token()
                    g_output_config.mode = "OFF"
                else:
                    self._error(f"Unknown output mode: {token[1]}")
            
            # Handle FORMAT clause (works for both explicit and shorthand syntax)
            token = self._current_token()
            if token and token[0] == 'ID' and token[1].upper() == 'FORMAT':
                self._next_token()
                format_token = self._current_token()
                if format_token and format_token[0] in ['ID', 'CSV', 'JSON', 'JSONL', 'XML', 'HTML', 'FIXED']:
                    output_format = format_token[1].upper()
                    if output_format in ["TEXT", "CSV", "JSON", "JSONL", 'XML', "HTML", "FIXED"]: 
                        g_output_config.format = output_format
                        self._next_token()
                    else: 
                        self._error(f"Unknown format type '{output_format}'")
                else: 
                    self._error("Missing or invalid format type after FORMAT")

    def _handle_output(self, results, column_names):
        if g_output_config.mode == "CONSOLE":
            writer_function = getattr(self, f"_write_as_{g_output_config.format.lower()}"); writer_function(results, column_names, sys.stdout)
        elif g_output_config.mode == "FILE":
            try:
                with open(g_output_config.file_path, "w", encoding="utf-8", newline='') as f:
                    writer_function = getattr(self, f"_write_as_{g_output_config.format.lower()}"); writer_function(results, column_names, f)
                print(f"{len(results)} rows written to {g_output_config.file_path}")
            except IOError as e: self._error(f"Error writing to file: {e}")

    def _write_as_text(self, results, headers, stream):
        if not results: stream.write("(0 rows returned)\n"); return
        widths = {h: len(h) for h in headers}
        for row in results:
            for i, h in enumerate(headers):
                cell_content = str(row[i])
                max_line_len = max(len(line) for line in cell_content.splitlines()) if cell_content else 0
                widths[h] = max(widths[h], max_line_len)
        header_line = " | ".join([f"{h:<{widths[h]}}" for h in headers])
        separator = "-+-".join(["-" * widths[h] for h in headers])
        stream.write(f"+-{separator}-+\n| {header_line} |\n+-{separator}-+\n")
        for row in results:
            processed_cells = [[str(v)] if v is not None else ["NULL"] for v in row]
            cell_lines = [str(v).splitlines() if v is not None else ["NULL"] for v in row]
            for cell in cell_lines:
                if not cell: cell.append("")
            max_lines_in_row = max(len(lines) for lines in cell_lines) if any(cell_lines) else 1
            for i in range(max_lines_in_row):
                row_parts = [f"{(cell_lines[j][i] if i < len(cell_lines[j]) else ''):<{widths[h]}}" for j, h in enumerate(headers)]
                stream.write(f"| {' | '.join(row_parts)} |\n")
            stream.write(f"+-{separator}-+\n")
        stream.write(f"({len(results)} rows returned)\n")

    def _write_as_csv(self, results, headers, stream):
        csv_writer = csv.writer(stream); csv_writer.writerow(headers); csv_writer.writerows(results)
    
    def _write_as_json(self, results, headers, stream):
        json.dump([dict(zip(headers, row)) for row in results], stream, indent=2)
    
    def _write_as_jsonl(self, results, headers, stream):
        for row in results: stream.write(json.dumps(dict(zip(headers, row))) + "\n")
    
    def _write_as_xml(self, results, headers, stream):
        """Writes query results as XML."""
        stream.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        stream.write('<resultset>\n')
        
        for row in results:
            stream.write('  <record>\n')
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else ""
                safe_value = str(value if value is not None else "").replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                safe_header = header.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                stream.write(f'    <{safe_header}>{safe_value}</{safe_header}>\n')
            stream.write('  </record>\n')
        
        stream.write('</resultset>\n')   
    
    def _write_as_html(self, results, headers, stream):
        """Writes query results as a basic HTML table."""
        stream.write("<!DOCTYPE html>\n")
        stream.write("<html>\n<head>\n<title>Query Result</title>\n")
        stream.write("<style>\n")
        stream.write("  body { font-family: sans-serif; }\n")
        stream.write("  table { border-collapse: collapse; width: 80%; margin: 20px auto; }\n")
        stream.write("  th, td { border: 1px solid #cccccc; padding: 8px; text-align: left; }\n")
        stream.write("  thead { background-color: #f2f2f2; font-weight: bold; }\n")
        stream.write("  tr:nth-child(even) { background-color: #f9f9f9; }\n")
        stream.write("</style>\n</head>\n<body>\n")
        stream.write("<h1>Query Result</h1>\n")
        
        if not results:
            stream.write("<p>(0 rows returned)</p>\n")
        else:
            stream.write("<table>\n")
            stream.write("  <thead>\n    <tr>\n")
            for h in headers:
                safe_h = h.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                stream.write(f"      <th>{safe_h}</th>\n")
            stream.write("    </tr>\n  </thead>\n")
            
            stream.write("  <tbody>\n")
            for row in results:
                stream.write("    <tr>\n")
                for cell in row:
                    safe_cell = str(cell if cell is not None else "").replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    stream.write(f"      <td>{safe_cell}</td>\n")
                stream.write("    </tr>\n")
            stream.write("  </tbody>\n")
            stream.write("</table>\n")
            stream.write(f"<p style='text-align: center; font-style: italic;'>({len(results)} rows returned)</p>\n")

        stream.write("</body>\n</html>\n")
        
    def _write_as_fixed(self, results, headers, stream):
        """Writes query results as a fixed-width text file without headers."""
        if not results:
            return

        # Step 1: Calculate the maximum width needed for each column
        widths = [len(h) for h in headers]
        
        for row in results:
            for i, cell in enumerate(row):
                if i < len(widths):
                    # Sanitize newlines before calculating width
                    value = str(cell if cell is not None else "")
                    sanitized_value = " ".join(value.splitlines())
                    cell_width = len(sanitized_value)
                    if cell_width > widths[i]:
                        widths[i] = cell_width
        
        # Step 2: Write the data rows, padded to the calculated widths
        for row in results:
            line_parts = []
            for i, cell in enumerate(row):
                 if i < len(widths):
                    value = str(cell if cell is not None else "")
                    # Replace any newlines with a single space
                    sanitized_value = " ".join(value.splitlines())
                    padded_value = sanitized_value.ljust(widths[i])
                    line_parts.append(padded_value)
            
            stream.write("".join(line_parts) + "\n")
            
    def _parse_if_statement(self):
        start_if_index = self.token_index
        self._expect('IF')
        
        condition_result = self._parse_condition() != 0
        self._expect('THEN')

        # --- Handle single-line IF THEN... ELSE ... ---
        is_single_line = self._current_token() and self._current_token()[0] != 'NEWLINE'
        if is_single_line:
            if condition_result:
                # Condition is true, so parse the THEN part
                self._parse_statement()
                # After parsing, skip the ELSE part if it exists
                if self._current_token() and self._current_token()[0] == 'ELSE':
                    while self._current_token() and self._current_token()[0] not in ['NEWLINE', 'COLON']:
                        self._next_token()
            else:
                # Condition is false, so skip the THEN part
                while self._current_token() and self._current_token()[0] not in ['NEWLINE', 'ELSE']:
                    self._next_token()
                # If there's an ELSE part, parse it
                if self._current_token() and self._current_token()[0] == 'ELSE':
                    self._next_token()
                    self._parse_statement()
            return

        # --- Handle multi-line IF...END IF block ---
        self._expect('NEWLINE')
        
        jump_locations = self.jump_map.get(start_if_index)
        if not jump_locations or jump_locations['endif'] is None:
            self._error("Mismatched multi-line IF statement; no corresponding END IF found.")

        endif_index = jump_locations['endif']
        
        try:
            if condition_result:
                # IF condition is true, execute its block and then jump to END IF
                stop_at = jump_locations['elseifs'][0] if jump_locations['elseifs'] else \
                          (jump_locations['else'] if jump_locations['else'] is not None else endif_index)
                
                while self.token_index < stop_at:
                    if self.program_terminated: return
                    self._parse_line()
                
                self.token_index = endif_index

            else:
                # IF condition is false, find the first true ELSEIF or the ELSE block
                found_true_block = False

                # Check ELSEIF blocks
                for i, elseif_index in enumerate(jump_locations['elseifs']):
                    self.token_index = elseif_index
                    self._expect('ELSEIF')
                    elseif_condition = self._parse_condition() != 0
                    self._expect('THEN')
                    self._expect('NEWLINE')
                    
                    if elseif_condition:
                        found_true_block = True
                        # This ELSEIF is true, execute its block
                        next_stop_at = jump_locations['elseifs'][i+1] if i + 1 < len(jump_locations['elseifs']) else \
                                       (jump_locations['else'] if jump_locations['else'] is not None else endif_index)

                        while self.token_index < next_stop_at:
                            if self.program_terminated: return
                            self._parse_line()
                        
                        # After executing, jump to the end
                        self.token_index = endif_index
                        break # Exit the loop over ELSEIFs
                
                # If no ELSEIF was true, check for an ELSE block
                if not found_true_block:
                    if jump_locations['else'] is not None:
                        self.token_index = jump_locations['else']
                        self._expect('ELSE')
                        if self._current_token()[0] == 'NEWLINE': self._next_token()
                        
                        while self.token_index < endif_index:
                             if self.program_terminated: return
                             self._parse_line()
                    else:
                        # No true conditions and no ELSE block, so just jump to END IF
                        self.token_index = endif_index

            # Move past the END IF token
            if self.token_index < len(self.tokens) and self.tokens[self.token_index][0] == 'END IF':
                 self._expect('END IF')

        except LoopExit as e:
            # If an EXIT FOR/DO is hit, jump past the whole IF structure
            self.token_index = endif_index + 1 if endif_index is not None else len(self.tokens)
            raise e


    def _format_output_value(self, value):
        if isinstance(value, (int, float)) and value >= 0:
            return " " + (str(int(value)) if isinstance(value, float) and value.is_integer() else str(value))
        if isinstance(value, float) and value.is_integer(): return str(int(value))
        return str(value)
        
    def _parse_date_string(self, date_str):
        date_str = date_str.replace('-', '')
        if len(date_str) == 8 and date_str.isdigit(): return datetime.strptime(date_str, '%Y%m%d').date()
        raise ValueError(f"Invalid date format: {date_str}")
        
    def _python_to_basic_data(self, data):
        if isinstance(data, dict): 
            if self.hash_keys_mode == 'IGNORE_CASE':
                return {str(k).upper(): self._python_to_basic_data(v) for k, v in data.items()}
            else:  # PRESERVE_CASE
                 return {str(k): self._python_to_basic_data(v) for k, v in data.items()}
        if isinstance(data, list): 
            return [self._python_to_basic_data(item) for item in data]
        if data is None: return ""
        if isinstance(data, bool): return -1.0 if data else 0.0
        return data
        
    def _basic_to_json_serializable(self, data):
        if isinstance(data, dict): return {k: self._basic_to_json_serializable(v) for k, v in data.items()}
        if isinstance(data, list): return [self._basic_to_json_serializable(item) for item in data]
        if isinstance(data, float) and data.is_integer(): return int(data)
        return data
        
    def _normalize_hash_key(self, key):
        """Normalize hash key based on current hash_keys_mode setting."""
        key_str = str(key)
        if isinstance(key, float) and key.is_integer():
            key_str = str(int(key))  # "1" not "1.0"
        
        if self.hash_keys_mode == 'IGNORE_CASE':
            return key_str.upper()
        else:  # PRESERVE_CASE
            return key_str
        
    def _to_camel_case(self, s):
        """Converts an UPPER_SNAKE_CASE string to camelCase."""
        components = s.lower().split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
        
    def _execute_function(self, name, args):
        name = name.upper()
        if name == 'RND':
            if not args: return random.random()
            if len(args) == 1: max_val = int(args[0]); return float(random.randint(1, max_val)) if max_val >= 1 else self._error("RND arg must be >= 1")
            self._error("RND takes 0 or 1 arguments.")
        elif name == 'UBOUND':
            if len(args) != 1 or not isinstance(args[0], list): self._error("UBOUND requires one array argument.")
            return float(len(args[0]) - 1 if args[0] else -1)
        elif name == 'FIND':
            if len(args) != 2: self._error("FIND requires 2 arguments.")
            if not isinstance(args[0], list): self._error("First argument to FIND must be an array.")
            try:
                return float(args[0].index(args[1]))
            except ValueError:
                return -1.0  # Not found

        elif name == 'ARRAY_SIZE':
            if len(args) != 1: self._error("ARRAY_SIZE requires 1 argument.")
            if not isinstance(args[0], list): self._error("ARRAY_SIZE requires an array argument.")
            return float(len(args[0]))

        elif name == 'ARRAY_JOIN':
            if not (2 <= len(args) <= 3): self._error("ARRAY_JOIN requires 2 or 3 arguments.")
            if not isinstance(args[0], list): self._error("First argument to ARRAY_JOIN must be an array.")
            delimiter = str(args[1]) if len(args) >= 2 else ","
            return delimiter.join(str(item) for item in args[0])
        elif name == 'JSON_SERIALIZE$':
            if not (1 <= len(args) <= 5):
                self._error("JSON_SERIALIZE$ requires 1 to 5 arguments: data, [indent], [sort_option$], [case_option$], ...")

            data = args[0]
            if not isinstance(data, (dict, list)):
                self._error("First argument to JSON_SERIALIZE$ must be a HASH or ARRAY.")

            indent_val, sort_keys, lowercase_keys, camelcase_keys = 0, False, False, False
            
            # Process optional arguments
            string_options = [str(arg).upper() for arg in args[1:] if isinstance(arg, str)]
            if "SORT_KEYS" in string_options: sort_keys = True
            if "LOWERCASE_KEYS" in string_options: lowercase_keys = True
            if "CAMELCASE_KEYS" in string_options: camelcase_keys = True
            
            numeric_args = [arg for arg in args[1:] if isinstance(arg, (int, float))]
            if numeric_args: indent_val = numeric_args[0]
                
            indent = int(indent_val) if indent_val > 0 else None

            serializable_data = self._basic_to_json_serializable(data)
            
            # --- NEW: Automatic filtering logic ---
            if isinstance(serializable_data, dict):
                keys = list(serializable_data.keys())
                has_numeric_keys = any(k.isdigit() for k in keys)
                has_non_numeric_keys = any(not k.isdigit() for k in keys)

                if has_numeric_keys and has_non_numeric_keys:
                    serializable_data = {k: v for k, v in serializable_data.items() if not k.isdigit()}
            # --- End of new logic ---

            if camelcase_keys and isinstance(serializable_data, dict):
                serializable_data = {self._to_camel_case(k): v for k, v in serializable_data.items()}
            elif lowercase_keys and isinstance(serializable_data, dict):
                serializable_data = {k.lower(): v for k, v in serializable_data.items()}

            return json.dumps(serializable_data, indent=indent, sort_keys=sort_keys)
        # --- HASH FUNCTIONS ---
        elif name == 'HASH_EXISTS':
            if len(args) != 2 or not isinstance(args[0], dict): 
                self._error("HASH_EXISTS requires hash_var, key$.")
            lookup_key = self._normalize_hash_key(args[1])
            return -1.0 if lookup_key in args[0] else 0.0
        elif name == 'HASH_JOIN':
            if len(args) < 2:
                self._error("HASH_JOIN requires at least two HASH arguments.")
            
            new_hash = {}
            for h in args:
                if not isinstance(h, dict):
                    self._error("All arguments to HASH_JOIN must be HASH variables.")
                new_hash.update(h)
            return new_hash
            if len(args) < 2:
                self._error("HASH_JOIN requires at least two HASH arguments.")
            
            new_hash = {}
            for h in args:
                if not isinstance(h, dict):
                    self._error("All arguments to HASH_JOIN must be HASH variables.")
                new_hash.update(h)
            return new_hash       
        elif name == 'HASH_KEYS':
            if len(args) != 1 or not isinstance(args[0], dict):
                self._error("HASH_KEYS requires one HASH argument.")
            return list(args[0].keys())

        elif name == 'HASH_VALUES':
            if len(args) != 1 or not isinstance(args[0], dict):
                self._error("HASH_VALUES requires one HASH argument.")
            return list(args[0].values())
        
        elif name == 'HASH_RENAME':
            if len(args) != 3 or not isinstance(args[0], dict):
                self._error("HASH_RENAME requires hash_var, old_key$, new_key$.")
            
            the_hash, old_key, new_key = args[0], args[1], args[2]
            
            # Normalize keys according to the current mode (IGNORE_CASE/PRESERVE_CASE)
            normalized_old = self._normalize_hash_key(old_key)
            normalized_new = self._normalize_hash_key(new_key)

            if normalized_old in the_hash:
                # Prevent overwriting an existing key with the new name
                if normalized_new in the_hash and normalized_old != normalized_new:
                    self._error(f"Cannot rename key: new key '{new_key}' already exists.")
                
                the_hash[normalized_new] = the_hash.pop(normalized_old)
                return -1.0 # BASIC true for success
            
            return 0.0 # BASIC false if old key was not found
        elif name == 'HASH_DELETE':
            # Note that this a a FUNCTION, i.e. n = hash_delete(h,"city")
            if len(args) != 2 or not isinstance(args[0], dict): 
                self._error("HASH_DELETE requires hash_var, key$.")
            lookup_key = self._normalize_hash_key(args[1])
            if lookup_key in args[0]: 
                del args[0][lookup_key]
                return 0
            return 0
        elif name == 'HASH_COUNT':
            if len(args) != 1 or not isinstance(args[0], dict): 
                self._error("HASH_COUNT requires a hash argument.")
            return float(len(args[0]))
        elif name == 'IS_HASH': 
            return -1.0 if isinstance(args[0], dict) else 0.0
        elif name == 'IS_ARRAY': 
            return -1.0 if isinstance(args[0], list) else 0.0
        elif name == 'COMMAND$':
            if len(args) != 1: 
                self._error("COMMAND$ requires 1 argument.")
            idx = int(args[0])
            return self.command_args[idx-1] if 1 <= idx <= len(self.command_args) else ""
        elif name == 'ENVIRON$':
            if len(args) != 1:
                self._error("ENVIRON$ requires 1 argument.")
            var_name = str(args[0])
            return os.environ.get(var_name, "")
        elif name == 'CURDIR$':
            if args: 
                self._error("CURDIR$ takes no arguments."); 
            return os.getcwd()
        elif name == 'FREEFILE':
            if args:
                self._error("FREEFILE function takes no arguments.")
            # This initialization must happen outside the 'if args:' check.
            file_num = 1
            while file_num in self.file_handles:
                file_num += 1
            return float(file_num)
        elif name == 'EOF':
            if len(args) < 1: return 0
            file_num = int(args[0])
            handle_info = self.file_handles.get(file_num)
            if not handle_info: 
                self._error(f"File #{file_num} is not open.")
            pos = handle_info['handle'].tell()
            is_eof = handle_info['handle'].read(1) == ''
            handle_info['handle'].seek(pos)
            return -1.0 if is_eof else 0.0
        elif name == 'FILE_EXISTS':
            if len(args) != 1: self._error("FILE_EXISTS requires 1 argument.")
            return -1.0 if os.path.exists(os.path.expanduser(str(args[0]))) else 0.0
        elif name == 'FILESIZE':
            if len(args) != 1: self._error("FILESIZE requires 1 argument.")
            filename = str(args[0])
            try:
                return float(os.path.getsize(os.path.expanduser(filename)))
            except (FileNotFoundError, OSError):
                return -1.0  # Return -1 if file doesn't exist or can't be accessed

        elif name == 'FILETIME':
            if len(args) != 1: self._error("FILETIME requires 1 argument.")
            filename = str(args[0])
            try:
                mtime = os.path.getmtime(os.path.expanduser(filename))
                return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            except (FileNotFoundError, OSError):
                return ""  # Return empty string if file doesn't exist

        elif name == 'FILEATTR':
            if len(args) != 1: self._error("FILEATTR requires 1 argument.")
            filename = str(args[0])
            try:
                filepath = os.path.expanduser(filename)
                stat_info = os.stat(filepath)
                attr_bits = 0
                if stat_info.st_mode & 0o200 == 0: attr_bits |= 1  # Read-only
                if os.name == 'nt':  # Windows
                    import stat
                    if stat_info.st_file_attributes & 2: attr_bits |= 2  # Hidden
                    if stat_info.st_file_attributes & 4: attr_bits |= 4  # System
                if os.path.isdir(filepath): attr_bits |= 16  # Directory
                return float(attr_bits)
            except (FileNotFoundError, OSError, AttributeError):
                return 0.0

        elif name == 'DISKSPACE':
            if len(args) != 1: self._error("DISKSPACE requires 1 argument.")
            path = str(args[0])
            try:
                if os.name == 'nt':  # Windows
                    import shutil
                    total, used, free = shutil.disk_usage(path)
                    return float(free)
                else:  # Unix-like
                    statvfs = os.statvfs(path)
                    return float(statvfs.f_frsize * statvfs.f_bavail)
            except (FileNotFoundError, OSError):
                return -1.0
        elif name == 'DATE$': return datetime.now().strftime('%Y-%m-%d')
        elif name == 'TIME$': return datetime.now().strftime('%H:%M:%S')
        elif name == 'DATEADD': return (self._parse_date_string(args[0]) + timedelta(days=int(args[1]))).strftime('%Y-%m-%d')
        elif name == 'DATEDIFF': return float((self._parse_date_string(args[0]) - self._parse_date_string(args[1])).days)
        elif name == 'YEAR': return float(self._parse_date_string(args[0]).year)
        elif name == 'MONTH': return float(self._parse_date_string(args[0]).month)
        elif name == 'DAY': return float(self._parse_date_string(args[0]).day)
        elif name == 'WEEKDAY': return float((self._parse_date_string(args[0]).weekday() + 1) % 7 + 1)
        elif name == 'FORMATDATE$':
            date_obj, format_mask = self._parse_date_string(args[0]), str(args[1]).upper()
            format_map = {'YYYY': '%Y', 'YY': '%y', 'MM': '%m', 'DD': '%d', 'HH': '%H', 'MI': '%M', 'SS': '%S'}
            py_format_str = format_mask
            for b, p in format_map.items(): py_format_str = py_format_str.replace(b, p)
            return date_obj.strftime(py_format_str)
        elif name == 'LEN': return float(len(str(args[0])))
        elif name == 'SPLIT':
            if not (2 <= len(args) <= 3): self._error("SPLIT requires 2 or 3 arguments.")
            source_str, delimiter_str = str(args[0]), str(args[1])
            if not delimiter_str: return list(source_str)
            if len(args) == 3: limit = int(args[2]); return source_str.split(delimiter_str, limit - 1) if limit > 0 else self._error("Limit must be > 0")
            return source_str.split(delimiter_str)
        elif name == 'LEFT$': return str(args[0])[:int(args[1])]
        elif name == 'RIGHT$': return str(args[0])[-int(args[1]):]
        elif name == 'MID$': s, st = str(args[0]), int(args[1])-1; ln = int(args[2]) if len(args)==3 else len(s); return s[st:st+ln]
        elif name == 'UCASE$': return str(args[0]).upper()
        elif name == 'LCASE$': return str(args[0]).lower()
        elif name == 'INSTR':
            if not (2 <= len(args) <= 3): self._error("INSTR requires 2 or 3 arguments.")
            if len(args) == 2:
                haystack, needle = str(args[0]), str(args[1])
                pos = haystack.find(needle)
                return float(pos + 1) if pos != -1 else 0.0
            else:  # 3 arguments: INSTR(start, haystack, needle)
                start, haystack, needle = int(args[0]) - 1, str(args[1]), str(args[2])
                pos = haystack.find(needle, max(0, start))
                return float(pos + 1) if pos != -1 else 0.0
        elif name == 'REVERSE$': 
            return str(args[0])[::-1]

        elif name == 'REPEAT$': 
            if len(args) != 2: self._error("REPEAT$ requires 2 arguments.")
            return str(args[0]) * int(args[1])

        elif name == 'PADLEFT$':
            if len(args) != 3: self._error("PADLEFT$ requires 3 arguments.")
            text, length, pad_char = str(args[0]), int(args[1]), str(args[2])
            if len(pad_char) == 0: pad_char = ' '
            return text.rjust(length, pad_char[0])

        elif name == 'PADRIGHT$':
            if len(args) != 3: self._error("PADRIGHT$ requires 3 arguments.")
            text, length, pad_char = str(args[0]), int(args[1]), str(args[2])
            if len(pad_char) == 0: pad_char = ' '
            return text.ljust(length, pad_char[0])

        elif name == 'STARTSWITH':
            if len(args) != 2: self._error("STARTSWITH requires 2 arguments.")
            text, prefix = str(args[0]), str(args[1])
            return -1.0 if text.startswith(prefix) else 0.0

        elif name == 'ENDSWITH':
            if len(args) != 2: self._error("ENDSWITH requires 2 arguments.")
            text, suffix = str(args[0]), str(args[1])
            return -1.0 if text.endswith(suffix) else 0.0

        elif name == 'CONTAINS':
            if len(args) != 2: self._error("CONTAINS requires 2 arguments.")
            text, substring = str(args[0]), str(args[1])
            return -1.0 if substring in text else 0.0

        elif name == 'PROPER$':
            if len(args) != 1: self._error("PROPER$ requires 1 argument.")
            return str(args[0]).title()

        elif name == 'ISALPHA':
            if len(args) != 1: self._error("ISALPHA requires 1 argument.")
            return -1.0 if str(args[0]).isalpha() else 0.0

        elif name == 'ISDIGIT':
            if len(args) != 1: self._error("ISDIGIT requires 1 argument.")
            return -1.0 if str(args[0]).isdigit() else 0.0

        elif name == 'ISALNUM':
            if len(args) != 1: self._error("ISALNUM requires 1 argument.")
            return -1.0 if str(args[0]).isalnum() else 0.0
        elif name == 'CHR$':
            if len(args) != 1: self._error("CHR$ requires one numeric argument.")
            return chr(int(args[0]))
        elif name == 'ASC':
            if len(args) != 1 or not isinstance(args[0], str) or len(args[0]) == 0:
                self._error("ASC requires one non-empty string argument.")
            return float(ord(args[0][0]))
        elif name == 'REPLACE$':
            if not (3 <= len(args) <= 5): self._error("REPLACE$ requires 3 to 5 arguments.")
            source_str, old_str, new_str = str(args[0]), str(args[1]), str(args[2])
            count = int(args[3]) if len(args) >= 4 else -1
            ignore_case = (args[4] != 0) if len(args) == 5 else False
            if ignore_case: return re.sub(re.escape(old_str), new_str, source_str, count=count if count != -1 else 0, flags=re.IGNORECASE)
            return source_str.replace(old_str, new_str, count)
        elif name == 'HEX$': return hex(int(args[0]))[2:]
        elif name == 'OCT$': return oct(int(args[0]))[2:]
        elif name == 'SPACE$': return ' ' * int(args[0])
        elif name == 'TRIM$': return str(args[0]).strip()
        elif name == 'LTRIM$': return str(args[0]).lstrip()
        elif name == 'RTRIM$': return str(args[0]).rstrip()
        elif name == 'STR$': return self._format_output_value(args[0])
        elif name == 'VAL': return float(args[0])
        elif name == 'INT': return float(math.floor(args[0]))
        elif name == 'FIX': return float(math.trunc(args[0]))
        elif name == 'ATN': return math.atan(args[0])
        elif name == 'COS': return math.cos(args[0])
        elif name == 'SIN': return math.sin(args[0])
        elif name == 'TAN': return math.tan(args[0])
        elif name == 'EXP': return math.exp(args[0])
        elif name == 'LOG': return math.log(args[0])
        elif name == 'SGN': n = args[0]; return 1.0 if n > 0 else -1.0 if n < 0 else 0.0
        elif name == 'SQR': return math.sqrt(args[0])
        elif name == 'MOD':
            if len(args) != 2: self._error("MOD requires 2 arguments.")
            return float(args[0] % args[1])

        elif name == 'ROUND':
            if not (1 <= len(args) <= 2): self._error("ROUND requires 1 or 2 arguments.")
            if len(args) == 1: return float(round(args[0]))
            return float(round(args[0], int(args[1])))

        elif name == 'CEIL':
            if len(args) != 1: self._error("CEIL requires 1 argument.")
            return float(math.ceil(args[0]))

        elif name == 'FLOOR':
            if len(args) != 1: self._error("FLOOR requires 1 argument.")
            return float(math.floor(args[0]))

        elif name == 'ABS':
            if len(args) != 1: self._error("ABS requires 1 argument.")
            return float(abs(args[0]))

        elif name == 'MIN':
            if len(args) < 2: self._error("MIN requires at least 2 arguments.")
            return float(min(args))

        elif name == 'MAX':
            if len(args) < 2: self._error("MAX requires at least 2 arguments.")
            return float(max(args))

        elif name == 'POWER':
            if len(args) != 2: self._error("POWER requires 2 arguments.")
            return float(pow(args[0], args[1]))

        elif name == 'DEGREES':
            if len(args) != 1: self._error("DEGREES requires 1 argument.")
            return float(math.degrees(args[0]))

        elif name == 'RADIANS':
            if len(args) != 1: self._error("RADIANS requires 1 argument.")
            return float(math.radians(args[0]))

        elif name == 'ATAN2':
            if len(args) != 2: self._error("ATAN2 requires 2 arguments.")
            return float(math.atan2(args[0], args[1]))
        else: self._error(f"Unknown function: {name}")
        
    def _parse_factor(self):
        token = self._current_token()
        if token[0] == 'OP' and token[1] in '+-':
            op = token[1]
            self._next_token()
            res = self._parse_factor() 
            return -res if op == '-' else res
        if token[0] == 'NUMBER': 
            self._next_token(); 
            return float(token[1])
        elif token[0] in ('STRING', 'BACKTICK_STRING'):
            self._next_token(); raw_value = token[1]
            if raw_value.startswith('"'): 
                return raw_value[1:-1].replace('""', '"')
            return raw_value[1:-1]
        elif token[0] == 'LPAREN':
            if self._peek_token() and self._peek_token()[0] == 'SQL_STRING':
                results = self._execute_sql(self._extract_sql_from_parens(), is_query=True)
                if len(results) != 1 or len(results[0]) != 1:
                    self._error("Scalar subquery must return one row/column.")
                return results[0][0]
            else: 
                self._next_token()
                res = self._parse_condition()
                self._expect('RPAREN')
                return res
        elif token[0] == 'SQL_STRING':
            self._next_token()
            results = self._execute_sql(token[1], is_query=True)
            if len(results) == 1 and len(results[0]) == 1:
                return results[0][0]
            else:
                self._error("A subquery used as a value must return exactly one row and one column.")
            return results[0][0]
        elif token[0] == 'ID':
            var_name = token[1]
            
            # Handle case-insensitive BASIC variable lookup
            actual_var_name = var_name
            if var_name not in self.variables:
                # Try to find existing variable with different case
                for existing_var in self.variables:
                    if existing_var.upper() == var_name.upper():
                        actual_var_name = existing_var
                        break
                else:
                    # Variable doesn't exist, create with uppercase name
                    actual_var_name = var_name.upper()
                    if not (self._peek_token() and self._peek_token()[0] == 'LPAREN'):
                        self.variables[actual_var_name] = "" if var_name.endswith('$') else 0.0
            
            var_name = actual_var_name
            
            if var_name.upper() in ['DATE$', 'TIME$', 'FREEFILE', 'RND', 'CURDIR$'] and not (self._peek_token() and self._peek_token()[0] == 'LPAREN'):
                self._next_token(); 
                return self._execute_function(var_name, [])
            
            self._next_token()
            
            # Additional case-insensitive lookup for variables that might exist with different case
            if var_name not in self.variables:
                upper_var_name = var_name.upper()
                if upper_var_name in self.variables:
                    var_name = upper_var_name
            
            current_value = self.variables.get(var_name)
            
            while self._current_token():
                token = self._current_token()
                if token[0] == 'LPAREN':
                    self._next_token()
                    if not isinstance(current_value, (list, dict)):
                        args = [];
                        if self._current_token()[0] != 'RPAREN':
                            while True:
                                args.append(self._parse_expression())
                                if self._current_token()[0] == 'RPAREN': break
                                self._expect('COMMA')
                        self._expect('RPAREN')
                        current_value = self._execute_function(var_name, args)
                        continue
                    if self._current_token()[0] == 'RPAREN': self._expect('RPAREN'); break
                    key_or_index = self._parse_expression(); self._expect('RPAREN')
                    if isinstance(current_value, list):
                        index = int(key_or_index)
                        if not 0 <= index < len(current_value): self._error("Array index out of bounds.")
                        current_value = current_value[index]
                    elif isinstance(current_value, dict):
                        original_key = str(key_or_index)
                        normalized_key = self._normalize_hash_key(key_or_index)
                        # Use the original key expression to determine type, not the variable name
                        default_val = "" if original_key.endswith('$') else 0.0
                        current_value = current_value.get(normalized_key, default_val)
                    continue
                elif token[0] == 'DOT':
                    if not isinstance(current_value, dict): self._error("Dot notation only for HASH.")
                    self._next_token()
                    key_token = self._current_token()
                    if not key_token:
                        self._error("Expected a key name after '.'")

                    # This set defines keywords that can be treated as keys.
                    PERMISSIBLE_KEYWORDS_AS_KEYS = {
                        'ACTION', 'BUTTON', 'DISPLAY', 'FIELD', 'HEADING', 'LABEL', 'MATCHES', 
                        'MAXLENGTH', 'MESSAGE', 'MINLENGTH', 'MINVALUE', 'PATTERN', 'PLACEHOLDER', 
                        'READONLY', 'REQUIRED', 'SEPARATOR', 'SIZE', 'SOURCE', 'TEXTBLOCK', 
                        'TITLE', 'TYPE', 'HTML', 'XML', 'JSON', 'JSONL'
                    }

                    key_name = ""
                    # It first checks for a generic ID as before.
                    if key_token[0] == 'ID':
                        self._next_token() 
                        key_name = key_token[1]
                    # If not an ID, it checks if it's an acceptable keyword.
                    elif key_token[0] in PERMISSIBLE_KEYWORDS_AS_KEYS:
                        # Not sure why we cannot accept anything here that looks like a ID
                        self._next_token() 
                        key_name = key_token[1] 
                    # If neither, it's an error.
                    else:
                        self._error(f"Invalid key name '{key_token[1]}' after '.'")
                    
                    is_string_access = key_name.endswith('$')
                    base_key = key_name.rstrip('$')
                    
                    #print(f"DEBUG: Looking for key '{base_key}' in hash with keys: {list(current_value.keys())}", file=sys.stderr)
                    
                    # 1. Try exact match first (fastest)
                    if base_key in current_value:
                        current_value = current_value[base_key]
                        #print(f"DEBUG: Found exact match", file=sys.stderr)
                    else:
                        # 2. Fall back to case-insensitive search for dot notation forgiveness
                        found = False
                        for candidate_key in current_value.keys():
                            if candidate_key.lower() == base_key.lower():
                                current_value = current_value[candidate_key]
                                #print(f"DEBUG: Found case-insensitive match: '{candidate_key}'", file=sys.stderr)
                                found = True
                                break
                        
                        if not found:
                            current_value = "" if is_string_access else 0.0
                            #print(f"DEBUG: No match found, using default", file=sys.stderr)
                    continue
                else: 
                    break
            return current_value
        else:
            self._error(f"Unexpected token in factor: {token}")
            print("\n--- TOKEN DUMP IN LEXER ---")
            for token in self.tokens:
                print(token)
            print("--------------------\n")            

    def _parse_dump_statement(self):
        """
        Parse and execute a DUMP statement for debugging.
        
        Syntax:
        DUMP TOKENS
        DUMP VARIABLES
        DUMP LABELS
        DUMP JUMPS
        """
        self._expect('DUMP')
        
        if not self._current_token() or self._current_token()[0] not in ['ID']:
            self._error("DUMP requires a target: TOKENS, VARIABLES, LABELS, or JUMPS")
        
        target = self._current_token()[1].upper()
        self._next_token()
        
        if target == 'TOKENS':
            print("=== TOKEN DUMP ===")
            print(f"Current token index: {self.token_index}")
            print(f"Total tokens: {len(self.tokens)}")
            print()
            
            # Show tokens around current position
            start = 0   #  max(0, self.token_index - 5)
            end = len(self.tokens) # min(len(self.tokens), self.token_index + 10)
            
            for i in range(start, end):
                marker = " -> " if i == self.token_index else "    "
                if i < len(self.tokens):
                    token = self.tokens[i]
                    line, col = self.lexer.get_line_col(token[2])
                    print(f"{marker}[{i:3d}] {token[0]:15} '{token[1]}' (Line {line}, Col {col})")
                
        elif target == 'VARIABLES':
            print("=== VARIABLE DUMP ===")
            if not self.variables:
                print("No variables defined")
            else:
                for name, value in sorted(self.variables.items()):
                    var_type = type(value).__name__
                    if isinstance(value, str):
                        display_value = f'"{value}"'
                    elif isinstance(value, list):
                        display_value = f"ARRAY[{len(value)}]"
                    elif isinstance(value, dict):
                        display_value = f"HASH[{len(value)}]"
                    else:
                        display_value = str(value)
                    print(f"  {name:20} = {display_value:30} ({var_type})")
                    
        elif target == 'LABELS':
            print("=== LABEL DUMP ===")
            if not self.labels:
                print("No labels defined")
            else:
                for label, token_index in sorted(self.labels.items()):
                    if token_index < len(self.tokens):
                        token = self.tokens[token_index]
                        line, col = self.lexer.get_line_col(token[2])
                        print(f"  {label:20} -> Token[{token_index}] (Line {line}, Col {col})")
                    else:
                        print(f"  {label:20} -> Token[{token_index}] (INVALID)")
                        
        elif target == 'JUMPS':
            print("=== JUMP MAP DUMP ===")
            if not self.jump_map:
                print("No jump mappings defined")
            else:
                for start_index, mappings in sorted(self.jump_map.items()):
                    if start_index < len(self.tokens):
                        start_token = self.tokens[start_index]
                        line, col = self.lexer.get_line_col(start_token[2])
                        print(f"  {start_token[0]} at Token[{start_index}] (Line {line}):")
                        for key, value in mappings.items():
                            if value is not None:
                                if isinstance(value, list):
                                    print(f"    {key}: {value}")
                                else:
                                    print(f"    {key}: Token[{value}]")
                            else:
                                print(f"    {key}: None")
                        print()
        else:
            self._error(f"Unknown DUMP target: {target}. Use TOKENS, VARIABLES, LABELS, or JUMPS")
        
    def _parse_term(self):
        res = self._parse_factor()
        while self._current_token() and self._current_token()[0] == 'OP' and self._current_token()[1] in '*/':
            op = self._current_token()[1]
            self._next_token()
            right = self._parse_factor()
            try:
                if op == '*':
                    res *= right
                elif op == '/':
                    res /= right
            except ZeroDivisionError:
                raise RuntimeError("Division by zero")
            except Exception as e:
                raise RuntimeError(f"Arithmetic error: {e}")
        return res
        
    def _parse_expression(self):
        res = self._parse_term()
        while self._current_token() and self._current_token()[0] == 'OP' and self._current_token()[1] in '+-':
            op = self._current_token()[1]
            self._next_token()
            right = self._parse_term()
            if op == '+':
                res = str(res) + str(right) if isinstance(res, str) or isinstance(right, str) else res + right
            elif op == '-':
                if isinstance(res, str) or isinstance(right, str):
                    raise RuntimeError("Type mismatch: Cannot subtract strings")
                res -= right
        return res

    def _parse_line_input_statement(self):
        self._expect('LINE INPUT')
        self._expect('HASH_SYM')

        file_num = int(self._parse_expression())

        self._expect('COMMA')
        var_name = self._expect('ID')[1]
        line = self.file_handles[file_num]['handle'].readline()
        self.variables[var_name] = line.rstrip('\n\r')
        
    def _parse_open_statement(self):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('OPEN')
        filename = self._parse_expression()
        self._expect('FOR')
        mode_token = self._current_token()
        if not mode_token or mode_token[0] not in ['OUTPUT', 'INPUT', 'APPEND']: 
            self._error("Expected file mode")
        self._next_token(); mode_map = {'OUTPUT': 'w', 'INPUT': 'r', 'APPEND': 'a'}
        py_mode = mode_map[mode_token[1]]
        self._expect('AS'); self._expect('HASH_SYM')
        file_num = int(self._parse_expression())
        if file_num in self.file_handles:
            self._error(f"File #{file_num} is already open.")
        dialect_params = {}
        if self._current_token() and self._current_token()[0] == 'WITH':
            self._next_token()
            self._expect('OPTIONS')
            options_str = self._parse_expression()
            for part in options_str.split(): 
                key, value = part.split('=')
                dialect_params[key.strip()] = value.strip()
        try:
            #print("DEBUG","ABOUT TO OPEN FILE ",filename)
            handle = open(filename, py_mode, newline='', encoding="utf-8")
            self.file_handles[file_num] = {'handle': handle, 'dialect': dialect_params}
        except FileNotFoundError as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            #print("DEBUG OPEN FILENOTFOUND", self.variables['ERRMSG$'],e)
            #self._error(f"File not found: {filename}")
            raise e
        except Exception as e: 
            self.variables['ERR'], 
            self.variables['ERRMSG$'] = 1.0, str(e); 
            print("DEBUG OPEN EXCEPTION", e)
            self._error(f"Error opening file: {e}")
        
    def _parse_close_statement(self):
        self._expect('CLOSE')
        
        # Check if a specific file handle is provided (e.g., CLOSE #1)
        if self._current_token() and self._current_token()[0] == 'HASH_SYM':
            self._next_token() # Consume the '#'
            file_num = int(self._parse_expression())
            
            handle_info = self.file_handles.get(file_num)
            if handle_info:
                handle_info['handle'].close()
                del self.file_handles[file_num]
            else:
                # This makes the command more robust by not crashing on a closed handle.
                self._error(f"File #{file_num} is not open.")
        else:
            # If no file number is given, it's a bare CLOSE. Close all files.
            self._close_all_files()
 
    def _parse_copy_statement(self):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('ID')  # COPY
        source_filename = self._parse_expression()
        self._expect('AS')
        dest_filename = self._parse_expression()
        
        try:
            import shutil
            shutil.copy2(os.path.expanduser(str(source_filename)), 
                         os.path.expanduser(str(dest_filename)))
        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {source_filename}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"Error copying file: {e}")
        
    def _parse_read_file_statement(self):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('READ FILE') 
        filename = str(self._parse_expression()) 
        self._expect('INTO') 
        var_name = self._expect('ID')[1]
        if not var_name.endswith('$'): 
            self._error("Destination for READ FILE must be a string variable.")
        try:
            with open(filename, 'r', encoding='utf-8') as f: 
                self.variables[var_name] = f.read()
        except FileNotFoundError as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {filename}")
        except Exception as e: 
            self.variables['ERR'], 
            self.variables['ERRMSG$'] = 1.0, str(e); 
            self._error(f"Error reading file: {e}")
        
    def _parse_input_statement(self):
        self._expect('INPUT'); prompt = " "
        if self._current_token()[0] == 'STRING':
            prompt = self._current_token()[1][1:-1].replace('""', '"')
            self._next_token(); 
            self._expect('SEMICOLON')
        var_name = self._expect('ID')[1]
        user_input = input(prompt)
        if var_name.endswith('$'): self.variables[var_name] = user_input
        else: self.variables[var_name] = float(user_input)
        
    def _parse_print_statement(self):
        self._expect('PRINT')
        target = sys.stdout
        if self._current_token() and self._current_token()[0] == 'HASH_SYM':
            self._next_token()
            
            file_num = int(self._parse_expression())
            
            target = self.file_handles[file_num]['handle']
            self._expect('COMMA')
        if self._current_token() and self._current_token()[0] == 'USING':
            self._next_token()
            format_string = self._parse_expression()
            self._expect('SEMICOLON')
            values = []
            while self._current_token() and self._current_token()[0] not in ['NEWLINE', 'END']:
                values.append(self._parse_expression())
                if self._current_token() and self._current_token()[0] == 'COMMA': self._next_token()
                else: break
            formatted_output = Formatter.format(format_string, values)
            if target == sys.stdout: print(formatted_output)
            else: target.write(formatted_output + '\n')
            return
        parts = []
        suppress_nl = False
        if (self._current_token() is None or 
            self._current_token()[0] in ['NEWLINE', 'END'] or
            (self._current_token()[0] in ['PRINT', 'IF', 'FOR', 'WHILE', 'DIM', 'LET', 'GOSUB', 'RETURN'] and 
             self._current_token()[0] not in ['NEXT', 'WEND', 'END LOOP', 'LOOP'])):
            parts.append('\n')
        else:
            while self._current_token() and self._current_token()[0] not in ['NEWLINE', 'END']:
                value = self._parse_expression()
                if isinstance(value, dict): 
                    parts.append(json.dumps(self._basic_to_json_serializable(value), indent=2))
                elif isinstance(value, list): 
                    formatted_list_items = []
                    for item in value:
                        if isinstance(item, dict):
                            # If the item is a hash, format it as a JSON string.
                            formatted_list_items.append(json.dumps(self._basic_to_json_serializable(item)))
                        else:
                            # Otherwise, use the standard formatting.
                            formatted_list_items.append(self._format_output_value(item))
                    parts.append("[" + ", ".join(formatted_list_items) + "]")
                else: 
                    parts.append(self._format_output_value(value))
                token = self._current_token()
                if token and token[0] == 'COMMA':
                    self._next_token()
                    parts.append('\t')
                    suppress_nl = False
                elif token and token[0] == 'SEMICOLON':
                    self._next_token()
                    suppress_nl = True
                else:
                    suppress_nl = False
                    break
            if not suppress_nl: parts.append('\n')
        output = "".join(parts)
        if target == sys.stdout: print(output, end='')
        else: target.write(output)   
            
    def _parse_write_statement(self):
        self._expect('WRITE'); target_handle, dialect_params = None, {}
        if self._current_token() and self._current_token()[0] == 'HASH_SYM':
            self._next_token(); file_num = int(self._parse_expression()); self._expect('COMMA')
            handle_info = self.file_handles.get(file_num)
            if not handle_info: self._error(f"File #{file_num} not open.")
            target_handle, dialect_params = handle_info['handle'], handle_info['dialect']
        values = []
        if self._current_token() and self._current_token()[0] not in ['NEWLINE', 'END']:
            while True:
                values.append(self._parse_expression())
                if self._current_token() and self._current_token()[0] == 'COMMA': self._next_token()
                else: break
        if target_handle is None:
            output_buffer = io.StringIO(); csv_writer = csv.writer(output_buffer, **dialect_params)
            csv_writer.writerow(values); print(output_buffer.getvalue().strip())
        else: csv.writer(target_handle, **dialect_params).writerow(values)
            
    def _parse_exit_statement(self):
        self._expect('EXIT')
        token = self._current_token()
        
        # EXIT LOOP is valid for DO...LOOP structures
        if not token or token[0] not in ['FOR', 'WHILE', 'LOOP', 'DO']:
            self._error("EXIT must be followed by FOR, WHILE, LOOP, or DO")
        
        exit_type = token[0]
        self._next_token()
        
        # Map EXIT LOOP and EXIT DO to the same internal type
        if exit_type == 'LOOP' or exit_type == 'DO':
            raise LoopExit('DO')  # Use 'DO' as the internal identifier
        else:
            raise LoopExit(exit_type)

    # 4. Implement the DO...LOOP parser:
    def _parse_do_loop_statement(self):
        """
        Parse DO...LOOP with optional WHILE/UNTIL conditions.
        Supports:
        - DO WHILE condition ... LOOP
        - DO UNTIL condition ... LOOP
        - DO ... LOOP WHILE condition   
        - DO ... LOOP UNTIL condition
        - DO ... LOOP (infinite loop)
        """
        start_index = self.token_index
        self._expect('DO')
        
        pre_test_type = None
        pre_test_condition_index = None
        
        if self._current_token() and self._current_token()[0] == 'WHILE':
            pre_test_type = 'WHILE'
            self._next_token()
            pre_test_condition_index = self.token_index
            self._skip_condition()
        elif self._current_token() and self._current_token()[0] == 'UNTIL':
            pre_test_type = 'UNTIL'
            self._next_token()
            pre_test_condition_index = self.token_index
            self._skip_condition()
        
        if self._current_token() and self._current_token()[0] == 'NEWLINE':
            self._next_token()
        
        body_start_index = self.token_index
        
        while True:
            # For pre-test loops, check condition before each iteration
            if pre_test_type:
                saved_index = self.token_index
                self.token_index = pre_test_condition_index
                condition_result = self._parse_condition() != 0
                self.token_index = saved_index
                
                if (pre_test_type == 'WHILE' and not condition_result) or \
                   (pre_test_type == 'UNTIL' and condition_result):
                    self._skip_to_loop_end(start_index)
                    return
            
            # Execute the loop body, catching any EXIT LOOP calls
            try:
                self.token_index = body_start_index
                self.run_block(end_tokens={'LOOP'})
            except LoopExit as e:
                if e.args[0] in ['DO', 'LOOP']:
                    # EXIT LOOP was called. Scan forward to find the matching LOOP token.
                    self._skip_block('DO', 'LOOP')
                    
                    # We are now positioned *after* the LOOP token. We still need
                    # to skip any post-loop condition (e.g., UNTIL x > 5).
                    if self._current_token() and self._current_token()[0] in ['WHILE', 'UNTIL']:
                        self._next_token() # Consume WHILE or UNTIL
                        # Scan forward past the condition until the end of the line.
                        while self._current_token() and self._current_token()[0] not in ['NEWLINE', 'END', 'COLON']:
                            self._next_token()
                    return
                else:
                    # This was an EXIT for a different loop (e.g. EXIT FOR), so re-raise it.
                    raise e
            
            # We should now be at the LOOP token
            self._expect('LOOP')
            
            # Check for a post-test condition (LOOP WHILE/UNTIL)
            if self._current_token() and self._current_token()[0] == 'WHILE':
                self._next_token()
                if not (self._parse_condition() != 0):
                    break # Condition is false, exit the loop
            elif self._current_token() and self._current_token()[0] == 'UNTIL':
                self._next_token()
                if self._parse_condition() != 0:
                    break # Condition is true, exit the loop
            
            # No post-test condition, or condition allows continuation.
            # The loop will restart and rewind the token_index.


    def _skip_condition(self):
        """Skip past a condition expression to the next statement."""
        # This is a simple version - enhance if needed for complex conditions
        depth = 0
        while self._current_token():
            token = self._current_token()
            if token[0] == 'LPAREN':
                depth += 1
            elif token[0] == 'RPAREN':
                depth -= 1
            elif depth == 0 and token[0] in ['NEWLINE', 'COLON']:
                break
            self._next_token()

    def _skip_to_loop_end(self, do_index):
        """Skip past the entire LOOP statement including any conditions."""
        # Try using the jump map first
        if do_index in self.jump_map:
            loop_index = self.jump_map[do_index].get('loop')
            if loop_index:
                # Position at the LOOP token
                self.token_index = loop_index + 1  # Move PAST the LOOP token
                
                # Now check if there's a WHILE/UNTIL condition to skip
                if self._current_token() and self._current_token()[0] in ['WHILE', 'UNTIL']:
                    self._next_token()
                    # Skip the condition - keep going until we hit a statement terminator
                    depth = 0
                    while self._current_token():
                        tok = self._current_token()
                        if tok[0] == 'LPAREN':
                            depth += 1
                        elif tok[0] == 'RPAREN':
                            depth -= 1
                        elif depth == 0 and tok[0] in ['NEWLINE', 'COLON', 'END']:
                            break
                        self._next_token()
                return
        
        # Fallback without jump map
        level = 1
        while self._current_token() and level > 0:
            token = self._current_token()
            self._next_token()
            if token[0] == 'DO':
                level += 1
            elif token[0] == 'LOOP':
                level -= 1
                if level == 0:
                    # We're now positioned after LOOP, check for conditions
                    if self._current_token() and self._current_token()[0] in ['WHILE', 'UNTIL']:
                        self._next_token()
                        # Skip condition expression
                        depth = 0
                        while self._current_token():
                            tok = self._current_token()
                            if tok[0] == 'LPAREN':
                                depth += 1
                            elif tok[0] == 'RPAREN':
                                depth -= 1
                            elif depth == 0 and tok[0] in ['NEWLINE', 'COLON', 'END']:
                                break
                            self._next_token()
                    return
        
    def _parse_while_statement(self):
        start_index = self.token_index
        self._expect('WHILE')

        try:
            while True:
                # On each pass, rewind to re-evaluate the condition
                self.token_index = start_index + 1
                if not (self._parse_condition() != 0):
                    # Normal Exit: condition is false. Find WEND and exit.
                    self.token_index = start_index + 1
                    self._skip_block('WHILE', 'WEND')
                    return

                # Condition was true, execute the body.
                if self._current_token() and self._current_token()[0] == 'NEWLINE':
                    self._next_token()
                
                self.run_block(end_tokens={'WEND'})
                self._expect('WEND')

        except LoopExit as e:
            if e.args[0] == 'WHILE':
                # An EXIT WHILE was called. Find the WEND from our current position.
                self._skip_block('WHILE', 'WEND')
                return
            else:
                # Not our EXIT, re-raise for an outer loop to handle
                raise e

    def _parse_sort_statement(self):
        self._expect('SORT')
        array_var_token = self._expect('ID')
        array_var_name = array_var_token[1]

        if array_var_name not in self.variables or not isinstance(self.variables.get(array_var_name), list):
            self._error(f"'{array_var_name}' is not a dimensioned array.")
        
        the_array = self.variables[array_var_name]
        if not the_array:
            return # Array is empty, nothing to do.

        sort_key = None
        
        if self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1] == 'ON':
            self._next_token() # Consume ON
            sort_key_expr = self._parse_expression()
            if not isinstance(sort_key_expr, str):
                self._error("Sort key provided with ON must be a string expression.")
            sort_key = self._normalize_hash_key(sort_key_expr) if self.hash_keys_mode == 'IGNORE_CASE' else sort_key_expr

        reverse_order = False
        if self._current_token() and self._current_token()[0] == 'ID':
            direction = self._current_token()[1]
            if direction in ['ASC', 'DESC']:
                if direction == 'DESC':
                    reverse_order = True
                self._next_token()

        try:
            if sort_key:
                the_array.sort(key=lambda item: item.get(sort_key, 0) if isinstance(item, dict) else 0, reverse=reverse_order)
            else:
                the_array.sort(reverse=reverse_order)
        except TypeError:
            if sort_key:
                the_array.sort(key=lambda item: str(item.get(sort_key, "")) if isinstance(item, dict) else "", reverse=reverse_order)
            else:
                the_array.sort(key=lambda item: str(item), reverse=reverse_order)
                
    def _parse_files_statement(self):
        self.variables['ERR'] = 0.0; self._expect('FILES')
        path_arg, with_details, into_array_name = ".", False, None
        if self._current_token() and self._current_token()[0] not in ['NEWLINE', 'INTO', 'WITH']: path_arg = self._parse_expression()
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token(); into_array_name = self._expect('ID')[1]
            if into_array_name not in self.variables or not isinstance(self.variables.get(into_array_name), list):
                self._error(f"'{into_array_name}' is not a dimensioned array.")
        if self._current_token() and self._current_token()[0] == 'WITH':
            self._next_token(); self._expect('DETAILS'); with_details = True
        try:
            expanded_path = os.path.expanduser(str(path_arg))
            glob_pattern = os.path.join(expanded_path, '*') if os.path.isdir(expanded_path) else expanded_path
        except Exception: self.variables['ERR'] = 1.0; glob_pattern = path_arg
        if into_array_name is None:
            file_paths = sorted(glob.glob(glob_pattern))
            if not file_paths: print("File not found"); return
            if with_details:
                for fp in file_paths:
                    try:
                        stats = os.stat(fp); name = os.path.basename(fp)
                        date_str = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        size_str = "<DIR>" if os.path.isdir(fp) else str(stats.st_size)
                        print(f"{name:<25}\t{size_str:>12}\t{date_str}")
                    except OSError: continue
            else:
                for fp in file_paths: print(os.path.basename(fp))
        else:
            if with_details:
                detailed_list = []
                for fp in glob.glob(glob_pattern):
                    try:
                        stats = os.stat(fp)
                        detailed_list.append({"name": os.path.basename(fp), "size": float(stats.st_size),
                                              "date": datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                                              "isdir": -1.0 if os.path.isdir(fp) else 0.0})
                    except OSError: continue
                self.variables[into_array_name] = detailed_list
            else: self.variables[into_array_name] = [os.path.basename(p) for p in glob.glob(glob_pattern)]

    def _parse_name_statement(self):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('ID'); old_filename = self._parse_expression(); self._expect('AS'); new_filename = self._parse_expression()
        try: os.rename(str(old_filename), str(new_filename))
        except FileNotFoundError as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            raise e
        except FileExistsError as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = 17.0, str(e)
            raise e
        except Exception as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            raise e

    def _parse_chdir_statement(self):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""}); self._expect('CHDIR'); path = self._parse_expression()
        try: os.chdir(os.path.expanduser(str(path)))
        except FileNotFoundError as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            raise e
        except NotADirectoryError as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = 20.0, str(e)
            raise e
        except Exception as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            raise e

    def _parse_mkdir_statement(self):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""}); self._expect('MKDIR'); path = self._parse_expression()
        try: os.makedirs(os.path.expanduser(str(path)), exist_ok=True)
        except Exception as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            raise e

    def _parse_rmdir_statement(self):
            self.variables.update({'ERR': 0.0, 'ERRMSG$': ""}); self._expect('RMDIR'); path = self._parse_expression()
            try: os.rmdir(os.path.expanduser(str(path)))
            except FileNotFoundError as e:
                self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
                raise e
            except OSError as e:
                self.variables['ERR'], self.variables['ERRMSG$'] = 39.0, str(e)
                raise e
            except Exception as e:
                self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
                raise e
 
    def _parse_kill_statement(self):
            self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
            self._expect('KILL')
            if self._current_token() and self._current_token()[0] == 'NEWLINE': self._error("KILL command requires a string argument.")
            filename = self._parse_expression()
            try:
                os.remove(os.path.expanduser(str(filename)))
            except FileNotFoundError as e:
                self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
                #raise e
            except Exception as e:
                self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
                raise e

    def _parse_error_statement(self):
        """
        Parse and execute an ERROR statement to trigger a user-defined error.
        """
        self._expect('ERROR')
        error_code = self._parse_expression()
        
        if not isinstance(error_code, (int, float)):
            self._error("ERROR requires a numeric error code.")
        
        error_num = int(error_code)
        
        # Check for optional custom message
        error_message = f"User-defined error {error_num}"
        if self._current_token() and self._current_token()[0] == 'COMMA':
            self._next_token()
            custom_message = self._parse_expression()
            if isinstance(custom_message, str):
                error_message = custom_message
            else:
                self._error("Error message must be a string.")
        
        # Set error variables
        self.variables['ERR'] = float(error_num)
        self.variables['ERRMSG$'] = error_message
        
        # Only raise if there's no error handler, otherwise let the normal error handling take over
        if not self.error_handler_label or self.in_error_handler:
            raise RuntimeError(f"Error {error_num}: {error_message}")
        else:
            # Jump to error handler (same logic as other errors)
            self.in_error_handler = True
            self.error_resume_index = self._find_next_statement_index(self.token_index)
            self.token_index = self.labels[self.error_handler_label]
        
    def _parse_run_statement(self):
        """
        Parse and execute a RUN statement to call another program and return.
        Uses a proper call stack to handle nested calls and gracefully handles errors.
        """
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('RUN')
        
        filename = self._parse_expression()
        if not isinstance(filename, str):
            self._error("RUN requires a string filename.")
        
        run_args = []
        while self._current_token() and self._current_token()[0] == 'COMMA':
            self._next_token()
            arg = self._parse_expression()
            run_args.append(str(arg))

        try:
            expanded_filename = os.path.expanduser(filename)
            if not os.path.exists(expanded_filename):
                raise FileNotFoundError(f"RUN: File not found: {filename}")

            with open(expanded_filename, 'r', encoding='utf-8') as f:
                target_source = f.read()

            # Push current state onto the stack
            current_state = {
                'lexer': self.lexer, 'tokens': self.tokens, 'token_index': self.token_index,
                'labels': self.labels, 'jump_map': self.jump_map,
                'form_definitions': self.form_definitions, 'command_args': self.command_args,
                'variables_snapshot': self.variables.copy(), 'gosub_stack': self.gosub_stack[:]
            }
            self.run_stack.append(current_state)

            # Setup new interpreter state for the called program
            self.lexer = Lexer(preprocess_continuations(target_source))
            self.tokens = self.lexer.tokens
            self.token_index = 0
            self.labels = {}
            self.jump_map = {}
            self.form_definitions = {} # Forms are not shared between run contexts
            self.command_args = run_args
            self.gosub_stack = []

            self._pre_scan_for_jumps()
            self._scan_for_labels()
            
            run_error = None
            try:
                # Execute the called program
                while self._current_token() and self._current_token()[0] != 'END' and not self.program_terminated:
                    if not self._parse_line():
                        break
            except ProgramEnd:
                pass # Normal program termination is not an error
            except Exception as e:
                # Capture the error instead of re-raising it immediately
                run_error = e
            finally:
                # CRITICAL: Always restore the caller's state
                if self.run_stack:
                    saved_state = self.run_stack.pop()
                    self.lexer = saved_state['lexer']
                    self.tokens = saved_state['tokens']
                    self.token_index = saved_state['token_index']
                    self.labels = saved_state['labels']
                    self.jump_map = saved_state['jump_map']
                    self.form_definitions = saved_state['form_definitions']
                    self.command_args = saved_state['command_args']
                    self.variables = saved_state['variables_snapshot']
                    self.gosub_stack = saved_state['gosub_stack']
                    # Reset the termination flag for the caller
                    self.program_terminated = False
                else:
                    # This case should ideally not be reached
                    print("CRITICAL WARNING: RUN stack underflow during state restoration.", file=sys.stderr)


            # Now that the caller's context is restored, set error variables
            if run_error:
                self.variables['ERR'] = 1.0
                self.variables['ERRMSG$'] = str(run_error)
            else:
                self.variables['ERR'] = 0.0
                self.variables['ERRMSG$'] = ""

        except Exception as setup_error:
            # This block catches errors during setup (e.g., FileNotFoundError)
            # We must still try to restore state if something was pushed to the stack
            if self.run_stack:
                saved_state = self.run_stack.pop()
                self.lexer = saved_state['lexer']; self.tokens = saved_state['tokens']
                self.token_index = saved_state['token_index']; self.labels = saved_state['labels']
                self.jump_map = saved_state['jump_map']; self.form_definitions = saved_state['form_definitions']
                self.command_args = saved_state['command_args']; self.variables = saved_state['variables_snapshot']
            
            # Since setup failed, this IS a fatal error for the caller's logic.
            # We set the variables and then raise the error to stop the caller.
            self.variables['ERR'] = 2.0 if isinstance(setup_error, FileNotFoundError) else 1.0
            self.variables['ERRMSG$'] = str(setup_error)
            self._error(f"RUN setup error: {setup_error}")

    def _parse_chain_statement(self):
        """
        Parse and execute a CHAIN statement to transfer control to another program.
        
        Syntax:
        CHAIN "filename.bas"
        CHAIN "filename.bas", "arg1", "arg2", ...
        CHAIN "filename.bas" PRESERVE
        CHAIN "filename.bas", "arg1" PRESERVE
        """
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('CHAIN')
        
        # Parse the filename
        filename = self._parse_expression()
        if not isinstance(filename, str):
            self._error("CHAIN requires a string filename.")
        
        # Parse optional arguments
        chain_args = []
        while self._current_token() and self._current_token()[0] == 'COMMA':
            self._next_token()
            # Check if the next token is PRESERVE (not an argument)
            if self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'PRESERVE':
                break
            arg = self._parse_expression()
            chain_args.append(str(arg))
        
        # Check for PRESERVE keyword
        preserve_variables = False
        if self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'PRESERVE':
            self._next_token()
            preserve_variables = True
        
        try:
            # Expand user home directory if needed
            expanded_filename = os.path.expanduser(filename)
            
            # Check if file exists
            if not os.path.exists(expanded_filename):
                self.variables['ERR'] = 2.0
                self.variables['ERRMSG$'] = f"File not found: {filename}"
                self._error(f"CHAIN: File not found: {filename}")
            
            # Read the target program
            try:
                with open(expanded_filename, 'r', encoding='utf-8') as f:
                    target_source = f.read()
            except Exception as e:
                self.variables['ERR'] = 1.0
                self.variables['ERRMSG$'] = str(e)
                self._error(f"CHAIN: Error reading file: {e}")
            
            # Close all open files before chaining
            self._close_all_files()
            
            # Close database connection
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
            
            # Prepare the new interpreter
            lexer = Lexer(preprocess_continuations(target_source))
            new_interpreter = Interpreter(lexer, chain_args, debug=self.debug_mode)
            
            # Handle variable preservation
            if preserve_variables:
                # Copy all variables except system variables and arrays/hashes that might cause issues
                system_vars = {'ERR', 'ERRMSG$', 'SQL_ROWCOUNT', 'SQL_FOUND', 'SQL_NOTFOUND', 'RECNO'}
                for var_name, var_value in self.variables.items():
                    if var_name not in system_vars:
                        # Only preserve simple variables (strings and numbers)
                        if isinstance(var_value, (str, int, float)):
                            new_interpreter.variables[var_name] = var_value
                        elif isinstance(var_value, (list, dict)):
                            # Serialize complex data structures to JSON strings
                            try:
                                serialized_name = f"{var_name}_JSON$"
                                json_data = self._execute_function('JSON_SERIALIZE$', [var_value])
                                new_interpreter.variables[serialized_name] = json_data
                                print(f"CHAIN: Serialized {var_name} as {serialized_name}")
                            except Exception as e:
                                print(f"CHAIN: Warning - Could not serialize {var_name}: {e}")
                                
            # Set up the new interpreter with the same configuration
            new_interpreter.db_engine = self.db_engine
            new_interpreter.sql_fatal_errors = self.sql_fatal_errors
            new_interpreter.hash_keys_mode = self.hash_keys_mode
            new_interpreter.trace_mode = self.trace_mode
            
            # Initialize database with the same engine
            new_interpreter._init_db()
            
            # Replace the current interpreter's state
            self.lexer = new_interpreter.lexer
            self.tokens = new_interpreter.tokens
            self.token_index = 0
            self.variables = new_interpreter.variables
            self.file_handles = new_interpreter.file_handles
            self.command_args = chain_args
            self.gosub_stack = []
            self.labels = new_interpreter.labels
            self.form_definitions = new_interpreter.form_definitions
            self.db_connection = new_interpreter.db_connection
            self.db_cursor = new_interpreter.db_cursor
            self.jump_map = new_interpreter.jump_map
            
            # Reset error handling state
            self.error_handler_label = None
            self.in_error_handler = False
            self.error_resume_index = None
            
            print(f"CHAIN: Transferred control to {filename}")
            if chain_args:
                print(f"CHAIN: Arguments passed: {', '.join(chain_args)}")
            if preserve_variables:
                print("CHAIN: Variables preserved")
            
        except Exception as e:
            self.variables['ERR'] = 1.0
            self.variables['ERRMSG$'] = str(e)
            if 'File not found' in str(e):
                self.variables['ERR'] = 2.0
            self._error(f"CHAIN error: {e}")

    def _parse_zip_statement(self):
        """
        Parse and execute a ZIP statement to create an archive.
        
        Syntax:
        ZIP "archive.zip" FROM "file1.txt", "*.bas", "data.csv"
        """
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('ZIP')
        
        archive_name = self._parse_expression()
        if not isinstance(archive_name, str):
            self._error("ZIP requires a string archive name.")
        
        self._expect('ID')  # Expect FROM keyword
        if self._current_token()[-2][1].upper() != 'FROM':
            self._error("Expected FROM after archive name in ZIP statement.")
        
        files_to_zip = []
        
        # Parse the comma-separated list of files/patterns
        if self._current_token() and self._current_token()[0] not in ['NEWLINE', 'END']:
            while True:
                file_pattern = self._parse_expression()
                if not isinstance(file_pattern, str):
                    self._error("File patterns must be strings.")
                
                # Auto-detect if it's a pattern or literal file
                if '*' in file_pattern or '?' in file_pattern:
                    # It's a glob pattern - expand it
                    expanded_files = glob.glob(file_pattern)
                    if expanded_files:
                        files_to_zip.extend(expanded_files)
                    else:
                        print(f"Warning: Pattern '{file_pattern}' matched no files")
                else:
                    # It's a literal filename
                    if os.path.exists(file_pattern):
                        files_to_zip.append(file_pattern)
                    else:
                        print(f"Warning: File '{file_pattern}' not found")
                
                # Check if there are more files
                if self._current_token() and self._current_token()[0] == 'COMMA':
                    self._next_token()
                else:
                    break
        
        if not files_to_zip:
            self.variables['ERR'] = 1.0
            self.variables['ERRMSG$'] = "No files found to zip"
            if self.sql_fatal_errors:
                self._error("No files found to zip")
        
        try:
            with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in files_to_zip:
                    # Use just the filename in the archive, not the full path
                    arc_name = os.path.basename(file_path)
                    zf.write(file_path, arc_name)
                    print(f"Added: {file_path} -> {arc_name}")
            
            print(f"Created {archive_name} with {len(files_to_zip)} files")
            self.variables['ERR'] = 0.0
            self.variables['ERRMSG$'] = ""
            
        except Exception as e:
            self.variables['ERR'] = 1.0
            self.variables['ERRMSG$'] = str(e)
            if self.sql_fatal_errors:
                self._error(f"ZIP error: {e}")

    def _parse_unzip_statement(self):
        """
        Parse and execute an UNZIP statement to extract an archive.
        
        Syntax:
        UNZIP "archive.zip"
        UNZIP "archive.zip" INTO "target_directory"
        """
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('UNZIP')
        
        archive_name = self._parse_expression()
        if not isinstance(archive_name, str):
            self._error("UNZIP requires a string archive name.")
        
        target_dir = "."  # Default to current directory
        
        # Check for optional TO clause
        if self._current_token() and self._current_token()[0] == 'TO':
            self._next_token()
            target_dir = self._parse_expression()
            if not isinstance(target_dir, str):
                self._error("Target directory must be a string.")
        
        try:
            # Check if archive exists
            if not os.path.exists(archive_name):
                self.variables['ERR'] = 2.0
                self.variables['ERRMSG$'] = f"Archive not found: {archive_name}"
                self._error(f"Archive not found: {archive_name}")
            
            # Create target directory if it doesn't exist
            if target_dir != "." and not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            # Extract the archive
            with zipfile.ZipFile(archive_name, 'r') as zf:
                # Get list of files in archive
                file_list = zf.namelist()
                
                # Extract all files
                zf.extractall(target_dir)
                
                print(f"Extracted {len(file_list)} files from {archive_name}")
                for filename in file_list:
                    print(f"  -> {os.path.join(target_dir, filename)}")
            
            self.variables['ERR'] = 0.0
            self.variables['ERRMSG$'] = ""
            
        except zipfile.BadZipFile as e:
            self.variables['ERR'] = 1.0
            self.variables['ERRMSG$'] = f"Invalid ZIP file: {e}"
            if self.sql_fatal_errors:
                self._error(f"Invalid ZIP file: {e}")
        except Exception as e:
            self.variables['ERR'] = 1.0
            self.variables['ERRMSG$'] = str(e)
            if self.sql_fatal_errors:
                self._error(f"UNZIP error: {e}")
        
    def _parse_shell_statement(self):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""}); self._expect('SHELL')
        if self._current_token() and self._current_token()[0] == 'NEWLINE': self._error("SHELL command requires a string argument.")
        command_string = self._parse_expression(); dest_var = None
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token(); dest_var = self._expect('ID')[1]
            if not dest_var.endswith('$'): self._error("Destination for SHELL output must be a string variable.")
        try:
            if dest_var:
                result = subprocess.run(str(command_string), shell=True, check=False, capture_output=True, text=True, encoding='utf-8', errors='replace')
                self.variables[dest_var] = result.stdout
                if result.stderr: self.variables['ERRMSG$'] = result.stderr
            else: result = subprocess.run(str(command_string), shell=True, check=False)
            self.variables['ERR'] = float(result.returncode)
        except Exception as e: 
            self.variables['ERR'], self.variables['ERRMSG$'] = -1.0, str(e)
            raise e
            
    def _parse_push_statement(self):
        self._expect('PUSH')
        array_name = self._expect('ID')[1]
        self._expect('COMMA')
        value = self._parse_expression()
        
        if array_name not in self.variables or not isinstance(self.variables[array_name], list):
            self._error(f"'{array_name}' is not an array.")
        
        self.variables[array_name].append(value)

    def _parse_pop_statement(self):
        self._expect('POP')
        array_name = self._expect('ID')[1]
        
        if array_name not in self.variables or not isinstance(self.variables[array_name], list):
            self._error(f"'{array_name}' is not an array.")
        
        if not self.variables[array_name]:
            self._error(f"Cannot POP from empty array '{array_name}'.")
        
        # Store result in a variable if INTO clause is present
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token()
            var_name = self._expect('ID')[1]
            self.variables[var_name] = self.variables[array_name].pop()
        else:
            self.variables[array_name].pop()

    def _parse_unshift_statement(self):
        self._expect('UNSHIFT')
        array_name = self._expect('ID')[1]
        self._expect('COMMA')
        value = self._parse_expression()
        
        if array_name not in self.variables or not isinstance(self.variables[array_name], list):
            self._error(f"'{array_name}' is not an array.")
        
        self.variables[array_name].insert(0, value)

    def _parse_shift_statement(self):
        self._expect('SHIFT')
        array_name = self._expect('ID')[1]
        
        if array_name not in self.variables or not isinstance(self.variables[array_name], list):
            self._error(f"'{array_name}' is not an array.")
        
        if not self.variables[array_name]:
            self._error(f"Cannot SHIFT from empty array '{array_name}'.")
        
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token()
            var_name = self._expect('ID')[1]
            self.variables[var_name] = self.variables[array_name].pop(0)
        else:
            self.variables[array_name].pop(0)

    def _parse_splice_statement(self):
        self._expect('SPLICE')
        array_name = self._expect('ID')[1]
        self._expect('COMMA')
        start_index = int(self._parse_expression())
        self._expect('COMMA')
        delete_count = int(self._parse_expression())
        
        if array_name not in self.variables or not isinstance(self.variables[array_name], list):
            self._error(f"'{array_name}' is not an array.")
        
        arr = self.variables[array_name]
        if start_index < 0 or start_index > len(arr):  # Changed >= to >
            self._error(f"SPLICE start index {start_index} out of bounds.")
        
        # Remove elements (only if start_index is within current bounds)
        if start_index < len(arr):
            for _ in range(min(delete_count, len(arr) - start_index)):
                arr.pop(start_index)
        
        # Insert new elements if provided
        while self._current_token() and self._current_token()[0] == 'COMMA':
            self._next_token()
            value = self._parse_expression()
            arr.insert(start_index, value)
            start_index += 1

    def _parse_reverse_statement(self):
        self._expect('REVERSE')
        array_name = self._expect('ID')[1]
        
        if array_name not in self.variables or not isinstance(self.variables[array_name], list):
            self._error(f"'{array_name}' is not an array.")
        
        self.variables[array_name].reverse()
    
    def _parse_browser_statement(self):
        """Parses and executes the BROWSER command to open a URL."""
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('BROWSER')
        
        # The next part must be an expression that resolves to the URL string
        url = self._parse_expression()
        if not isinstance(url, str):
            self._error("BROWSER command requires a string argument for the URL.")

        # Default options for webbrowser.open()
        new_tab = 0  # 0: same window, 1: new window, 2: new tab

        # Parse an optional OPTIONS clause, e.g., OPTIONS "new=2"
        if self._current_token() and self._current_token()[0] == 'OPTIONS':
            self._next_token()
            options_str = self._parse_expression()
            if isinstance(options_str, str):
                # Simple parsing for the 'new' option
                opt_str_lower = options_str.lower()
                if "new=1" in opt_str_lower:
                    new_tab = 1
                elif "new=2" in opt_str_lower:
                    new_tab = 2
        
        try:
            # Open the URL in the default web browser
            success = webbrowser.open(url, new=new_tab)
            if not success:
                # This can happen on systems without a GUI or configured browser
                self.variables['ERR'] = 52.0 # Bad file name or number
                self.variables['ERRMSG$'] = "Could not open a web browser. Check system configuration."
        except Exception as e:
            self.variables['ERR'] = 1.0 # General error
            self.variables['ERRMSG$'] = f"An error occurred while trying to open the browser: {e}"
            
    def _parse_fetch_statement(self):
        self.variables['ERR'] = 0.0; self._expect('FETCH'); url = self._parse_expression()
        post_data_hash, headers_hash, upload_file_info, method = None, None, None, 'GET'
        while self._current_token() and self._current_token()[0] not in ['INTO', 'TO FILE']:
            clause = self._current_token()
            if clause[0] == 'POST':
                method = 'POST'; self._next_token(); hash_name = self._expect('ID')[1]
                post_data_hash = self.variables.get(hash_name)
                if self._current_token() and self._current_token()[0] == 'LPAREN': self._next_token(); self._expect('RPAREN')
            elif clause[0] == 'USING':
                self._next_token(); next_clause = self._current_token()
                if next_clause[0] == 'ID' and next_clause[1] == 'FILE':
                    self._next_token(); field_name = self._parse_expression(); self._expect('ASSIGN'); file_path = self._parse_expression()
                    upload_file_info = (field_name, file_path)
                elif next_clause[0] == 'ID' and next_clause[1] == 'HEADERS':
                    self._next_token(); hash_name = self._expect('ID')[1]; headers_hash = self.variables.get(hash_name)
                    if self._current_token() and self._current_token()[0] == 'LPAREN': self._next_token(); self._expect('RPAREN')
                else: self._error("Expected FILE or HEADERS after USING")
            else: self._error(f"Unexpected token '{clause[0]}' in FETCH statement")
        destination_token = self._current_token()
        if not destination_token: self._error("FETCH statement requires an INTO or TO FILE clause.")
        try:
            if destination_token[0] == 'TO FILE':
                self._next_token(); local_filename = self._parse_expression()
                if method == 'POST':
                    if upload_file_info:
                        with open(upload_file_info[1], 'rb') as f:
                            files = {upload_file_info[0]: f}; response = requests.post(url, data=post_data_hash, headers=headers_hash, files=files, timeout=30, stream=True)
                    else: response = requests.post(url, data=post_data_hash, headers=headers_hash, timeout=15, stream=True)
                else: response = requests.get(url, headers=headers_hash, timeout=15, stream=True)
                response.raise_for_status()
                with open(local_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
                self.variables['ERR'] = float(response.status_code)
            elif destination_token[0] == 'INTO':
                self._next_token(); dest_var = self._expect('ID')[1]
                if upload_file_info and method == 'POST':
                    with open(upload_file_info[1], 'rb') as f:
                        files = {upload_file_info[0]: f}; response = requests.post(url, data=post_data_hash, headers=headers_hash, files=files, timeout=30)
                elif method == 'POST': response = requests.post(url, data=post_data_hash, headers=headers_hash, timeout=15)
                else: response = requests.get(url, headers=headers_hash, timeout=15)
                self.variables['ERR'] = float(response.status_code)
                try: self.variables[dest_var] = response.content.decode('utf-8')
                except UnicodeDecodeError: self.variables[dest_var] = "Binary data received"
            else: self._error("FETCH statement requires an INTO or TO FILE clause.")
        except FileNotFoundError: self.variables['ERR'] = -2.0
        except requests.exceptions.RequestException: self.variables['ERR'] = -1.0

    def _parse_load_statement(self):
        peek = self._peek_token()
        if peek and peek[0] == 'CSV': self._parse_load_csv_statement()
        elif peek and peek[0] == 'JSON': self._parse_load_json_statement()
        elif peek and peek[0] == 'EXCEL': self._parse_load_excel_statement()
        elif peek and peek[0] == 'FIXED': self._parse_load_fixed_statement()
        else: self._error("Expected CSV, JSON, FIXED, or EXCEL after LOAD")

    def _parse_table_name(self):
        """Parses a table name, accepting either an unquoted ID or a quoted STRING."""
        token = self._current_token()
        if not token or token[0] not in ['ID', 'STRING']:
            self._error("Expected a table name (e.g., MyTable or \"MyTable\")")
        
        self._next_token()
        name = token[1]
        if token[0] == 'STRING':
            # Strip the surrounding quotes from the string token
            return name.strip('"')
        return name  
        
    def _parse_load_csv_statement(self):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('LOAD')
        self._expect('CSV')

        csv_filename = self._parse_expression()
        destination_mode, destination_target, db_mode = None, None, None

        if self._current_token() and self._current_token()[0] == 'CREATE':
            destination_mode = 'CREATE_TABLE'; self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE': self._next_token()
            destination_target = self._parse_table_name()
        elif self._current_token() and self._current_token()[0] == 'INTO':
            destination_mode = 'INTO_TABLE'; self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE': self._next_token()
            destination_target = self._parse_table_name()
            if self._current_token() and self._current_token()[0] in ['APPEND', 'REPLACE']:
                db_mode = self._current_token()[1]; self._next_token()
            else: self._error("Expected APPEND or REPLACE for INTO TABLE clause.")
        else: self._error("Expected CREATE TABLE, INTO TABLE clause.")

        options = {'header': False, 'skip': 0, 'limit': None, 'encoding': 'utf-8', 
                   'delimiter': ',', 'transform': '', 'format': 'CSV', 'batchsize': 10000, 'fields': ''}
        if self._current_token() and self._current_token()[0] == 'OPTIONS':
            self._next_token(); options_str = self._parse_expression(); temp_options = {}
            key_matches = list(re.finditer(r'\b(\w+)=', options_str))
            for i, match in enumerate(key_matches):
                key, start_pos = match.group(1).lower(), match.end()
                end_pos = key_matches[i+1].start() if i + 1 < len(key_matches) else len(options_str)
                value = options_str[start_pos:end_pos].strip()
                if value.startswith('"') and value.endswith('"'): value = value[1:-1]
                temp_options[key] = value
            for key, value in temp_options.items():
                if key == 'header': options['header'] = value.lower() in ['true', 'y', '1']
                elif key in ['skip', 'limit', 'batchsize']: options[key] = int(value)
                else: options[key] = value
        
        try:
            with open(csv_filename, 'r', newline='', encoding=options['encoding']) as infile:
                for _ in range(options['skip']): next(infile)
                reader = csv.reader(infile, delimiter=options['delimiter'])
                
                original_headers = []
                if options['header']:
                    try: original_headers = next(reader)
                    except StopIteration: return

                final_headers, column_map = original_headers, list(range(len(original_headers))) if original_headers else None
                
                if options['fields']:
                    if not options['header']: self._error("FIELDS option requires header=true.")
                    field_specs = re.split(r',\s*(?![^\[]*\])', options['fields'])
                    
                    if field_specs[0].strip() == '*':
                        excluded_fields = {spec.strip()[2:-1].lower() for spec in field_specs[1:] if spec.strip().startswith('-[')}
                        final_headers = [h for h in original_headers if h.lower() not in excluded_fields]
                        column_map = [i for i, h in enumerate(original_headers) if h.lower() not in excluded_fields]
                    else:
                        header_lookup = {h.lower(): i for i, h in enumerate(original_headers)}
                        new_headers, new_map = [], []
                        for spec in field_specs:
                            match = re.match(r'\[([^\]]*)\](?:\s+as\s+(\w+))?', spec.strip())
                            if not match: self._error(f"Invalid FIELDS specification: {spec}")
                            original_name, new_name = match.groups()
                            if original_name.lower() not in header_lookup:
                                self._error(f"Field '{original_name}' not found in CSV header.")
                            new_map.append(header_lookup[original_name.lower()])
                            if self.hash_keys_mode == 'IGNORE_CASE':
                                final_field_name = new_name.upper() if new_name else original_name.upper()
                            else:
                                final_field_name = new_name if new_name else original_name
                            new_headers.append(final_field_name)
                        final_headers, column_map = new_headers, new_map

                elif destination_mode in ['CREATE_TABLE', 'INTO_TABLE']:
                    cursor = self.db_cursor
                    if destination_mode == 'CREATE_TABLE':
                        if not final_headers and not options['fields']: self._error("CREATE TABLE requires header=true or a FIELDS option.")
                        cols_def = ', '.join([f'[{h}] TEXT' for h in final_headers])
                        cursor.execute(f'DROP TABLE IF EXISTS [{destination_target}];'); cursor.execute(f'CREATE TABLE [{destination_target}] ({cols_def});')
                    if db_mode == 'REPLACE': cursor.execute(f'DELETE FROM [{destination_target}];')
                    
                    insert_sql, batch, total_rows_processed = None, [], 0
                    self.db_connection.execute('BEGIN TRANSACTION;')
                    try:
                        for row in reader:
                            if column_map is None: column_map = list(range(len(row)))
                            if not row: continue
                            processed_row = [row[i] for i in column_map if i < len(row)]
                            
                            if insert_sql is None:
                                num_cols = len(processed_row)
                                if num_cols == 0: continue
                                placeholders = ', '.join(['?'] * num_cols)
                                if final_headers:
                                    quoted_headers = ", ".join([f'[{h}]' for h in final_headers])
                                    insert_sql = f'INSERT INTO [{destination_target}] ({quoted_headers}) VALUES ({placeholders});'
                                else:
                                    insert_sql = f'INSERT INTO [{destination_target}] VALUES ({placeholders});'
                            
                            batch.append(processed_row)
                            total_rows_processed += 1
                            if len(batch) >= options['batchsize']:
                                cursor.executemany(insert_sql, batch); batch = []
                        
                        if batch: cursor.executemany(insert_sql, batch)
                        self.db_connection.execute('COMMIT;')
                        print(f"{total_rows_processed} records loaded into table {destination_target}")
                    except Exception as e:
                        self.db_connection.execute('ROLLBACK;'); raise e
        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {csv_filename}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, f"CSV load error: {e}"
            self._error(f"An error occurred during CSV load: {e}")

    def _parse_load_fixed_statement(self):
        """
        Parse and execute LOAD FIXED for fixed-width files.
        Refactored to stream the file and use explicit transactions.
        """
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('LOAD')
        self._expect('FIXED')
        
        filename = self._parse_expression()
        
        destination_mode, destination_target, db_mode = None, None, None
        
        if self._current_token() and self._current_token()[0] == 'CREATE':
            destination_mode = 'CREATE_TABLE'
            self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE': self._next_token()
            destination_target = self._parse_table_name()
        elif self._current_token() and self._current_token()[0] == 'INTO':
            destination_mode = 'INTO_TABLE'
            self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE': self._next_token()
            destination_target = self._parse_table_name()
            if self._current_token() and self._current_token()[0] in ['APPEND', 'REPLACE']:
                db_mode = self._current_token()[1]
                self._next_token()
            else:
                self._error("Expected APPEND or REPLACE for INTO TABLE clause.")
        else:
            self._error("Expected CREATE TABLE or INTO TABLE clause.")
        
        if not (self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'FIELDS'):
            self._error("LOAD FIXED requires a FIELDS specification.")
        
        self._next_token()
        fields_spec = self._parse_expression()
        #print("DEBUG-FIXED",destination_target)
        field_definitions = []
        for field_def in fields_spec.split(','):
            field_def = field_def.strip()
            if ':' not in field_def: self._error(f"Invalid field specification: {field_def}")
            field_name, positions = field_def.split(':', 1)
            if '-' not in positions: self._error(f"Invalid position specification: {positions}")
            start_pos, end_pos = positions.split('-', 1)
            try:
                start_pos = int(start_pos.strip()) - 1
                end_pos = int(end_pos.strip())
                field_definitions.append({'name': field_name.strip(), 'start': start_pos, 'end': end_pos})
            except ValueError: self._error(f"Invalid position numbers: {positions}")
        
        try:
            cursor = self.db_cursor
            if destination_mode == 'CREATE_TABLE':
                field_names = [f['name'] for f in field_definitions]
                cols_def = ', '.join([f'[{name}] TEXT' for name in field_names])
                cursor.execute(f'DROP TABLE IF EXISTS [{destination_target}]')
                cursor.execute(f'CREATE TABLE [{destination_target}] ({cols_def})')

            if db_mode == 'REPLACE':
                cursor.execute(f'DELETE FROM [{destination_target}]')
            
            field_names = [f['name'] for f in field_definitions]
            placeholders = ', '.join(['?'] * len(field_names))
            quoted_fields = ', '.join([f'[{name}]' for name in field_names])
            insert_sql = f'INSERT INTO [{destination_target}] ({quoted_fields}) VALUES ({placeholders})'

            batch, total_rows_processed = [], 0
            batch_size = 10000

            self.db_connection.execute('BEGIN TRANSACTION;')
            try:
                with open(filename, 'r', encoding='utf-8') as infile:
                    for line in infile:
                        line = line.rstrip('\n\r')
                        record = [line[f['start']:f['end']].strip() if f['start'] < len(line) else "" for f in field_definitions]
                        
                        if not any(record): continue

                        batch.append(record)
                        total_rows_processed += 1
                        if len(batch) >= batch_size:
                            cursor.executemany(insert_sql, batch); batch = []
                
                if batch: cursor.executemany(insert_sql, batch)
                self.db_connection.execute('COMMIT;')
                print(f"Loaded {total_rows_processed} records into table {destination_target}")

            except Exception as e:
                self.db_connection.execute('ROLLBACK;'); raise e
        
        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {filename}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"LOAD FIXED error: {e}")

        
    def _parse_for_statement(self):
        start_index = self.token_index
        self._expect('FOR')
        var = self._expect('ID')[1]
        self._expect('ASSIGN')
        start_val = self._parse_expression()
        self._expect('TO')
        end_val = self._parse_expression()
        step_val = 1.0
        if self._current_token() and self._current_token()[0] == 'STEP':
            self._next_token()
            step_val = self._parse_expression()
        
        self.variables[var] = start_val
        body_start_index = self.token_index

        try:
            while True:
                current_val = self.variables.get(var)
                
                if (step_val > 0 and current_val > end_val) or \
                   (step_val < 0 and current_val < end_val):
                    # --- Normal Completion Path ---
                    self.token_index = body_start_index
                    self._skip_block('FOR', 'NEXT')
                    
                    # --- START OF FIX ---
                    # _skip_block leaves us ON the token after NEXT. Consume it.
                    if self._current_token() and self._current_token()[0] == 'ID':
                        self._next_token()
                    # --- END OF FIX ---
                    return

                # --- Execute One Iteration ---
                self.token_index = body_start_index
                if self._current_token() and self._current_token()[0] == 'NEWLINE':
                    self._next_token()
                
                self.run_block(end_tokens={'NEXT'})
                
                self._expect('NEXT')
                if self._current_token() and self._current_token()[0] == 'ID':
                    self._next_token()
                
                self.variables[var] += step_val

        except LoopExit as e:
            if e.args[0] == 'FOR':
                # --- EXIT FOR Path ---
                self._skip_block('FOR', 'NEXT')
                if self._current_token() and self._current_token()[0] == 'ID':
                    self._next_token()
                return
            else:
                raise e
                
    def _parse_load_excel_statement(self):
        self._expect('LOAD')
        self._expect('EXCEL')

        excel_filename = self._parse_expression()
        destination_mode, destination_target, db_mode = None, None, None

        if self._current_token() and self._current_token()[0] == 'CREATE':
            destination_mode = 'CREATE_TABLE'
            self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE': self._next_token()
            destination_target = self._parse_table_name()
        elif self._current_token() and self._current_token()[0] == 'INTO':
            destination_mode = 'INTO_TABLE'
            self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE': self._next_token()
            destination_target = self._parse_table_name()
            if self._current_token() and self._current_token()[0] in ['APPEND', 'REPLACE']:
                db_mode = self._current_token()[1]
                self._next_token()
            else:
                self._error("Expected APPEND or REPLACE for INTO TABLE clause.")
        else: self._error("Expected CREATE TABLE, INTO TABLE clause.")

        options = {'header': True, 'sheetname': None, 'sheetindex': 0, 'batchsize': 10000,
                   'limit': None, 'fields': '', 'transform': '', 'format': 'CSV'}
        if self._current_token() and self._current_token()[0] == 'OPTIONS':
            self._next_token(); options_str = self._parse_expression(); temp_options = {}
            key_matches = list(re.finditer(r'\b(\w+)=', options_str))
            for i, match in enumerate(key_matches):
                key, start_pos = match.group(1).lower(), match.end()
                end_pos = key_matches[i+1].start() if i + 1 < len(key_matches) else len(options_str)
                value = options_str[start_pos:end_pos].strip().strip('"')
                temp_options[key] = value
            for key, value in temp_options.items():
                if key == 'header': options['header'] = value.lower() in ['true', '1', 'y']
                elif key in ['sheetindex', 'batchsize', 'limit']: options[key] = int(value)
                else: options[key] = value

        try:
            workbook = xlrd3.open_workbook(excel_filename)
            sheet = None
            if options['sheetname']:
                target_sheet_name = options['sheetname'].lower()
                sheet_names_lower = [name.lower() for name in workbook.sheet_names()]
                if target_sheet_name in sheet_names_lower:
                    sheet = workbook.sheet_by_index(sheet_names_lower.index(target_sheet_name))
                else: self._error(f"No sheet named '{options['sheetname']}'.")
            else: sheet = workbook.sheet_by_index(options['sheetindex'])

            start_row = 0
            original_headers = [str(cell.value) for cell in sheet.row(0)] if options['header'] else [f"Field_{i+1}" for i in range(sheet.ncols)]
            if options['header']: start_row = 1
            
            final_headers, column_map = original_headers, list(range(len(original_headers)))
            
            if destination_mode in ['CREATE_TABLE', 'INTO_TABLE']:
                cursor = self.db_cursor
                if destination_mode == 'CREATE_TABLE':
                    cols_def = ', '.join([f'[{h}] TEXT' for h in final_headers])
                    cursor.execute(f'DROP TABLE IF EXISTS [{destination_target}];')
                    cursor.execute(f'CREATE TABLE [{destination_target}] ({cols_def});')
                if db_mode == 'REPLACE': cursor.execute(f'DELETE FROM [{destination_target}];')

                placeholders = ', '.join(['?'] * len(final_headers))
                quoted_headers = ', '.join([f'[{h}]' for h in final_headers])
                insert_sql = f'INSERT INTO [{destination_target}] ({quoted_headers}) VALUES ({placeholders});'
                
                batch, total_rows_processed = [], 0
                limit = options.get('limit')
                
                self.db_connection.execute('BEGIN TRANSACTION;')
                try:
                    for row_idx in range(start_row, sheet.nrows):
                        if limit is not None and total_rows_processed >= limit: break
                        raw_row = [sheet.cell_value(row_idx, col_idx) for col_idx in column_map]
                        batch.append(raw_row)
                        total_rows_processed += 1
                        if len(batch) >= options['batchsize']:
                            cursor.executemany(insert_sql, batch); batch = []
                    
                    if batch: cursor.executemany(insert_sql, batch)
                    self.db_connection.execute('COMMIT;')
                    print(f"{total_rows_processed} records loaded into table {destination_target}")
                except Exception as e:
                    self.db_connection.execute('ROLLBACK;'); raise e

        except FileNotFoundError: self._error(f"File not found: {excel_filename}")
        except xlrd3.biffh.XLRDError as e: self._error(f"Excel file error: {e}")
        except Exception as e: self._error(f"An error occurred during Excel load: {e}")
 
    def _parse_load_json_statement(self):
        """Loads a JSON file (array of objects) into a database table with data type inference."""
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('LOAD')
        self._expect('JSON')

        # --- 1. PARSE CLAUSES ---
        json_filename = self._parse_expression()
        destination_mode = None
        destination_target = None
        db_mode = None

        if self._current_token() and self._current_token()[0] == 'CREATE':
            destination_mode = 'CREATE_TABLE'
            self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE': self._next_token()
            destination_target = self._parse_table_name()
        elif self._current_token() and self._current_token()[0] == 'INTO':
            destination_mode = 'INTO_TABLE'
            self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE': self._next_token()
            destination_target = self._parse_table_name()
            if self._current_token() and self._current_token()[0] in ['APPEND', 'REPLACE']:
                db_mode = self._current_token()[1]
                self._next_token()
            else:
                self._error("Expected APPEND or REPLACE for INTO TABLE clause.")
        else:
            self._error("Expected CREATE TABLE or INTO TABLE clause.")

        options = {'batchsize': 10000}
        if self._current_token() and self._current_token()[0] == 'OPTIONS':
            self._next_token()
            options_str = self._parse_expression()
            if 'batchsize=' in options_str:
                options['batchsize'] = int(options_str.split('=')[1])

        # --- 2. READ AND PROCESS DATA ---
        try:
            with open(json_filename, 'r', encoding='utf-8') as infile:
                data = json.load(infile)

            if isinstance(data, dict): data = [data] # Allow a single object as well as an array
            if not isinstance(data, list): self._error("JSON file must contain an array or a single object."); return
            if not data: print("0 records loaded (JSON is empty)."); return
            
            # --- Schema Inference ---
            headers, seen_keys, col_types = [], set(), {}
            for record in data:
                if not isinstance(record, dict): self._error("Elements of the JSON array must be objects.")
                for key, value in record.items():
                    if key not in seen_keys:
                        seen_keys.add(key); headers.append(key); col_types[key] = 'INTEGER'
                    
                    current_type = col_types[key]
                    if value is None or current_type == 'TEXT': continue
                    if isinstance(value, str): col_types[key] = 'TEXT'
                    elif isinstance(value, float): col_types[key] = 'REAL'
                    elif not isinstance(value, int): col_types[key] = 'TEXT' # bool, list, dict -> TEXT
            
            # --- Database Operations ---
            cursor = self.db_cursor
            if destination_mode == 'CREATE_TABLE':
                cols_def = ', '.join([f'[{h}] {col_types[h]}' for h in headers])
                cursor.execute(f'DROP TABLE IF EXISTS [{destination_target}];')
                cursor.execute(f'CREATE TABLE [{destination_target}] ({cols_def});')

            if db_mode == 'REPLACE':
                cursor.execute(f'DELETE FROM [{destination_target}];')

            placeholders = ', '.join(['?'] * len(headers))
            quoted_headers = ', '.join([f'[{h}]' for h in headers])
            insert_sql = f'INSERT INTO [{destination_target}] ({quoted_headers}) VALUES ({placeholders});'
            
            batch_size = options['batchsize']
            total_rows_processed = 0
            
            self.db_connection.execute('BEGIN TRANSACTION;')
            try:
                batch = []
                for record in data:
                    # Convert dict/list values to JSON strings for storage
                    row = [json.dumps(record.get(h)) if isinstance(record.get(h), (dict, list)) else record.get(h) for h in headers]
                    batch.append(row)
                    total_rows_processed += 1
                    if len(batch) >= batch_size:
                        cursor.executemany(insert_sql, batch); batch = []
                
                if batch: cursor.executemany(insert_sql, batch)
                self.db_connection.execute('COMMIT;')
                print(f"{total_rows_processed} records loaded into table {destination_target}")

            except Exception as e:
                self.db_connection.execute('ROLLBACK;'); raise e

        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {json_filename}")
        except json.JSONDecodeError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, f"JSON parsing error: {e}"
            self._error(f"JSON parsing error: {e}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, f"An error occurred during JSON load: {e}"
            self._error(f"An error occurred during JSON load: {e}")
            
    def _parse_for_each_statement(self):
        self._expect('FOR EACH')
        key_var = self._expect('ID')[1]
        self._expect('IN')
        self._expect('HASH')
        hash_var_name = self._expect('ID')[1]
        if hash_var_name not in self.variables or not isinstance(self.variables[hash_var_name], dict):
            self._error(f"'{hash_var_name}' is not a hash.")

        keys_to_iterate = list(self.variables[hash_var_name].keys())
        body_start_index = self.token_index
        original_value = self.variables.get(key_var)

        try:
            # If the hash is empty, just skip the whole block.
            if not keys_to_iterate:
                self.token_index = body_start_index
                self._skip_block('FOR EACH', 'NEXT')
                return

            for key in keys_to_iterate:
                self.variables[key_var] = key
                
                # Rewind and execute the loop body for this iteration.
                self.token_index = body_start_index
                if self._current_token() and self._current_token()[0] == 'NEWLINE': self._next_token()
                
                self.run_block(end_tokens={'NEXT'})
                
                # After each iteration, consume the NEXT token.
                self._expect('NEXT')
                if self._current_token() and self._current_token()[0] == 'ID':
                    self._next_token() # Consume optional variable

        except LoopExit as e:
            if e.args[0] == 'FOR':
                # An EXIT FOR was hit. Find the matching NEXT to clean up.
                self._skip_block('FOR EACH', 'NEXT')
            else:
                raise e
        finally:
            # Restore the original value of the loop variable.
            if original_value is not None:
                self.variables[key_var] = original_value
            elif key_var in self.variables:
                del self.variables[key_var]

    def _parse_for_in_sql_loop(self):
        start_index = self.token_index
        self._expect('FOR')
        loop_var_name = self._expect('ID')[1]
        self._expect('IN')
        sql_query = self._extract_sql_from_parens()
        
        results = self._execute_sql(sql_query, is_query=True)
        loop_body_start_index = self.token_index
        original_value = self.variables.get(loop_var_name)
        
        try:
            # If the query returns no rows, just skip the loop body entirely.
            if not results:
                self.token_index = loop_body_start_index
                self._skip_block('FOR', 'NEXT')
                return

            column_names = [desc[0].upper() for desc in self.db_cursor.description] if self.db_cursor.description else []
            
            row_number = 0
            for row in results:
                row_number += 1
                self.variables['RECNO'] = float(row_number)
                # Set up the loop variable for this iteration
                record_hash = {}
                for i, cell_value in enumerate(row):
                    final_value = cell_value if cell_value is not None else ""
                    record_hash[str(i + 1)] = final_value
                    if i < len(column_names):
                        record_hash[column_names[i]] = final_value
                self.variables[loop_var_name] = record_hash
                
                # Rewind and execute the loop body for this iteration
                self.token_index = loop_body_start_index
                if self._current_token() and self._current_token()[0] == 'NEWLINE': self._next_token()
                
                self.run_block(end_tokens={'NEXT'})
                
                # After each iteration, we must consume the NEXT token.
                self._expect('NEXT')
                # Also consume the optional loop variable (e.g., NEXT rec)
                if self._current_token() and self._current_token()[0] == 'ID':
                    self._next_token()

            # After the last iteration, the parser is already in the correct position.

        except LoopExit as e:
            if e.args[0] == 'FOR':
                # An EXIT FOR was hit. Find the matching NEXT to clean up.
                self._skip_block('FOR', 'NEXT')
            else:
                # An EXIT for a different loop type (e.g., WHILE) was hit. Re-raise it.
                raise e
        finally:
            # Restore the original value of the loop variable.
            if original_value is not None:
                self.variables[loop_var_name] = original_value
            elif loop_var_name in self.variables:
                del self.variables[loop_var_name]
            if 'RECNO' in self.variables:
                del self.variables['RECNO']
                
    def _parse_for_in_json_loop(self):
        self._expect('FOR')
        loop_var_name = self._expect('ID')[1]
        self._expect('IN')
        self._expect('JSON')
        
        # The filename is expected inside parentheses, e.g., JSON("my_data.json")
        self._expect('LPAREN')
        filename = self._parse_expression()
        self._expect('RPAREN')
        
        if not isinstance(filename, str):
            self._error("FOR...IN JSON requires a string filename.")

        loop_body_start_index = self.token_index
        original_value = self.variables.get(loop_var_name)
        
        try:
            # --- Automatic File Handling ---
            with open(filename, 'r', encoding='utf-8') as infile:
                data = json.load(infile)

            # Allow both an array of objects or a single top-level object
            if isinstance(data, dict):
                data = [data]
            
            if not isinstance(data, list):
                self._error("JSON file for FOR...IN loop must contain an array of objects.")
            
            if not data:
                self.token_index = loop_body_start_index
                self._skip_block('FOR', 'NEXT') # JSON array is empty, skip the loop.
                return
            row_number = 0
            # --- Loop Execution ---
            for record in data:
                row_number += 1
                self.variables['RECNO'] = float(row_number)
                # Convert the Python dict to a DbBasic HASH
                record_hash = self._python_to_basic_data(record)
                self.variables[loop_var_name] = record_hash
                
                # Rewind and execute the loop body for this iteration
                self.token_index = loop_body_start_index
                if self._current_token() and self._current_token()[0] == 'NEWLINE': self._next_token()
                
                self.run_block(end_tokens={'NEXT'})
                
                # After each iteration, consume the NEXT token.
                self._expect('NEXT')
                if self._current_token() and self._current_token()[0] == 'ID':
                    self._next_token()

        except FileNotFoundError:
            self._error(f"File not found for JSON loop: {filename}")
        except json.JSONDecodeError as e:
            self._error(f"Invalid JSON in file '{filename}': {e}")
        except LoopExit as e:
            if e.args[0] == 'FOR':
                # An EXIT FOR was hit. Find the matching NEXT to clean up.
                self._skip_block('FOR', 'NEXT')
            else:
                raise e
        finally:
            # Restore the original value of the loop variable.
            if original_value is not None:
                self.variables[loop_var_name] = original_value
            elif loop_var_name in self.variables:
                del self.variables[loop_var_name]
            if 'RECNO' in self.variables:
                del self.variables['RECNO']            

    def _parse_for_in_jsonl_loop(self):
        """Parses and executes a FOR...IN JSONL(...) loop."""
        self._expect('FOR')
        loop_var_name = self._expect('ID')[1]
        self._expect('IN')
        self._expect('JSONL')
        
        self._expect('LPAREN')
        filename = self._parse_expression()
        self._expect('RPAREN')
        
        if not isinstance(filename, str):
            self._error("FOR...IN JSONL requires a string filename.")

        loop_body_start_index = self.token_index
        original_value = self.variables.get(loop_var_name)
        row_number = 0
        try:
            with open(filename, 'r', encoding='utf-8') as infile:
                # Iterate over each line in the JSONL file
                for line in infile:
                    row_number += 1
                    self.variables['RECNO'] = float(row_number)
                    line = line.strip()
                    if not line:
                        continue # Skip empty lines

                    # Parse the single line of JSON
                    record = json.loads(line)
                    
                    # Convert the Python dict to a DbBasic HASH
                    record_hash = self._python_to_basic_data(record)
                    self.variables[loop_var_name] = record_hash
                    
                    # Rewind and execute the loop body for this iteration
                    self.token_index = loop_body_start_index
                    if self._current_token() and self._current_token()[0] == 'NEWLINE': self._next_token()
                    
                    self.run_block(end_tokens={'NEXT'})
                    
                    # After each iteration, consume the NEXT token.
                    self._expect('NEXT')
                    if self._current_token() and self._current_token()[0] == 'ID':
                        self._next_token()

        except FileNotFoundError:
            self._error(f"File not found for JSONL loop: {filename}")
        except json.JSONDecodeError as e:
            self._error(f"Invalid JSON in line of file '{filename}': {e}")
        except LoopExit as e:
            if e.args[0] == 'FOR':
                # An EXIT FOR was hit. Find the matching NEXT to clean up.
                self._skip_block('FOR', 'NEXT')
            else:
                raise e
        finally:
            # Restore the original value of the loop variable.
            if original_value is not None:
                self.variables[loop_var_name] = original_value
            elif loop_var_name in self.variables:
                del self.variables[loop_var_name]
            if 'RECNO' in self.variables:
                del self.variables['RECNO']
                
    def _parse_for_in_csv_loop(self):
        self._expect('FOR')
        loop_var_name = self._expect('ID')[1]
        self._expect('IN')
        self._expect('CSV')
        filename = self._parse_expression()
        if not isinstance(filename, str):
            self._error("FOR...IN CSV requires a string filename.")
        
        options = {'header': False}
        if self._current_token() and self._current_token()[0] == 'OPTIONS':
            self._next_token()
            options_str = self._parse_expression()
            if 'header=true' in options_str.lower():
                options['header'] = True
        
        loop_body_start_index = self.token_index
        original_value = self.variables.get(loop_var_name)
        
        try:
            with open(filename, 'r', newline='', encoding='utf-8') as infile:
                csv_reader = csv.reader(infile)
                
                headers = []
                if options['header']:
                    try:
                        raw_headers = next(csv_reader)
                        if self.hash_keys_mode == 'IGNORE_CASE':
                            headers = [re.sub(r'[^a-zA-Z0-9_]', '', h).strip().upper() for h in raw_headers]
                        else:
                            headers = [re.sub(r'[^a-zA-Z0-9_]', '', h).strip() for h in raw_headers]
                    except StopIteration:
                        self._skip_block('FOR', 'NEXT')
                        return

                all_rows = list(csv_reader)
                if not all_rows:
                    self.token_index = loop_body_start_index
                    self._skip_block('FOR', 'NEXT')
                    return
            row_number = 1
            for row in all_rows:
                row_number += 1
                self.variables['RECNO'] = float(row_number)
                record_hash = {}
                for i, cell_value in enumerate(row):
                    record_hash[str(i + 1)] = cell_value
                    if headers and i < len(headers):
                        record_hash[headers[i]] = cell_value
                self.variables[loop_var_name] = record_hash
                
                # Rewind and execute the loop body for this iteration
                self.token_index = loop_body_start_index
                if self._current_token() and self._current_token()[0] == 'NEWLINE': self._next_token()
                
                self.run_block(end_tokens={'NEXT'})
                
                # After each iteration, consume the NEXT token.
                self._expect('NEXT')
                if self._current_token() and self._current_token()[0] == 'ID':
                    self._next_token()

        except LoopExit as e:
            if e.args[0] == 'FOR':
                # An EXIT FOR was hit. Find the matching NEXT to clean up.
                self._skip_block('FOR', 'NEXT')
            else:
                raise e
        finally:
            if original_value is not None:
                self.variables[loop_var_name] = original_value
            elif loop_var_name in self.variables:
                del self.variables[loop_var_name]
            if 'RECNO' in self.variables:
                del self.variables['RECNO']
        
    def _parse_dim_statement(self):
        self._expect('DIM'); var_name = self._expect('ID')[1]
        if self._current_token() and self._current_token()[0] == 'AS':
            self._next_token(); type_token = self._current_token()
            if not type_token or type_token[0] not in ['HASH', 'ARRAY']: self._error(f"Expected HASH or ARRAY after AS")
            self._next_token()
            if type_token[0] == 'HASH': self.variables[var_name] = {}
            elif type_token[0] == 'ARRAY': self.variables[var_name] = []
        elif self._current_token() and self._current_token()[0] == 'LPAREN':
            self._expect('LPAREN')
            if self._current_token() and self._current_token()[0] == 'RPAREN': self._expect('RPAREN'); self.variables[var_name] = []
            else:
                size = int(self._parse_expression()); self._expect('RPAREN')
                default_value = "" if var_name.endswith('$') else 0.0
                self.variables[var_name] = [default_value] * (size + 1)
        else: self._error(f"Invalid DIM statement for '{var_name}'.")
            
    def _parse_json_statement(self):
        self._expect('PARSE'); self._expect('JSON')
        json_string = self._parse_expression()
        self._expect('INTO'); var_name = self._expect('ID')[1]
        if self._current_token() and self._current_token()[0] == 'LPAREN': self._next_token(); self._expect('RPAREN')
        if var_name not in self.variables: self._error(f"Target variable '{var_name}' must be dimensioned.")
        try: parsed_data = json.loads(json_string)
        except json.JSONDecodeError as e: self._error(f"Invalid JSON string: {e}")
        self.variables[var_name] = self._python_to_basic_data(parsed_data)
        
    def _parse_redim_statement(self):
        self._expect('REDIM'); var_name = self._expect('ID')[1]
        if var_name not in self.variables or not isinstance(self.variables.get(var_name), list): self._error(f"'{var_name}' not dimensioned for REDIM.")
        self._expect('LPAREN'); size = int(self._parse_expression()); self._expect('RPAREN')
        default_value = "" if var_name.endswith('$') else 0.0
        self.variables[var_name] = [default_value] * (size + 1)
        
    def _parse_assignment_statement(self):
        if self._current_token()[0] == 'LET': self._next_token()
        var_name = self._expect('ID')[1]
        if self._current_token() and self._current_token()[0] == 'LPAREN':
            self._expect('LPAREN'); key_or_index_expr = self._parse_expression(); self._expect('RPAREN'); self._expect('ASSIGN'); value = self._parse_expression()
            if var_name not in self.variables or not isinstance(self.variables.get(var_name), (list, dict)): self._error(f"'{var_name}' is not an array or hash.")
            collection = self.variables[var_name]
            if isinstance(collection, list):
                index = int(key_or_index_expr)
                if index >= len(collection):
                    default_value = "" if var_name.endswith('$') else 0.0
                    collection.extend([default_value] * (index - len(collection) + 1))
                collection[index] = value
            elif isinstance(collection, dict): 
                normalized_key = self._normalize_hash_key(key_or_index_expr)
                collection[normalized_key] = value
        elif self._current_token() and self._current_token()[0] == 'DOT':
            self._next_token(); 
            key_token = self._expect('ID'); 
            base_key = key_token[1].rstrip('$')  # Strip $ before normalizing
            #print("DEBUG1",base_key)
            key_name = self._normalize_hash_key(base_key) if self.hash_keys_mode == 'IGNORE_CASE' else base_key 
            #print("DEBUG2",key_name)
            self._expect('ASSIGN'); 
            value = self._parse_expression()
            if var_name not in self.variables or not isinstance(self.variables.get(var_name), dict): 
                self._error(f"'{var_name}' is not a HASH for dot notation.")
            self.variables[var_name][key_name] = value
        elif self._current_token() and self._current_token()[0] == 'ASSIGN':
            self._expect('ASSIGN'); value = self._parse_expression()
            if value is None: self.variables[var_name] = "" if var_name.endswith('$') else 0.0
            else: self.variables[var_name] = value
        else: self._error(f"Invalid assignment statement for '{var_name}'")

    def _parse_analyze_csv_statement(self):
        """Parses and executes ANALYZE CSV, providing a detailed report on the file."""
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('ANALYZE CSV')
        filename = self._parse_expression()
        
        options = {'header': 'auto', 'delimiter': 'auto', 'constraints': '', 'limit': None}
        if self._current_token() and self._current_token()[0] == 'OPTIONS':
            self._next_token()
            options_str = self._parse_expression()
            key_matches = list(re.finditer(r'\b(\w+)=', options_str))
            for i, match in enumerate(key_matches):
                key = match.group(1).lower()
                start_pos = match.end()
                end_pos = key_matches[i+1].start() if i + 1 < len(key_matches) else len(options_str)
                value = options_str[start_pos:end_pos].strip().strip('"')
                
                if key == 'header':
                    if value.lower() in ['true', '1', 'y']: options['header'] = True
                    elif value.lower() in ['false', '0', 'n']: options['header'] = False
                elif key == 'delimiter': options['delimiter'] = value
                elif key == 'constraints': options['constraints'] = value
                elif key == 'limit': options['limit'] = int(value) 

        into_hash_name = None
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token()
            into_hash_name = self._expect('ID')[1]
            if into_hash_name not in self.variables or not isinstance(self.variables.get(into_hash_name), dict):
                 self._error(f"'{into_hash_name}' is not a dimensioned hash for use with ANALYZE INTO.")

        report = {}
        try:
            # --- Start of new analysis logic ---
            date_formats_to_try = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y%m%d", "%Y-%m-%dT%H:%M:%S"]
            logical_trues = {'true', 't', 'y', 'yes', '1'}
            logical_falses = {'false', 'f', 'n', 'no', '0'}

            with open(filename, 'r', newline='', encoding='utf-8', errors='replace') as infile:
                sample = infile.read(8192)
                infile.seek(0)
                
                sniffer = csv.Sniffer()
                if options['delimiter'] == 'auto':
                    try: report['DELIMITER'] = sniffer.sniff(sample).delimiter
                    except csv.Error: report['DELIMITER'] = ','
                else:
                    report['DELIMITER'] = options['delimiter']

                has_header = options['header']
                if has_header == 'auto':
                    try: has_header = sniffer.has_header(sample)
                    except csv.Error: has_header = False
                report['HEADER_ROW'] = -1.0 if has_header else 0.0
                
                reader = csv.reader(infile, delimiter=report['DELIMITER'])
                
                headers = []
                if has_header:
                    try: headers = next(reader) 
                    except StopIteration: pass
                
                record_count = 0
                field_counts = {}
                col_stats = {}

                limit = options.get('limit')
                for i, row in enumerate(reader):
                    if limit is not None and i >= limit: break
                    record_count += 1
                    num_fields = len(row)
                    field_counts[num_fields] = field_counts.get(num_fields, 0) + 1

                    if not headers and row:
                        headers = [f"Field_{j+1}" for j in range(num_fields)]
                    
                    for j, field in enumerate(row):
                        if j >= len(headers): continue
                        h = headers[j]
                        if h not in col_stats:
                            col_stats[h] = {
                                'MIN_LEN': None, 'MAX_LEN': 0, 'EMPTY_COUNT': 0,  # Changed to uppercase
                                'INTEGER_COUNT': 0, 'FLOAT_COUNT': 0, 'DATE_COUNT': 0,  # Changed to uppercase
                                'LOGICAL_COUNT': 0, 'STRING_COUNT': 0, 'MAX_DECIMALS': 0,  # Changed to uppercase
                                'MIN_VALUE': None, 'MAX_VALUE': None 
                            }

                        field_len = len(field)
                        if col_stats[h]['MIN_LEN'] is None or field_len < col_stats[h]['MIN_LEN']: col_stats[h]['MIN_LEN'] = field_len
                        if field_len > col_stats[h]['MAX_LEN']: col_stats[h]['MAX_LEN'] = field_len

                        # Trim whitespace first
                        field = field.strip()

                        if not field:
                            col_stats[h]['EMPTY_COUNT'] += 1
                            continue

                        # --- NEW: Data Cleaning for Type Analysis ---
                        cleaned_field = field.replace('$', '').replace(',', '')
                        
                        # If cleaning results in an empty string (e.g., field was just "$"), count as empty
                        if not cleaned_field:
                            col_stats[h]['EMPTY_COUNT'] += 1
                            continue
                        
                        # --- End of New Logic ---


                        # Type checking logic (now uses cleaned_field)
                        try:
                            int_val = int(cleaned_field)
                            col_stats[h]['INTEGER_COUNT'] += 1
                            if col_stats[h]['MIN_VALUE'] is None or int_val < col_stats[h]['MIN_VALUE']: 
                                col_stats[h]['MIN_VALUE'] = int_val
                            if col_stats[h]['MAX_VALUE'] is None or int_val > col_stats[h]['MAX_VALUE']: 
                                col_stats[h]['MAX_VALUE'] = int_val
                            continue
                        except (ValueError, TypeError): pass

                        try:
                            float_val = float(cleaned_field)
                            col_stats[h]['FLOAT_COUNT'] += 1
                            if '.' in cleaned_field:
                                decimals = len(cleaned_field.split('.')[1])
                                if decimals > col_stats[h]['MAX_DECIMALS']: col_stats[h]['MAX_DECIMALS'] = decimals
                            if col_stats[h]['MIN_VALUE'] is None or float_val < col_stats[h]['MIN_VALUE']: 
                                col_stats[h]['MIN_VALUE'] = float_val
                            if col_stats[h]['MAX_VALUE'] is None or float_val > col_stats[h]['MAX_VALUE']: 
                                col_stats[h]['MAX_VALUE'] = float_val
                            continue
                        except (ValueError, TypeError): pass

                        lower_field = field.lower()
                        if lower_field in logical_trues or lower_field in logical_falses:
                            col_stats[h]['LOGICAL_COUNT'] += 1
                            continue
                        
                        is_a_date = False
                        for fmt in date_formats_to_try:
                            try:
                                date_val = datetime.strptime(field, fmt)
                                col_stats[h]['DATE_COUNT'] += 1
                                if col_stats[h]['MIN_VALUE'] is None or date_val < col_stats[h]['MIN_VALUE']: col_stats[h]['MIN_VALUE'] = date_val
                                if col_stats[h]['MAX_VALUE'] is None or date_val > col_stats[h]['MAX_VALUE']: col_stats[h]['MAX_VALUE'] = date_val
                                is_a_date = True
                                break
                            except (ValueError, TypeError): pass
                        if is_a_date: continue
                        
                        col_stats[h]['STRING_COUNT'] += 1
                        # Add min/max tracking for strings (alphabetical ordering)
                        if col_stats[h]['MIN_VALUE'] is None or field < col_stats[h]['MIN_VALUE']: 
                            col_stats[h]['MIN_VALUE'] = field
                        if col_stats[h]['MAX_VALUE'] is None or field > col_stats[h]['MAX_VALUE']: 
                            col_stats[h]['MAX_VALUE'] = field
                        

                # Post-processing to suggest SQL types
                for h, stats in col_stats.items():
                    total_data_points = record_count - stats['EMPTY_COUNT']
                    if total_data_points == 0:
                        stats['SUGGESTED_DATA_TYPE'] = 'TEXT'
                    elif stats['STRING_COUNT'] > 0:
                        stats['SUGGESTED_DATA_TYPE'] = 'TEXT'
                    elif stats['DATE_COUNT'] > 0 and stats['INTEGER_COUNT'] == 0 and stats['FLOAT_COUNT'] == 0:
                        stats['SUGGESTED_DATA_TYPE'] = 'DATE' # Or TEXT for safety
                    elif stats['FLOAT_COUNT'] > 0:
                        stats['SUGGESTED_DATA_TYPE'] = 'REAL'
                    elif stats['INTEGER_COUNT'] > 0 or stats['LOGICAL_COUNT'] > 0:
                        stats['SUGGESTED_DATA_TYPE'] = 'INTEGER'
                    else:
                        stats['SUGGESTED_DATA_TYPE'] = 'TEXT'
                    # Convert datetimes to strings for the report
                    if isinstance(stats['MIN_VALUE'], datetime): stats['MIN_VALUE'] = stats['MIN_VALUE'].isoformat()
                    if isinstance(stats['MAX_VALUE'], datetime): stats['MAX_VALUE'] = stats['MAX_VALUE'].isoformat()


                report['HEADERS'] = headers 
                report['DATA_RECORDS'] = record_count
                report['FIELD_COUNT_DISTRIBUTION'] = self._python_to_basic_data(field_counts)
                report['COLUMN_STATISTICS'] = self._python_to_basic_data(col_stats)

            if into_hash_name:
                self.variables[into_hash_name] = self._python_to_basic_data(report)
            else:
                print(f"--- CSV Analysis Report for: {filename} ---")
                print(f"  Delimiter Detected : '{report.get('DELIMITER', 'N/A')}'")
                print(f"  Header Row Detected: {'Yes' if report.get('HEADER_ROW') else 'No'}")
                print(f"  Total Data Records : {report.get('DATA_RECORDS', 0)}")
                print(f"  Headers (in order) : {', '.join(report.get('HEADERS', []))}")
                
                if 'FIELD_COUNT_DISTRIBUTION' in report and report['FIELD_COUNT_DISTRIBUTION']:
                    print("  Field Count Distribution:")
                    for count, num_rows in report['FIELD_COUNT_DISTRIBUTION'].items():
                        print(f"    - {int(num_rows)} record(s) with {count} field(s)")

                if 'COLUMN_STATISTICS' in report and report['COLUMN_STATISTICS']:
                    print("\n  Column Statistics:")
                    for col_name in headers:
                        stats = report['COLUMN_STATISTICS'].get(col_name, {})
                        print(f"    - [{col_name}] -> Suggested Type: {stats.get('SUGGESTED_DATA_TYPE', 'N/A')}")
                        print(f"      Counts (Total: {record_count}):")
                        type_counts = []
                        if stats.get('INTEGER_COUNT', 0) > 0: type_counts.append(f"Int: {int(stats['INTEGER_COUNT'])}")
                        if stats.get('FLOAT_COUNT', 0) > 0: type_counts.append(f"Float: {int(stats['FLOAT_COUNT'])}")
                        if stats.get('DATE_COUNT', 0) > 0: type_counts.append(f"Date: {int(stats['DATE_COUNT'])}")
                        if stats.get('LOGICAL_COUNT', 0) > 0: type_counts.append(f"Logical: {int(stats['LOGICAL_COUNT'])}")
                        if stats.get('STRING_COUNT', 0) > 0: type_counts.append(f"String: {int(stats['STRING_COUNT'])}")
                        if stats.get('EMPTY_COUNT', 0) > 0: type_counts.append(f"Empty: {int(stats['EMPTY_COUNT'])}")
                        print(f"        {', '.join(type_counts)}")
                        print(f"      Length (Min/Max) : {stats.get('MIN_LEN', 0)} / {stats.get('MAX_LEN', 0)}")
                        if stats.get('FLOAT_COUNT', 0) > 0:
                            print(f"      Max Decimals     : {int(stats.get('MAX_DECIMALS', 0))}")
                        if stats.get('MIN_VALUE') is not None:
                             print(f"      Value Range      : {stats.get('MIN_VALUE')} to {stats.get('MAX_VALUE')}")
                        #print("DEBUG:",stats)

        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {filename}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during CSV analysis: {e}")

    def _guess_fixed_width_columns(self, lines, space_threshold=0.90):
        """Analyzes lines of text to guess fixed-width column breaks."""
        if not lines:
            return []
        
        # Pad lines to the same length for consistent column analysis
        max_len = max(len(line.rstrip('\n\r')) for line in lines) if lines else 0
        if max_len == 0:
            return []
            
        padded_lines = [line.rstrip('\n\r').ljust(max_len) for line in lines]
        num_lines = len(padded_lines)
        
        # Tally spaces in each column position
        space_counts = [0] * max_len
        for line in padded_lines:
            for i, char in enumerate(line):
                if char == ' ':
                    space_counts[i] += 1
        
        # A column is a separator if it's mostly spaces
        is_separator = [(count / num_lines) > space_threshold for count in space_counts]
        
        # Find field boundaries based on transitions from data to separators
        definitions = []
        in_field = False
        start_pos = 0
        field_num = 1
        
        for i in range(max_len):
            is_last_char = (i == max_len - 1)
            # Start of a new field is a non-separator column when we aren't in a field
            if not is_separator[i] and not in_field:
                in_field = True
                start_pos = i
            # End of a field is a separator column when we are in a field, or end of line
            elif in_field and (is_separator[i] or is_last_char):
                end_pos = i if is_separator[i] else i + 1
                definitions.append({
                    'name': f'Field_{field_num}',
                    'start': start_pos,
                    'end': end_pos,
                    'width': end_pos - start_pos
                })
                field_num += 1
                in_field = False
        
        return definitions
        
    def _parse_analyze_fixed_statement(self):
        """
        Parse and execute ANALYZE FIXED. FIELDS is optional.
        Guesses columns based on a 1000-line sample, then analyzes the full file via streaming.
        """
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('ANALYZE FIXED')
        filename = self._parse_expression()
        
        field_definitions = []
        
        # --- Step 1: Determine field definitions (manually or by guessing from a sample) ---
        if self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'FIELDS':
            self._next_token()
            fields_spec = self._parse_expression()
            for field_def in fields_spec.split(','):
                # (Manual parsing logic is the same)
                parts = field_def.strip().split(':')
                if len(parts) != 2: self._error(f"Invalid field specification: {field_def}")
                field_name, positions = parts
                pos_parts = positions.split('-')
                if len(pos_parts) != 2: self._error(f"Invalid position specification: {positions}")
                try:
                    start_pos = int(pos_parts[0].strip()) - 1
                    end_pos = int(pos_parts[1].strip())
                    field_definitions.append({
                        'name': field_name.strip(), 'start': start_pos, 'end': end_pos, 'width': end_pos - start_pos
                    })
                except ValueError:
                    self._error(f"Invalid position numbers: {positions}")
        else:
            # Auto-detect fields from a 1000-line sample
            sample_lines = []
            try:
                with open(filename, 'r', encoding='utf-8', errors='replace') as infile:
                    for i, line in enumerate(infile):
                        if i >= 1000:
                            break
                        sample_lines.append(line)
            except FileNotFoundError as e:
                self._error(f"File not found: {filename}")
            print(f"Notice: FIELDS clause not provided; guessing column layout for '{filename}'.", file=sys.stderr)
            field_definitions = self._guess_fixed_width_columns(sample_lines)
            if not field_definitions:
                print(f"Warning: Could not auto-detect any field columns in {filename}.")

        into_hash_name = None
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token()
            into_hash_name = self._expect('ID')[1]
            if into_hash_name not in self.variables or not isinstance(self.variables.get(into_hash_name), dict):
                self._error(f"'{into_hash_name}' is not a dimensioned hash.")

        # --- Step 2: Perform full analysis by streaming the entire file ---
        report = {}
        try:
            record_count = 0
            line_length_stats = {}
            first_two_lines = []
            field_stats = {field['name']: {
                'START_POS': field['start'],
                'END_POS': field['end'],
                'DEFINED_WIDTH': field['width'], 'MIN_LEN': None, 'MAX_LEN': 0,
                'EMPTY_COUNT': 0, 'SAMPLE_VALUES': []
            } for field in field_definitions}

            with open(filename, 'r', encoding='utf-8', errors='replace') as infile:
                for line in infile:
                    # Capture first two lines for the report sample
                    if record_count < 2:
                        first_two_lines.append(line)
                    
                    record_count += 1
                    line = line.rstrip('\n\r')
                    line_len = len(line)
                    line_length_stats[line_len] = line_length_stats.get(line_len, 0) + 1
                    
                    for field in field_definitions:
                        stats = field_stats[field['name']]
                        value = line[field['start']:field['end']].rstrip() if field['start'] < line_len else ""
                        
                        if not value:
                            stats['EMPTY_COUNT'] += 1
                        else:
                            value_len = len(value)
                            if stats['MIN_LEN'] is None or value_len < stats['MIN_LEN']:
                                stats['MIN_LEN'] = value_len
                            if value_len > stats['MAX_LEN']:
                                stats['MAX_LEN'] = value_len
                            if len(stats['SAMPLE_VALUES']) < 3 and value not in stats['SAMPLE_VALUES']:
                                stats['SAMPLE_VALUES'].append(value)
            
            # Build the final report
            report['FILENAME'] = filename
            report['TOTAL_RECORDS'] = record_count
            report['LINE_LENGTH_DISTRIBUTION'] = self._python_to_basic_data(line_length_stats)
            report['FIELD_ANALYSIS'] = self._python_to_basic_data(field_stats)
            report['FIELD_COUNT'] = len(field_definitions)

            if into_hash_name:
                self.variables[into_hash_name] = self._python_to_basic_data(report)
            else:
                # The printing logic now uses 'first_two_lines'
                print(f"--- Fixed-Width Analysis Report for: {filename} ---")
                print(f"  Total Records: {report.get('TOTAL_RECORDS', 0)}")
                print(f"  Defined Fields: {report.get('FIELD_COUNT', 0)}")
                
                line_lengths = report.get('LINE_LENGTH_DISTRIBUTION', {})
                max_line_length = int(max(line_lengths.keys())) if line_lengths else 0
                print(f"  Maximum Line Length: {max_line_length}")
                
                if max_line_length > 0:
                    print("\nPosition Reference:")
                    tens_ruler = "         "
                    for i in range(1, (max_line_length // 10) + 2):
                        tens_ruler += f"{i}         "
                    print(f"{tens_ruler[:max_line_length]}")
                    
                    units_ruler = "123456789" * ((max_line_length // 9) + 2)
                    print(f"{units_ruler[:max_line_length]}")

                    for line in first_two_lines:
                        print(line.rstrip('\n\r'))
                
                if 'FIELD_ANALYSIS' in report:
                    print("\n  Field Analysis:")
                    for field_name, stats in report['FIELD_ANALYSIS'].items():
                        print(f"    [{field_name}]:")
                        start_display = int(stats.get('START_POS', -1)) + 1
                        end_display = int(stats.get('END_POS', 0))
                        print(f"      Position Range:  {start_display}-{end_display}")
                        print(f"      Defined Width:   {stats.get('DEFINED_WIDTH', 0)}")
                        print(f"      Actual Length:   {stats.get('MIN_LEN', 'N/A')} - {stats.get('MAX_LEN', 'N/A')}")
                        print(f"      Empty Fields: {stats.get('EMPTY_COUNT', 0)}")
                        if stats.get('SAMPLE_VALUES'):
                            samples = ', '.join([f'"{v}"' for v in stats['SAMPLE_VALUES']])
                            print(f"      Sample Values: {samples}")
                if field_definitions:
                    fields_spec_parts = []
                    for field in field_definitions:
                        start_display = field['start'] + 1
                        end_display = field['end']
                        name = field['name']
                        fields_spec_parts.append(f"{name}:{start_display}-{end_display}")
                    
                    fields_spec_string = ",".join(fields_spec_parts)
                    example_command = f'LOAD FIXED "{filename}" CREATE TABLE MyTable FIELDS "{fields_spec_string}"'
                    
                    print("\n  Example LOAD Command:")
                    print(f"    {example_command}")
                    
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during fixed-width analysis: {e}")
        
        
    def _parse_form_statement(self):
        self._expect('FORM')
        form_name = self._expect('ID')[1]

        form_def = {
            "name": form_name,
            "source": None,
            "display_rows": 1, # Default to a single-record form
            "elements": [],
            "buttons": []
        }

        # --- Parse form-level attributes like DISPLAY and SOURCE ---
        parsing_attributes = True
        while parsing_attributes:
            tok = self._current_token()
            if tok and tok[0] == 'DISPLAY':
                self._next_token()
                form_def["display_rows"] = int(self._expect('NUMBER')[1])
            elif tok and tok[0] == 'SOURCE':
                self._next_token()
                form_def["source"] = {"type": "SQL", "query": self._extract_sql_from_parens()}
            elif tok and tok[0] == 'NEWLINE':
                # This is the key fix: simply consume newlines and continue the loop.
                self._next_token()
                continue
            else:
                parsing_attributes = False # No more top-level attributes found

        # Loop through the rest of the form elements (FIELD, HEADING, etc.)
        while self._current_token() and self._current_token()[0] != 'ENDFORM':
            tok = self._current_token()

            if tok[0] == 'HEADING':
                self._next_token()
                text = self._expect('STRING')[1].strip('"')
                form_def["elements"].append({"type": "HEADING", "text": text})
            
            elif tok[0] == 'TEXTBLOCK':
                self._next_token()
                text = self._expect('STRING')[1].strip('"')
                form_def["elements"].append({"type": "TEXTBLOCK", "text": text})

            elif tok[0] == 'SEPARATOR':
                self._next_token()
                form_def["elements"].append({"type": "SEPARATOR"})
            
            elif tok[0] == 'FIELD':
                self._next_token()
                field_name = self._expect('ID')[1]
                self._expect('TYPE')
                field_type = self._expect('ID')[1].upper()

                field_def = {
                    "type": "FIELD", "name": field_name, "field_type": field_type,
                    "label": field_name, "placeholder": "", "readonly": False,
                    "validations": {}
                }
                
                # --- FULL attribute parsing loop for a FIELD ---
                while self._current_token() and self._current_token()[0] not in ['NEWLINE', 'ENDFORM', 'FIELD', 'BUTTON', 'HEADING', 'SEPARATOR']:
                    attr_tok = self._current_token()
                    
                    if attr_tok[0] == 'READONLY':
                        self._next_token()
                        field_def["readonly"] = True
                    
                    elif attr_tok[0] == 'LABEL':
                        self._next_token()
                        field_def["label"] = self._expect('STRING')[1].strip('"')
                    
                    elif attr_tok[0] == 'PLACEHOLDER':
                        self._next_token()
                        field_def["placeholder"] = self._expect('STRING')[1].strip('"')

                    elif attr_tok[0] == 'REQUIRED':
                        self._next_token()
                        self._expect('MESSAGE')
                        msg = self._expect('STRING')[1].strip('"')
                        field_def["validations"]["required"] = {"message": msg}

                    elif attr_tok[0] == 'MINLENGTH':
                        self._next_token()
                        val = int(self._expect('NUMBER')[1])
                        self._expect('MESSAGE')
                        msg = self._expect('STRING')[1].strip('"')
                        field_def["validations"]["minlength"] = {"value": val, "message": msg}
                    
                    elif attr_tok[0] == 'MAXLENGTH':
                        self._next_token()
                        val = int(self._expect('NUMBER')[1])
                        self._expect('MESSAGE')
                        msg = self._expect('STRING')[1].strip('"')
                        field_def["validations"]["maxlength"] = {"value": val, "message": msg}

                    elif attr_tok[0] == 'MINVALUE':
                        self._next_token()
                        val = float(self._expect('NUMBER')[1])
                        self._expect('MESSAGE')
                        msg = self._expect('STRING')[1].strip('"')
                        field_def["validations"]["minvalue"] = {"value": val, "message": msg}

                    elif attr_tok[0] == 'PATTERN':
                        self._next_token()
                        val = self._expect('STRING')[1].strip('"')
                        self._expect('MESSAGE')
                        msg = self._expect('STRING')[1].strip('"')
                        field_def["validations"]["pattern"] = {"value": val, "message": msg}

                    elif attr_tok[0] == 'MATCHES':
                        self._next_token()
                        val = self._expect('STRING')[1].strip('"')
                        self._expect('MESSAGE')
                        msg = self._expect('STRING')[1].strip('"')
                        field_def["validations"]["matches"] = {"value": val, "message": msg}
                    
                    else:
                        self._error(f"Unexpected attribute '{attr_tok[1]}' for FIELD.")
                
                form_def["elements"].append(field_def)

            elif tok[0] == 'BUTTON':
                self._next_token()
                button_tok = self._current_token()
                if button_tok[0] == 'STRING':
                    button_name = button_tok[1].strip('"')
                else:
                    button_name = button_tok[1]
                self._next_token()
                self._expect('ACTION')
                action = self._current_token()[1].upper()
                self._next_token()
                form_def["buttons"].append({"name": button_name, "action": action})

            elif tok[0] == 'NEWLINE':
                self._next_token()

            else:
                self._error(f"Unexpected token '{tok[1]}' inside FORM definition.")

        self._expect('ENDFORM')
        
        if form_name in self.form_definitions:
            self._error(f"Duplicate FORM definition: '{form_name}'")
        
        self.form_definitions[form_name] = form_def
        print("DEBUG", form_def)
        

    def _parse_open_form_statement(self):
        self._expect('OPENFORM')
        form_name = self._expect('ID')[1]

        # --- 1. Parse optional USING clause to get the starting record ID ---
        record_id = None
        if self._current_token() and self._current_token()[0] == 'USING':
            self._next_token()
            record_id = self._parse_expression()

        if form_name not in self.form_definitions:
            self._error(f"FORM '{form_name}' is not defined.")
        
        form_def = self.form_definitions[form_name]
        
        record_ids = []
        current_index = -1
        # The view mode starts based on the form's DISPLAY attribute
        current_view_mode = 'grid' if form_def.get("display_rows", 1) > 1 else 'single'

        # If the form is data-bound, fetch the list of all IDs for navigation
        if form_def.get("source"):
            # FIX #1: Derive navigation IDs from the SOURCE query itself, assuming an 'id' column exists.
            # This respects any ordering in the user's original query.
            grid_query = form_def["source"]["query"]
            nav_query = f"SELECT id FROM ({grid_query}) AS t"
            all_ids_result = self._execute_sql(nav_query, is_query=True)
            record_ids = [row[0] for row in all_ids_result]
            
            if record_id in record_ids:
                current_index = record_ids.index(record_id)
            elif record_ids:
                current_index = 0 # Default to the first record if no ID is specified


        # --- 3. The Main Controller Loop ---
        # This loop runs the form, waits for an action, and then re-runs or exits.
        while True:
            initial_data = {}
            # Fetch data for the current record if we are in single view mode
            if current_view_mode == 'single' and current_index != -1:
                current_id = record_ids[current_index]
                self.variables['ID'] = current_id # Set bind variable for the query
                
                # FIX #2: Wrap the grid query to create a filtered query for the single view.
                # This robustly filters the full dataset down to the specific record.
                grid_query = form_def["source"]["query"]
                single_query = f"SELECT * FROM ({grid_query}) AS t WHERE id = :id"
                row_data = self._execute_sql(single_query, is_query=True)
                
                if row_data and self.db_cursor.description:
                    headers = [desc[0] for desc in self.db_cursor.description]
                    initial_data = dict(zip(headers, row_data[0]))
            # For grid view, fetch all data
            elif current_view_mode == 'grid' and form_def.get("source"):
                # This part is correct: it uses the original query for the grid.
                rows = self._execute_sql(form_def["source"]["query"], is_query=True)
                headers = [desc[0] for desc in self.db_cursor.description] if self.db_cursor.description else []
                initial_data = {"headers": headers, "rows": rows}



            # Pass navigation and view info to the TUI
            nav_info = {
                "current_mode": current_view_mode,
                "has_prev": current_index > 0,
                "has_next": current_index < len(record_ids) - 1
            }

            # Run the TUI and wait for the user to perform an action
            try:
                # Run the TUI and wait for the user to perform an action
                runner = FormRunner(form_def, initial_data, nav_info, view_mode=current_view_mode)
                results = runner.run()
                action = results.get("action")
                print(f"DEBUG: Form returned action='{action}', results={results}")
            except Exception as e:
                print(f"Form error: {e}")
                self.variables["FORM_RESULT$"] = "ERROR"
                break

            # --- 4. Handle the Action Returned from the TUI ---
            if not action or action in ["CLOSE", "CANCEL", "INSERT", "UPDATE"]:
                self.variables["FORM_RESULT$"] = action
                if action == "UPDATE":
                    print(f"INTERPRETER: Would execute UPDATE for record {results.get('id')}")
                # Any of these actions will break the loop and exit the form.
                break 
            
            elif action == "VIEW_GRID":
                current_view_mode = 'grid'

            elif action == "VIEW_SINGLE":
                current_view_mode = 'single'
                if "selected_id" in results and results["selected_id"] in record_ids:
                    current_index = record_ids.index(results["selected_id"])
            
            elif action == "NEXT_RECORD":
                if current_index < len(record_ids) - 1:
                    current_index += 1
            
            elif action == "PREV_RECORD":
                if current_index > 0:
                    current_index -= 1
            
            elif action == "FIRST_RECORD":
                if record_ids:
                    current_index = 0

            elif action == "LAST_RECORD":
                if record_ids:
                    current_index = len(record_ids) - 1
            
    def _format_bytes(self, size):
        """Helper function to format bytes into KB, MB, etc."""
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024**2:
            return f"{size/1024:.2f} KB"
        elif size < 1024**3:
            return f"{size/1024**2:.2f} MB"
        else:
            return f"{size/1024**3:.2f} GB"

    def _parse_analyze_file_statement(self):
        """Performs a detailed statistical analysis of a text file."""
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('ANALYZE FILE')
        filename = self._parse_expression()

        into_hash_name = None
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token()
            into_hash_name = self._expect('ID')[1]
            if into_hash_name not in self.variables or not isinstance(self.variables.get(into_hash_name), dict):
                 self._error(f"'{into_hash_name}' is not a dimensioned hash for use with ANALYZE INTO.")

        try:
            report = {}
            file_size = os.path.getsize(filename)
            report['FILE_SIZE_BYTES'] = file_size
            
            with open(filename, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            full_content = "".join(lines)
            total_lines = len(lines)
            empty_lines = sum(1 for line in lines if not line.strip())
            
            report['TOTAL_LINES'] = total_lines
            report['EMPTY_LINES'] = empty_lines
            report['NON_EMPTY_LINES'] = total_lines - empty_lines
            report['TOTAL_CHARACTERS'] = len(full_content)
            report['TOTAL_WORDS'] = len(full_content.split())

            if into_hash_name:
                self.variables[into_hash_name] = self._python_to_basic_data(report)
            else:
                print(f"--- File Analysis Report for: {filename} ---")
                print(f"  File Size    : {self._format_bytes(file_size)}")
                print(f"  Total Lines  : {report['TOTAL_LINES']}")
                print(f"  Empty Lines  : {report['EMPTY_LINES']}")
                print(f"  Total Chars  : {report['TOTAL_CHARACTERS']}")
                print(f"  Total Words  : {report['TOTAL_WORDS']}")

        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {filename}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during file analysis: {e}")

    def _parse_analyze_json_statement(self):
        """Parses and executes ANALYZE JSON, reporting on structural consistency."""
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('ANALYZE JSON')
        filename = self._parse_expression()

        into_hash_name = None
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token()
            into_hash_name = self._expect('ID')[1]
            if into_hash_name not in self.variables or not isinstance(self.variables.get(into_hash_name), dict):
                 self._error(f"'{into_hash_name}' is not a dimensioned hash for use with ANALYZE INTO.")

        report = {}
        try:
            with open(filename, 'r', encoding='utf-8') as infile:
                data = json.load(infile)
            
            # If the JSON is a single object, treat it as an array with one element
            if isinstance(data, dict):
                data = [data]

            if not isinstance(data, list):
                self._error("JSON file must contain an array of objects or a single object.")
                return

            report['TOTAL_RECORDS'] = len(data)
            
            # Analyze the consistency of keys across all objects
            key_sets = [tuple(sorted(d.keys())) for d in data if isinstance(d, dict)]
            key_distribution = {}
            for ks in key_sets:
                key_distribution[ks] = key_distribution.get(ks, 0) + 1
            
            report['IS_CONSISTENT'] = -1.0 if len(key_distribution) <= 1 else 0.0
            report['KEY_SET_DISTRIBUTION'] = self._python_to_basic_data(key_distribution)
            
            if into_hash_name:
                self.variables[into_hash_name] = self._python_to_basic_data(report)
            else:
                print(f"--- JSON Analysis Report for: {filename} ---")
                print(f"  Total Records : {report['TOTAL_RECORDS']}")
                print(f"  Is Consistent : {'Yes' if report['IS_CONSISTENT'] else 'No'}")
                print("  Key Set Distribution:")
                for key_set, count in report['KEY_SET_DISTRIBUTION'].items():
                    print(f"    - {int(count)} record(s) with keys: {key_set}")

        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {filename}")
        except json.JSONDecodeError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"JSON parsing error: {e}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during JSON analysis: {e}")


    def _parse_describe_statement(self):
        """Parses and executes DESCRIBE TABLE, printing or capturing metadata."""
        self._expect('DESCRIBE')
        # The TABLE keyword is optional for usability
        if self._current_token() and self._current_token()[0] == 'TABLE':
            self._next_token()
        
        table_name = self._parse_expression()
        
        into_array_name = None
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token()
            into_array_name = self._expect('ID')[1]
            if into_array_name not in self.variables or not isinstance(self.variables.get(into_array_name), list):
                 self._error(f"'{into_array_name}' is not a dimensioned array for use with DESCRIBE INTO.")

        try:
            # Use PRAGMA to get table info, which is the standard SQLite way
            pragma_sql = f"PRAGMA table_info('{table_name}')"
            results = self._execute_sql(pragma_sql, is_query=True)
            
            if not results:
                print(f"Table '{table_name}' not found or has no columns.")
                return

            # The column names from the PRAGMA result itself
            headers = [desc[0] for desc in self.db_cursor.description]
            
            if into_array_name:
                # Capture the metadata into an array of hashes
                metadata_list = []
                for row in results:
                    metadata_list.append(dict(zip(headers, row)))
                self.variables[into_array_name] = self._python_to_basic_data(metadata_list)
            else:
                # Print the metadata to the console using the existing table formatter
                self._handle_output(results, headers)

        except sqlite3.Error as e:
            self.variables['ERR'] = 1.0
            self.variables['ERRMSG$'] = str(e)
            if self.sql_fatal_errors:
                self._error(f"Fatal SQLite Error: {e}")
        
    def _parse_gosub_statement(self):
        self._expect('GOSUB'); label_name = self._expect('ID')[1]
        if label_name not in self.labels: self._error(f"Label '{label_name}' not found.")
        self.gosub_stack.append(self.token_index); self.token_index = self.labels[label_name]
        
    def _parse_return_statement(self):
        self._expect('RETURN')
        if not self.gosub_stack: self._error("RETURN without GOSUB.")
        self.token_index = self.gosub_stack.pop()

TEST_PROGRAM_SOURCE = """
REM --- Test complex IF statement ---
x = 5
y = 15
PRINT "x = 5, y = 15"
IF (y - x) * 2 = 20 THEN
    PRINT "Test Passed: (15 - 5) * 2 = 20"
ELSE
    PRINT "Test Failed"
END IF

IF (y - x) * 2 <> 20 THEN
    PRINT "Test Failed"
ELSE
    PRINT "Test Passed: (15 - 5) * 2 is not <> 20"
END IF

z = 1
IF (y > x) AND (z = 1) THEN
    PRINT "Test Passed: Logical AND with parentheses"
END IF

END
"""

def run_interpreter(source_code, cmd_args=None, source_name="script", debug=False, dump_tokens=True):
    #print(f"--- Running {source_name} ---")
    if cmd_args is None: cmd_args = []
    
    interpreter = None
    try:
        lexer = Lexer(preprocess_continuations(source_code))

        # --- ADD THIS BLOCK ---
        if dump_tokens:
            print("\n--- TOKEN DUMP ---")
            for token in lexer.tokens:
                print(token)
            print("--------------------\n")
        # --- END OF BLOCK ---

        interpreter = Interpreter(lexer, cmd_args, debug=debug)
        interpreter.run()
    except (RuntimeError, ValueError, sqlite3.Error) as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        if interpreter: interpreter.close()
        #print(f"\n--- Finished {source_name} ---", file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        run_interpreter(TEST_PROGRAM_SOURCE, source_name="Internal Test Program")
        print("\n" + "="*50)
        print("Usage: python basic.py <filename.bas | -> [args...] [--debug] [--dump-tokens]", file=sys.stderr)
        return
 
    args = sys.argv[1:]
    is_debug = False
    if "--debug" in args:
        is_debug = True
        args.remove("--debug")

    dump_tokens_flag = False
    if "--dump-tokens" in args:
        dump_tokens_flag = True
        args.remove("--dump-tokens")
        
    source_code = ""
    cmd_args = []
    source_name = "script"
    
    if not args:
         print("Error: No source file specified.", file=sys.stderr)
         return

    if args[0] == '-':
        source_code = sys.stdin.read()
        source_name = "stdin"
        cmd_args = args[1:]
    else:
        filepath = args[0]
        source_name = filepath
        cmd_args = args[1:]
        if not os.path.exists(filepath):
            print(f"Error: File '{filepath}' not found.", file=sys.stderr)
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            print(f"An error occurred reading file: {e}", file=sys.stderr)
            return

    new_source_code = preprocess_continuations(source_code)
    if source_code.strip():
        # --- PASS THE NEW FLAG HERE ---
        run_interpreter(new_source_code, cmd_args, source_name, debug=is_debug, dump_tokens=dump_tokens_flag)
    else:
        print("No source code provided.", file=sys.stderr)
        
if __name__ == "__main__":
    main()
