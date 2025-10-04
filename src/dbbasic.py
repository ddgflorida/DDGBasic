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
import html
import fnmatch
import subprocess
import requests
import calendar
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import webbrowser
import zipfile
import xlrd3
import openpyxl
from bs4 import BeautifulSoup
from openpyxl.styles import Font, PatternFill, Alignment
from tui_runner import FormRunner
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, quote_plus

try:
    from web_form_runner import WebFormRunner
except ImportError:
    WebFormRunner = None

csv.field_size_limit(1024 * 1024)


def preprocess_includes(source_code, base_path='.', included_files=None):
    """
    Recursively finds all 'INCLUDE "filename"' statements and replaces them
    with the content of the specified file.
    """
    if included_files is None:
        included_files = set()

    include_pattern = re.compile(r'^\s*INCLUDE\s+"([^"]+)"', re.IGNORECASE | re.MULTILINE)

    def replacer(match):
        include_filename = match.group(1)
        include_path = os.path.join(base_path, include_filename)
        absolute_path = os.path.abspath(include_path)

        if absolute_path in included_files:
            return f"' SKIPPING CIRCULAR INCLUDE: \"{include_filename}\""

        included_files.add(absolute_path)
        try:
            with open(include_path, 'r', encoding='utf-8') as f:
                included_code = f.read()
            new_base_path = os.path.dirname(include_path)
            processed_included_code = preprocess_includes(included_code, new_base_path, included_files)
            return (
                f'\' <<< START INCLUDE: "{include_filename}"\n'
                f'{processed_included_code}\n'
                f'\' <<< END INCLUDE: "{include_filename}"'
            )
        except FileNotFoundError:
            return f'ERROR 2, "INCLUDE file not found: {include_filename} in folder {absolute_path}"'
        except Exception as e:
            return f'ERROR 1, "Error reading INCLUDE file: {e}"'

    # This line is crucial: it runs the replacement and ALWAYS returns a string.
    return include_pattern.sub(replacer, source_code)
    
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

    @staticmethod
    def starts_with(s, prefix):
      if not isinstance(s, str) or not isinstance(prefix, str): return None
      return 1 if s.startswith(prefix) else 0

    @staticmethod
    def ends_with(s, suffix):
      if not isinstance(s, str) or not isinstance(suffix, str): return None
      return 1 if s.endswith(suffix) else 0

    @staticmethod
    def initcap(s):
      if not isinstance(s, str): return None
      return s.title()

    @staticmethod
    def split_part(s, delimiter, part_index):
      if not isinstance(s, str) or not isinstance(delimiter, str) or not isinstance(part_index, int):
          return None
      
      # SQL functions are typically 1-based, while Python is 0-based.
      if part_index <= 0:
          return ""
      
      parts = s.split(delimiter)
      
      try:
          return parts[part_index - 1]
      except IndexError:
          # Return an empty string if the part index is out of bounds.
          return ""
    
    @staticmethod
    def translate(s, from_str, to_str):
      if not isinstance(s, str) or not isinstance(from_str, str) or not isinstance(to_str, str):
          return None
      translation_table = str.maketrans(from_str, to_str)
      return s.translate(translation_table)

    @staticmethod
    def instr2(s, substring):
      if not isinstance(s, str) or not isinstance(substring, str): return None
      pos = s.find(substring)
      return pos + 1 if pos != -1 else 0

    @staticmethod
    def instr3(s, substring, start):
      if not isinstance(s, str) or not isinstance(substring, str) or not isinstance(start, int): return None
      if start == 0: return 0
      start_pos = start - 1 if start > 0 else len(s) + start
      if start_pos < 0: start_pos = 0
      pos = s.find(substring, start_pos)
      return pos + 1 if pos != -1 else 0

    @staticmethod
    def instr4(s, substring, start, nth):
      if not isinstance(s, str) or not isinstance(substring, str) or not isinstance(start, int) or not isinstance(nth, int): return None
      if nth <= 0: return 0
      pos = start - 1 if start > 0 else len(s) + start
      if pos < 0: pos = 0
      found_pos = -1
      for _ in range(nth):
          found_pos = s.find(substring, pos)
          if found_pos == -1:
              return 0
          pos = found_pos + 1
      return found_pos + 1

    @staticmethod
    def soundex(s):
        if not s or not isinstance(s, str):
            return None
        s = s.upper()
        first_letter = s[0]
        if not 'A' <= first_letter <= 'Z':
            return None
        soundex_map = {
            'BFPV': '1', 'CGJKQSXZ': '2', 'DT': '3',
            'L': '4', 'MN': '5', 'R': '6'
        }
        code = first_letter
        prev_code = ''
        for char_map, num_code in soundex_map.items():
            if first_letter in char_map:
                prev_code = num_code
                break
        for char in s[1:]:
            if len(code) >= 4:
                break
            current_code = ''
            for char_map, num_code in soundex_map.items():
                if char in char_map:
                    current_code = num_code
                    break
            if current_code and current_code != prev_code:
                code += current_code
            if current_code:
                prev_code = current_code
        return (code + '000')[:4]
        
    @classmethod
    def register_all(cls, conn):
        functions_to_register = {
            "REVERSE": (1, cls.reverse), "STUFF": (4, cls.stuff), "LEFT$": (2, cls.left),
            "RIGHT$": (2, cls.right), "LPAD": (3, cls.lpad), "RPAD": (3, cls.rpad),
            "REPLICATE": (2, cls.replicate), "CHARINDEX": (2, cls.charindex),
            "STARTS_WITH": (2, cls.starts_with),
            "ENDS_WITH": (2, cls.ends_with),
            "INITCAP": (1, cls.initcap),
            "SPLIT_PART": (3, cls.split_part),
            "TRANSLATE": (3, cls.translate),
            "SOUNDEX": (1, cls.soundex),
            "INSTR": [(2, cls.instr2), (3, cls.instr3), (4, cls.instr4)],
        }
        for name, funcs in functions_to_register.items():
            # Handle both single and multiple function registrations for a given name
            if isinstance(funcs, list):
                for num_params, func in funcs:
                    conn.create_function(name, num_params, func)
            else:
                num_params, func = funcs
                conn.create_function(name, num_params, func)

# =================================================================
# GLOBAL STATE AND CONFIGURATION
# =================================================================
class OutputConfig:
    def __init__(self):
        self.mode = "CONSOLE"
        self.format = "TEXT"
        self.file_path = ""
        self.sql_options = {} 

g_output_config = OutputConfig()
g_null_handling_settings = {}
g_null_handling_default = 'CONVERT_EMPTY_TO_NULL'

# =================================================================
# Exception class for loop exits
# =================================================================
class LoopExit(Exception):
    """Exception raised to exit from a loop early."""
    pass

class ProgramEnd(Exception):
    """Exception raised to signal the END of the program."""
    pass

class RedirectSignal(Exception):
    """Exception raised to signal an HTTP redirect."""
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
            elif source_code[i:i+2] == '--': in_comment = True
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

def preprocess_echo_statements(source_code):
    lines = source_code.split('\n')
    processed_lines = []
    
    for line in lines:
        # Check if this line starts with ECHO (with optional leading whitespace)
        echo_match = re.match(r'^(\s*ECHO)\s*(.*)$', line, re.IGNORECASE)
        if echo_match:
            leading_space = echo_match.group(1)  # "ECHO" with any leading whitespace
            content = echo_match.group(2).rstrip()  # Content after ECHO
            escaped_content = content.replace('"', '""')
            processed_line = f'{leading_space} "{escaped_content}"'
            processed_lines.append(processed_line)
        else:
            processed_lines.append(line)
    
    return '\n'.join(processed_lines)
        
class Lexer:
    def __init__(self, source_code):
        source_code = source_code.replace('\r\n', '\n')
        lines = source_code.splitlines()
        numbered = [f"{i+1}: {line}" for i, line in enumerate(lines)]
        self.raw_source_code = source_code # "\n".join(numbered)
        self.line_starts = [0]
        for match in re.finditer(r"\n", source_code):
            self.line_starts.append(match.end())
        # Pre-process ECHO statements before tokenizing
        #print("DEBUG BEFORE:",self.raw_source_code)
        processed_code = preprocess_echo_statements(self.raw_source_code)
        #print("DEBUG AFTER:", processed_code)
        self.tokens = self._tokenize(processed_code)
    
    def get_line_col(self, pos):
        line = 1
        for i, start in enumerate(self.line_starts):
            if start > pos: break
            line = i + 1
        col = pos - self.line_starts[line-1] + 1
        return line, col

    def _tokenize(self, source_code_to_process):
        replacements = {
            r'\bEND\s+IF\b': 'ENDIF', r'\bLINE\s+INPUT\b': 'LINEINPUT', r'\bEND\s+LOOP\b': 'ENDLOOP',
            r'\bFOR\s+EACH\b': 'FOREACH', r'\bEND\s+TRANSACTION\b': 'ENDTRANSACTION', r'\bREAD\s+FILE\b': 'READFILE',
            r'\bTO\s+FILE\b': 'TOFILE', r'\bINTO\s+FILE\b': 'INTOFILE', 
            r'\bANALYZE\s+CSV\b': 'ANALYZECSV',r'\bANALYZE\s+FIXED\b': 'ANALYZEFIXED',
            r'\bANALYZE\s+JSONL\b': 'ANALYZEJSONL', r'\bANALYZE\s+JSON\b': 'ANALYZEJSON',
            r'\bANALYZE\s+XML\b': 'ANALYZEXML',r'\bANALYZE\s+TEXT\b': 'ANALYZETEXT',
            r'\bON\s+ERROR\s+GOTO\b': 'ONERRORGOTO',
            r'\bEND\s+FORM\b': 'ENDFORM',r'\bOPEN\s+FORM\b': 'OPENFORM',
            r'\bWITH\s+DETAILS\b': 'WITHDETAILS',
            r'\bWITH\s+FULLPATH\b': 'WITHFULLPATH',
            r'\bWITH\s+FOLDERSONLY\b': 'WITHFOLDERSONLY',
            r'\bWITH\s+FILESONLY\b': 'WITHFILESONLY', 
            r'\bLIST\s+FIELDS\b': 'LISTFIELDS'
        }
        code = source_code_to_process
        for pattern, repl in replacements.items():
            code = re.sub(pattern, repl, code, flags=re.IGNORECASE)
        self.modified_source_code = code

        token_specification = [
            # For giggles
            ('FORM', r'\bFORM\b(?!\$)'),  
            ('ENDFORM', r'\bENDFORM\b(?!\$)'),
            ('FIELD', r'\bFIELD\b(?!\$)'),
            ('BUTTON', r'\bBUTTON\b(?!\$)'),
            ('BELL', r'\bBELL\b(?!\$)'), 
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
            ('GRIDEDIT', r'\bGRIDEDIT\b(?!\$)'),
            ('SEARCH', r'\bSEARCH\b(?!\$)'),
            ('LOOKUP', r'\bLOOKUP\b(?!\$)'),   
            ('RETURNS', r'\bRETURNS\b(?!\$)'), 
            # ---------------------------
            ('STRING', r'"([^"]|"")*"'), ('SINGLE_Q_STRING', r"'[^']*'"),
            ('BACKTICK_STRING', r'`[^`]*`'), ('ASSIGN', r'='),('NUMBER', r'\d+(\.\d*)?'),
            ('REM', r'REM[^\n]*'), ('DASH_COMMENT', r'--[^\n]*'),
            ('AND', r'\bAND\b(?!\$)'), ('OR', r'\bOR\b(?!\$)'), ('FOREACH', r'\bFOREACH\b(?!\$)'),
            ('ANALYZECSV', r'\bANALYZECSV\b'), ('ANALYZEJSON', r'\bANALYZEJSON\b'), ('ANALYZETEXT', r'\bANALYZETEXT\b'),
            ('LINEINPUT', r'\bLINEINPUT\b(?!\$)'), ('TOFILE', r'\bTOFILE\b(?!\$)'), ('READFILE', r'\bREADFILE\b(?!\$)'),
            ('ENDLOOP', r'\bENDLOOP\b(?!\$)'), ('DATABASE', r'\bDATABASE\b(?!\$)'), ('SELECT', r'\bSELECT\b(?!\$)'),
            ('INSERT', r'\bINSERT\b(?!\$)'), ('DELETE', r'\bDELETE\b(?!\$)'), ('DESCRIBE', r'\bDESCRIBE\b(?!\$)'),
            ('UPDATE', r'\bUPDATE\b(?!\$)'), ('CREATE', r'\bCREATE\b(?!\$)'), ('DROP', r'\bDROP\b(?!\$)'),('ALTER', r'\bALTER\b(?!\$)'),
            ('BEGIN', r'\bBEGIN\b(?!\$)'), ('COMMIT', r'\bCOMMIT\b(?!\$)'), ('ROLLBACK', r'\bROLLBACK\b(?!\$)'),
            ('ENDTRANSACTION', r'\bENDTRANSACTION\b(?!\$)'), ('SUMMARIZE', r'\bSUMMARIZE\b(?!\$)'), 
            ('PRAGMA', r'\bPRAGMA\b(?!\$)'),('MERGE', r'\bMERGE\b(?!\$)'),('UPSERT', r'\bUPSERT\b(?!\$)'),
            ('COPY', r'\bCOPY\b(?!\$)'),('ATTACH', r'\bATTACH\b(?!\$)'),
            ('WITHFULLPATH', r'\bWITHFULLPATH\b(?!\$)'), ('WITHDETAILS', r'\bWITHDETAILS\b(?!\$)'),
            ('WITHFOLDERSONLY', r'\bWITHFOLDERSONLY\b(?!\$)'), ('WITHFILESONLY', r'\bWITHFILESONLY\b(?!\$)'),
            ('WITH', r'\bWITH\b(?!\$)'), ('FETCH', r'\bFETCH\b(?!\$)'),
            ('POST', r'\bPOST\b(?!\$)'), ('EXISTS', r'\bEXISTS\b(?!\$)'), ('ERROR', r'\bERROR\b(?!\$)'),
            ('XML', r'\bXML\b(?!\$)'), ('JSON', r'\bJSON\b(?!\$)'), ('JSONL', r'\bJSONL\b(?!\$)'),('SHOW', r'\bSHOW\b(?!\$)'), 
            ('PARSE', r'\bPARSE\b(?!\$)'), ('INTO', r'\bINTO\b(?!\$)'),('DUMP', r'\bDUMP\b(?!\$)'), 
            ('HASH', r'\bHASH\b(?!\$)'),('SORT', r'\bSORT\b(?!\$)'),('FIXED', r'\bFIXED\b(?!\$)'),('EXECUTE', r'\bEXECUTE\b(?!\$)'),
            ('ARRAY', r'\bARRAY\b(?!\$)'), ('GOSUB', r'\bGOSUB\b(?!\$)'), ('RETURN', r'\bRETURN\b(?!\$)'),
            ('SHELL', r'\bSHELL\b(?!\$)'), ('BROWSER', r'\bBROWSER\b(?!\$)'),('RUN', r'\bRUN\b(?!\$)'),
            ('DIM', r'\bDIM\b(?!\$)'), ('REDIM', r'\bREDIM\b(?!\$)'),('CHAIN', r'\bCHAIN\b(?!\$)'),
            ('OPTIONS', r'\bOPTIONS\b(?!\$)'), ('CSV', r'\bCSV\b(?!\$)'), ('HTML', r'\bHTML\b(?!\$)'), 
            ('TABLE', r'\bTABLE\b(?!\$)'), ('TEXT', r'\bTEXT\b(?!\$)'),('EVAL', r'\bEVAL\b(?!\$)'),
            ('LOAD', r'\bLOAD\b(?!\$)'), ('APPEND', r'\bAPPEND\b(?!\$)'), 
            ('REPLACE', r'\bREPLACE\b(?!\$)'), ('TRUNCATE', r'\bTRUNCATE\b(?!\$)'),
            ('EXCEL', r'\bEXCEL\b(?!\$)'), ('WRITE', r'\bWRITE\b(?!\$)'), ('USING', r'\bUSING\b(?!\$)'),
            ('OPEN', r'\bOPEN\b(?!\$)'), ('CLOSE', r'\bCLOSE\b(?!\$)'), ('INPUT', r'\bINPUT\b(?!\$)'),
            ('SET', r'\bSET\b(?!\$)'), ('OUTPUT', r'\bOUTPUT\b(?!\$)'), ('AS', r'\bAS\b(?!\$)'),
            ('PRINT', r'\bPRINT\b(?!\$)'), ('LET', r'\bLET\b(?!\$)'), ('IF', r'\bIF\b(?!\$)'), ('THEN', r'\bTHEN\b(?!\$)'),
            ('ELSEIF', r'\bELSEIF\b(?!\$)'),('ELSE', r'\bELSE\b(?!\$)'), ('ENDIF', r'\bENDIF\b(?!\$)'), 
            ('FOR', r'\bFOR\b(?!\$)'), ('TO', r'\bTO\b(?!\$)'),('ECHO', r'\bECHO\b(?!\$)'),
            ('ZIP', r'\bZIP\b(?!\$)'),('UNZIP', r'\bUNZIP\b(?!\$)'), ('UNPACK', r'\bUNPACK\b(?!\$)'),
            ('DO', r'\bDO\b(?!\$)'), ('UNTIL', r'\bUNTIL\b(?!\$)'),
            ('STEP', r'\bSTEP\b(?!\$)'), ('NEXT', r'\bNEXT\b(?!\$)'), ('IN', r'\bIN\b(?!\$)'), ('LOOP', r'\bLOOP\b(?!\$)'),
            ('WHILE', r'\bWHILE\b(?!\$)'), ('WEND', r'\bWEND\b(?!\$)'), ('NOT', r'\bNOT\b(?!\$)'), ('END', r'\bEND\b(?!\$)'),
            ('EXIT', r'\bEXIT\b(?!\$)'), ('FILES', r'\bFILES\b(?!\$)'), ('CHDIR', r'\bCHDIR\b(?!\$)'),
            ('MKDIR', r'\bMKDIR\b(?!\$)'), ('RMDIR', r'\bRMDIR\b(?!\$)'), ('KILL', r'\bKILL\b(?!\$)'),
            ('ONERRORGOTO', r'\bONERRORGOTO\b'), ('RESUME', r'\bRESUME\b(?!\$)'),
            ('TRON', r'\bTRON\b(?!\$)'), ('TROFF', r'\bTROFF\b(?!\$)'),('GOTO', r'\bGOTO\b(?!\$)'), 
            ('DETAILS', r'\bDETAILS\b(?!\$)'), ('REDIRECT', r'\bREDIRECT\b(?!\$)'),
            ('PUSH', r'\bPUSH\b(?!\$)'), ('POP', r'\bPOP\b(?!\$)'),
            ('SHIFT', r'\bSHIFT\b(?!\$)'), ('UNSHIFT', r'\bUNSHIFT\b(?!\$)'),
            ('SPLICE', r'\bSPLICE\b(?!\$)'), ('REVERSE', r'\bREVERSE\b(?!\$)'),
            ('ID', r'(?!INTO\b)[a-zA-Z_][a-zA-Z0-9_]*\$?'),
            ('OP', r"[+\*/-]"), ('CARET', r'\^'), ('AMPERSAND', r'&'),
            ('RELOP', r'<>|<=|>=|<|>'), ('HASH_SYM', r'#'), ('LPAREN', r'\('), ('RPAREN', r'\)'), 
            ('LBRACKET', r'\['), ('RBRACKET', r'\]'),('COMMA', r','),
            ('SEMICOLON', r';'), ('COLON', r':'), ('DOT', r'\.'), ('NEWLINE', r'\n'),
            ('SKIP', r'[ \t\u00A0]+'), ('MISMATCH', r'.'),
        ]
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
        raw_tokens, tokens, is_start_of_line = [], [], True
        for mo in re.finditer(tok_regex, code, re.IGNORECASE):
            kind, value, pos = mo.lastgroup, mo.group(), mo.start()
            #print("DEBUG", kind, value, pos)
            if kind in ['SKIP', 'REM', 'DASH_COMMENT']: continue
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

            # Handle line-level SQL (e.g., SELECT * FROM mytable;)
            if is_start_of_line and kind in Interpreter.SQL_KEYWORDS:
                semicolon_pos = self.modified_source_code.find(';', pos)
                if semicolon_pos != -1:
                    sql_end_pos = semicolon_pos + 1
                    sql_text = self.modified_source_code[pos:sql_end_pos].strip()
                    tokens.append(('SQL_STRING', sql_text, pos))
                    while i < len(raw_tokens) and raw_tokens[i][2] < sql_end_pos: i += 1
                    is_start_of_line = False
                    continue

            # Handle IN (SELECT...), EXISTS (SELECT...), or scalar (SELECT...) subqueries
            potential_subquery = (kind in ('IN', 'EXISTS', 'LPAREN', 'ASSIGN'))
            if potential_subquery:
                
                # Determine the start of the subquery content
                lparen_index = i
                if kind != 'LPAREN':
                    lparen_index = i + 1
                #print("DEBUG:","We may have a subquery, lparen_index=", lparen_index, "tokens=",tokens)
                #print("DEBUG raw:",raw_tokens)
                if lparen_index < len(raw_tokens) and raw_tokens[lparen_index][0] == 'LPAREN':
                    sql_keyword_index = lparen_index + 1
                    if sql_keyword_index < len(raw_tokens) and raw_tokens[sql_keyword_index][0] in Interpreter.SQL_KEYWORDS:
                        
                        # Add the token that came before the subquery, if any (e.g., IN, EXISTS, =)
                        if kind != 'LPAREN':
                            tokens.append(raw_tokens[i])

                        # Scan the raw source to find the matching closing parenthesis
                        lp_pos = raw_tokens[lparen_index][2]
                        nesting, search_pos, end_paren_pos, in_string = 1, lp_pos + 1, -1, False
                        while search_pos < len(self.modified_source_code):
                            char = self.modified_source_code[search_pos]
                            if char == "'": in_string = not in_string
                            elif not in_string and char == '(': nesting += 1
                            elif not in_string and char == ')':
                                nesting -= 1
                                if nesting == 0:
                                    end_paren_pos = search_pos
                                    break
                            search_pos += 1

                        if nesting != 0: self._error("Unmatched parenthesis in SQL subquery.")
                        
                        # Create and add the subquery tokens
                        sql_text = self.modified_source_code[lp_pos + 1 : end_paren_pos]
                        tokens.append(('LPAREN', '(', lp_pos))
                        tokens.append(('SQL_STRING', sql_text.strip(), lp_pos + 1))
                        tokens.append(('RPAREN', ')', end_paren_pos))
                        
                        # Correctly advance the raw_token index past the entire subquery
                        i = lparen_index
                        while i < len(raw_tokens) and raw_tokens[i][2] <= end_paren_pos:
                            i += 1
                        
                        is_start_of_line = False
                        #print("DEBUG:","SQL_STRING, end_paren_pos=", end_paren_pos, "tokens=",tokens)
                        continue
            u_value = value.upper()
            #if kind != 'STRING': value = u_value
            if kind == 'BACKTICK_STRING': kind = 'STRING'
            elif u_value == 'ENDIF': kind, value = 'END IF', 'END IF'
            elif u_value == 'LINEINPUT': kind, value = 'LINE INPUT', 'LINE INPUT'
            elif u_value == 'READFILE': kind, value = 'READ FILE', 'READ FILE' 
            elif u_value == 'TOFILE': kind, value = 'TO FILE', 'TO FILE'
            elif u_value == 'ENDFORM': kind, value = 'ENDFORM', 'END FORM'
            elif u_value == 'FOREACH': kind, value = 'FOR EACH', 'FOR EACH'
            elif u_value == 'ENDTRANSACTION': kind, value = 'END TRANSACTION', 'END TRANSACTION'
            elif u_value == 'ANALYZECSV': kind, value = 'ANALYZE CSV', 'ANALYZE CSV'
            elif u_value == 'ANALYZEJSON': kind, value = 'ANALYZE JSON', 'ANALYZE JSON'
            elif u_value == 'ANALYZEJSONL': kind, value = 'ANALYZE JSONL', 'ANALYZE JSONL'
            elif u_value == 'ANALYZEXML': kind, value = 'ANALYZE XML', 'ANALYZE XML'
            elif u_value == 'ANALYZETEXT': kind, value = 'ANALYZE TEXT', 'ANALYZE TEXT'
            elif u_value == 'ANALYZEFIXED': kind, value = 'ANALYZE FIXED', 'ANALYZE FIXED'
            elif u_value == 'ONERRORGOTO': kind, value = 'ON ERROR GOTO', 'ON ERROR GOTO'
            elif u_value == 'WITHFULLPATH': kind, value = 'WITH FULLPATH', 'WITH FULLPATH'
            elif u_value == 'WITHDETAILS': kind, value = 'WITH DETAILS', 'WITH DETAILS'
            elif u_value == 'WITHFOLDERSONLY': kind, value = 'WITH FOLDERSONLY', 'WITH FOLDERSONLY'
            elif u_value == 'WITHFILESONLY': kind, value = 'WITH FILESONLY', 'WITH FILESONLY' 
            
            tokens.append((kind, value, pos)); is_start_of_line = False; i += 1
            #print("DEBUG:", tokens)
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
    SQL_KEYWORDS = {'SELECT', 'INSERT', 'DELETE', 'UPDATE', 'CREATE', 'DROP', 'ATTACH', 'COPY',
                    'WITH', 'BEGIN', 'COMMIT', 'ROLLBACK', 'END TRANSACTION', 'ALTER', 'SUMMARIZE', 'PRAGMA'}
    SQL_RESERVED_WORDS = {
            'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'TABLE', 'ATTACH', 'COPY',
            'VIEW', 'INDEX', 'ORDER', 'GROUP', 'BY', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'SUMMARIZE', 'PRAGMA',
            'OUTER', 'ON', 'AS', 'IN', 'IS', 'NULL', 'NOT', 'AND', 'OR', 'LIMIT', 'OFFSET'
        }
    INVALID_KEY_TOKENS = {
                    'ASSIGN', 'LPAREN', 'RPAREN', 'COMMA', 'STRING', 'NUMBER',
                    'OP', 'RELOP', 'DOT', 'SEMICOLON', 'COLON', 'NEWLINE', 'HASH_SYM'
                }
    
    def __init__(self, lexer, cmd_args=None, debug=False, shared_db_connection=None):
        self.lexer = lexer
        self.tokens = self.lexer.tokens
        self.token_index = 0
        self.variables = {}
        lines = self.lexer.raw_source_code.splitlines()
        numbered = [f"{i+1}: {line}" for i, line in enumerate(lines)]

        self.file_handles = {}
        self.command_args = cmd_args if cmd_args is not None else []
        self.gosub_stack = []
        self.labels = {}
        self.form_definitions = {}
        self.db_engine = 'sqlite' # Set SQLite as the default engine
        self.sql_fatal_errors = True
        self.trace_mode = False   # FOR TRON AND TROFF
        self.program_terminated = False # Termination flag
        self.hash_keys_mode = 'PRESERVE_CASE'  # Default to preserve case
        self.run_stack = []
        self.last_sql_statement = ""
                
        # --- NEW: Error handling state ---
        self.error_handler_label = None
        self.in_error_handler = False
        self.error_resume_index = None
        
        self.debug_mode = debug # <-- And add this line
        self.jump_map = {}
        self.db_connection = None
        self._is_shared_connection = False # Flag to track ownership

        if shared_db_connection:
            self.db_connection = shared_db_connection
            self.db_cursor = self.db_connection.cursor()
            self._is_shared_connection = True
        else:
            self._init_db() # Only create a new DB if one wasn't passed in

        self._pre_scan_for_jumps()
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
                # A DO loop must start a statement. Check if the previous token
                # is a statement separator (or if it's the first token).
                is_start_of_statement = (index == 0) or (self.tokens[index - 1][0] in ['NEWLINE', 'COLON'])
                
                if not is_start_of_statement:
                    continue # This DO is part of another command, not a loop start.

                # Also, ignore if it's part of an 'EXIT DO' statement.
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

    def _quote_identifier(self, identifier: str, quote_style: str = '"') -> str:
            """
            Wraps a SQL identifier in quotes if it's a reserved
            keyword or contains characters that require quoting.
            Supports different quoting styles ('"' or '[') and automatically
            forces '"' if the engine is DuckDB.
            """
            # --- NEW: Engine-aware safety check ---
            # If the engine is DuckDB, it does not support bracket quoting.
            # Force the quote style to double quotes, overriding any user preference.
            if self.db_engine == 'duckdb' and quote_style == '[':
                quote_style = '"'
            # --- END NEW LOGIC ---

            identifier_str = str(identifier)
            
            # Determine the quote characters based on the (potentially overridden) style
            if quote_style == '[':
                open_quote, close_quote = '[', ']'
            else:
                open_quote, close_quote = '"', '"'

            # Rule 1: If it's a reserved keyword, it must be quoted.
            if identifier_str.upper() in self.SQL_RESERVED_WORDS:
                return f'{open_quote}{identifier_str}{close_quote}'
            
            # Rule 2: If it's a "simple" identifier, it doesn't need quotes.
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier_str):
                return identifier_str
                
            # Rule 3: If it's not simple, it must be quoted.
            # Before quoting, remove any characters that would conflict with the quotes.
            safe_identifier = identifier_str.replace(open_quote, '').replace(close_quote, '')
            return f'{open_quote}{safe_identifier}{close_quote}'

    def _split_sql_statements(self, sql_text: str) -> list[str]:
        """
        Splits a single string of SQL into a list of individual statements.

        This function correctly handles:
        - Single-line comments starting with '--'
        - Multi-line comments enclosed in '/*' and '*/'
        - Semicolons used as statement terminators, ignoring those inside comments or string literals.

        Args:
            sql_text: A string containing one or more SQL statements.

        Returns:
            A list of strings, where each string is a single SQL statement.
        """
        statements = []
        current_statement = []
        
        # State flags
        in_multiline_comment = False
        in_single_line_comment = False
        in_string_literal = False
        
        # We use an index to allow for two-character lookaheads (e.g., for '/*' or '--')
        i = 0
        while i < len(sql_text):
            char = sql_text[i]
            
            # --- State: In a single-line comment ---
            if in_single_line_comment:
                if char == '\n':
                    in_single_line_comment = False
                    # Preserve the newline in the current statement buffer
                    current_statement.append(char)
                i += 1
                continue

            # --- State: In a multi-line comment ---
            if in_multiline_comment:
                if char == '*' and i + 1 < len(sql_text) and sql_text[i+1] == '/':
                    in_multiline_comment = False
                    i += 2 # Skip both '*' and '/'
                else:
                    i += 1
                continue

            # --- State: Not in any comment ---
            
            # Check for start of a multi-line comment '/*'
            if not in_string_literal and char == '/' and i + 1 < len(sql_text) and sql_text[i+1] == '*':
                in_multiline_comment = True
                i += 2
                continue

            # Check for start of a single-line comment '--'
            if not in_string_literal and char == '-' and i + 1 < len(sql_text) and sql_text[i+1] == '-':
                in_single_line_comment = True
                i += 2
                continue
            
            # Check for entering/exiting a string literal
            if char == "'":
                in_string_literal = not in_string_literal
            
            # Check for statement terminator ';'
            if char == ';' and not in_string_literal:
                statement_str = "".join(current_statement).strip()
                if statement_str:
                    statements.append(statement_str)
                current_statement = [] # Reset for the next statement
                i += 1
                continue

            # If not a special character, append to the current statement
            current_statement.append(char)
            i += 1
            
        # After the loop, add any remaining text as the final statement
        last_statement = "".join(current_statement).strip()
        if last_statement:
            statements.append(last_statement)
            
        return statements
    
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
        elif token[0] == 'ID' and token[1].upper() == 'ENGINE':
            self._next_token() # Consume ENGINE
            engine_token = self._expect('ID')
            engine_name = engine_token[1].lower()
            if engine_name in ['sqlite', 'duckdb']:
                self.db_engine = engine_name
                #print(f"Database engine set to {self.db_engine}.")
                # Close any existing connection when switching engines
                if self.db_connection:
                    self.db_connection.close()
                    self.db_connection = None
                # Reinitialize with new engine
                self._init_db()
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
        if self.db_connection and not self._is_shared_connection:
            self.db_connection.close()
            self.db_connection = None

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
        
    def _get_primary_key(self, table_name):
        """
        Determines the primary key column for a given table.
        Returns the column name or 'rowid' for SQLite tables without explicit PKs.
        """
        try:
            if self.db_engine == 'duckdb':
                # DuckDB: Query information schema for primary key constraints
                pk_sql = f"""
                    SELECT kcu.column_name 
                    FROM information_schema.table_constraints tc 
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name 
                    WHERE tc.table_name = '{table_name}' 
                        AND tc.constraint_type = 'PRIMARY KEY'
                    ORDER BY kcu.ordinal_position
                    LIMIT 1
                """
                pk_result = self._execute_sql(pk_sql, is_query=True)
                if pk_result:
                    return pk_result[0][0]
                else:
                    return None
                    
            else:  # SQLite
                # First, check for explicit primary key columns
                schema_info = self._execute_sql(f"PRAGMA table_info('{table_name}')", is_query=True)
                if not schema_info:
                    raise RuntimeError(f"Table '{table_name}' does not exist")
                
                # Look for columns marked as primary key (pk = 1)
                explicit_pk = next((col[1] for col in schema_info if col[5] == 1), None)
                if explicit_pk:
                    return explicit_pk
                
                # No explicit PK found, check if table uses implicit rowid
                table_sql_result = self._execute_sql(
                    f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'", 
                    is_query=True
                )
                
                if table_sql_result and table_sql_result[0][0]:
                    table_ddl = table_sql_result[0][0].upper()
                    if "WITHOUT ROWID" in table_ddl:
                        # Table was created WITHOUT ROWID, so no implicit primary key
                        return None
                    else:
                        # Table has implicit rowid
                        return "rowid"
                else:
                    # Shouldn't happen if table exists, but fallback to rowid
                    return "rowid"
                    
        except Exception as e:
            # Log the error but don't crash the program
            print(f"Warning: Failed to auto-discover primary key for '{table_name}': {e}")
            # Both SQLite and DuckDB support rowid as fallback
            return None
    
    def _table_exists(self, table_name):
            """Checks if a table exists in the current database."""
            if self.db_engine == 'duckdb':
                sql = f"SELECT 1 FROM duckdb_tables() WHERE table_name = ?"
            else: # SQLite
                sql = f"SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?"
            
            result = self._execute_sql(sql, is_query=True, params=[table_name])
            return bool(result)
        
    def _get_table_metadata(self, table_name: str, include_indexes: bool = False) -> dict:
        """
        Fetches comprehensive metadata for a given table.

        Args:
            table_name: The name of the table to inspect.
            include_indexes: Whether to include index information.

        Returns:
            A dictionary containing:
            {
                'pk': 'primary_key_column_name',
                'columns': ['col1', 'col2', ...],
                'types': { 'COL1_UPPER': 'INTEGER', 'COL2_UPPER': 'TEXT', ... },
                'indexes': ['CREATE INDEX ...', ...] (if include_indexes=True)
            }
        """
        metadata = {'pk': None, 'columns': [], 'types': {}}
        
        try:
            if self.db_engine == 'duckdb':
                # DuckDB: Get all info from information_schema
                cols_sql = f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position"
                schema_info = self._execute_sql(cols_sql, is_query=True)
                if not schema_info: 
                    self._error(f"Table '{table_name}' not found or has no columns.")
                
                for row in schema_info:
                    col_name, col_type = row[0], row[1].upper()
                    metadata['columns'].append(col_name)
                    metadata['types'][col_name.upper()] = col_type
                metadata['pk'] = self._get_primary_key(table_name) or "rowid"
                
                # Get indexes if requested
                if include_indexes:
                    index_sql = f"""
                    SELECT sql FROM duckdb_indexes() WHERE table_name = '{table_name}'
                    UNION ALL
                    -- Primary keys and unique constraints for this table
                    SELECT 
                        'ALTER TABLE "' || tc.table_name || '" ADD CONSTRAINT "' || tc.constraint_name || 
                        '" ' || tc.constraint_type || ' (' || 
                        string_agg('"' || kcu.column_name || '"', ', ' ORDER BY kcu.ordinal_position) || ');' AS sql
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_name = kcu.table_name
                    WHERE tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                        AND tc.table_name = '{table_name}'
                    GROUP BY tc.table_name, tc.constraint_name, tc.constraint_type
                    ORDER BY 1
                    """
                    index_results = self._execute_sql(index_sql, is_query=True)
                    metadata['indexes'] = [row[0] for row in index_results] if index_results else []
                    
            else: 
                # SQLite: Use PRAGMA
                schema_info = self._execute_sql(f"PRAGMA table_info('{table_name}')", is_query=True)
                if not schema_info: 
                    self._error(f"Table '{table_name}' not found.")
                
                # schema_info format: (cid, name, type, notnull, dflt_value, pk)
                for col in schema_info:
                    col_name, col_type = col[1], col[2].upper()
                    metadata['columns'].append(col_name)
                    metadata['types'][col_name.upper()] = col_type
                metadata['pk'] = self._get_primary_key(table_name) or "rowid"
                
                # Get indexes if requested
                if include_indexes:
                    index_sql = f"""
                    SELECT sql FROM sqlite_master 
                    WHERE type = 'index' AND sql IS NOT NULL AND tbl_name = '{table_name}'

                    UNION ALL

                    SELECT 
                        'ALTER TABLE "' || m.name || '" ADD CONSTRAINT "pk_' || m.name || 
                        '" PRIMARY KEY (' || group_concat('"' || p.name || '"', ', ') || ');' AS sql
                    FROM sqlite_master m
                    JOIN pragma_table_info(m.name) p
                        ON m.name = '{table_name}'
                    WHERE p.pk > 0
                    GROUP BY m.name
                    HAVING COUNT(p.pk) > 0

                    UNION ALL

                    SELECT 
                        'ALTER TABLE "' || m.name || '" ADD CONSTRAINT "unique_' || m.name || '_' || group_concat(p.name, '_') || 
                        '" UNIQUE (' || group_concat('"' || p.name || '"', ', ') || ');' AS sql
                    FROM sqlite_master m
                    JOIN pragma_index_list(m.name) il ON m.name = '{table_name}'
                    JOIN pragma_index_info(il.name) p ON il.name = p.name
                    WHERE il.origin = 'u'
                    GROUP BY m.name, il.name

                    ORDER BY 1
                    """
                    index_results = self._execute_sql(index_sql, is_query=True)
                    metadata['indexes'] = [row[0] for row in index_results] if index_results else []
            
            return metadata
            
        except Exception as e:
            # Re-raise as a more specific error
            self._error(f"Failed to get metadata for table '{table_name}': {e}")

    def _get_database_objects(self, object_type: str = 'tables') -> list:
        """
        Returns a list of database objects (tables or indexes) for both SQLite and DuckDB.
        
        Args:
            object_type: 'tables' or 'indexes'
        
        Returns:
            List of object names or SQL statements
        """
        if object_type.lower() == 'tables':
            if self.db_engine == 'duckdb':
                sql = "SHOW TABLES"
            else:  # SQLite
                sql = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        
        elif object_type.lower() == 'indexes':
            if self.db_engine == 'duckdb':
                sql = """
                SELECT sql FROM duckdb_indexes()
                UNION ALL
                -- Primary keys and unique constraints
                SELECT 
                    'ALTER TABLE "' || tc.table_name || '" ADD CONSTRAINT "' || tc.constraint_name || 
                    '" ' || tc.constraint_type || ' (' || 
                    string_agg('"' || kcu.column_name || '"', ', ' ORDER BY kcu.ordinal_position) || ');' AS sql
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_name = kcu.table_name
                WHERE tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                GROUP BY tc.table_name, tc.constraint_name, tc.constraint_type
                ORDER BY 1
                """
            else:  # SQLite
                sql = """
                SELECT sql FROM sqlite_master 
                WHERE type = 'index' AND sql IS NOT NULL

                UNION ALL

                SELECT 
                    'ALTER TABLE "' || m.name || '" ADD CONSTRAINT "pk_' || m.name || 
                    '" PRIMARY KEY (' || group_concat('"' || p.name || '"', ', ') || ');' AS sql
                FROM sqlite_master m
                JOIN pragma_table_info(m.name) p
                    ON m.name IS NOT NULL
                WHERE p.pk > 0
                GROUP BY m.name
                HAVING COUNT(p.pk) > 0

                UNION ALL

                SELECT 
                    'ALTER TABLE "' || m.name || '" ADD CONSTRAINT "unique_' || m.name || '_' || group_concat(p.name, '_') || 
                    '" UNIQUE (' || group_concat('"' || p.name || '"', ', ') || ');' AS sql
                FROM sqlite_master m
                JOIN pragma_index_list(m.name) il ON m.name IS NOT NULL
                JOIN pragma_index_info(il.name) p ON il.name = p.name
                WHERE il.origin = 'u'
                GROUP BY m.name, il.name

                ORDER BY 1
                """
        else:
            raise ValueError(f"Unsupported object_type: {object_type}")
        
        results = self._execute_sql(sql, is_query=True)
        return [row[0] for row in results] if results else []

    def _get_table_list(self):
        return self._get_database_objects('tables')
        '''
        """Returns a list of user-created table names for both SQLite and DuckDB."""
        if self.db_engine == 'duckdb':
            sql = "SHOW TABLES"
        else:  # SQLite
            sql = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        
        results = self._execute_sql(sql, is_query=True)
        return [row[0] for row in results] if results else []
        '''
    
    def _find_variable_key(self, var_name):
        """Finds the actual stored key for a variable.
        
        Tries an exact match first, then a case-insensitive match.
        Returns the key if found, otherwise None.
        """
        # 1. Exact match first
        if var_name in self.variables:
            return var_name
        
        # 2. If not found, try a case-insensitive search
        var_name_upper = var_name.upper()
        for key in self.variables:
            if key.upper() == var_name_upper:
                return key
                
        return None

    def _get_variable_value(self, var_path, auto_create=True):
        """
        Get variable value supporting dot notation.
        
        First, it tries an exact match on the variable name. If not found,
        it performs a case-insensitive search. Hash keys are handled similarly.
        """
        # --- 1. Parse Input ---
        if '.' in var_path:
            var_name, hash_key = var_path.split('.', 1)
        else:
            var_name, hash_key = var_path, None

        # --- 2. Find the Variable ---
        actual_var_key = self._find_variable_key(var_name)
        
        if actual_var_key is None:
            # Variable does not exist in any form
            if not auto_create:
                return None
            
            # Auto-create with the exact case provided
            actual_var_key = var_name 
            if hash_key:
                self.variables[actual_var_key] = {}
            else:
                self.variables[actual_var_key] = "" if var_name.endswith('$') else 0.0

        variable = self.variables[actual_var_key]

        # --- 3. Handle Hash Access if Needed ---
        if hash_key is None:
            return variable

        if not isinstance(variable, dict):
            # Promote a simple variable to a hash if needed
            if not auto_create:
                return None
            variable = self.variables[actual_var_key] = {}

        # Hash key lookup: exact match first, then case-insensitive
        if hash_key in variable:
            return variable[hash_key]
            
        hash_key_upper = hash_key.upper()
        for existing_key in variable:
            if existing_key.upper() == hash_key_upper:
                return variable[existing_key]
        
        # --- 4. Auto-create Hash Key if Needed ---
        if auto_create:
            default_value = "" if hash_key.endswith('$') else 0.0
            variable[hash_key] = default_value # Store with exact case
            return default_value
            
        return None

    def _set_variable_value(self, var_name, value, hash_key=None):
        """
        Set variable value, preserving the original case of the variable
        and hash key.
        """
        # Find the key to use: prefer an existing case-insensitive match
        key_to_use = self._find_variable_key(var_name) or var_name
        
        if hash_key is None:
            # Simple variable assignment
            self.variables[key_to_use] = value
        else:
            # Hash assignment
            if key_to_use not in self.variables or not isinstance(self.variables[key_to_use], dict):
                self.variables[key_to_use] = {}
            
            # Find existing hash key to overwrite, preserving its case
            actual_hash_key = hash_key
            hash_key_upper = hash_key.upper()
            for existing_key in self.variables[key_to_use]:
                if existing_key.upper() == hash_key_upper:
                    actual_hash_key = existing_key
                    break
            
            # Store hash value with the appropriate (new or existing) case-sensitive key
            self.variables[key_to_use][actual_hash_key] = value

                
    def _extract_sql_from_parens(self):
        self._expect('LPAREN') 
        sql_token = self._expect('SQL_STRING')
        self._expect('RPAREN')
        return sql_token[1]

    def _execute_sql(self, sql_string, is_query=False, params=None):
        self.variables.update({'ERR': 0.0, 'ERRMSG$': "", 'SQL_ROWCOUNT': 0.0, 'SQL_FOUND': 0.0, 'SQL_NOTFOUND': -1.0})

        # If parameters are provided directly, we assume the SQL is already formatted
        # with '?' placeholders and we can execute it immediately.
        if params is not None:
            try:
                self.db_cursor.execute(sql_string, params)
                if not is_query:
                    row_count = self.db_cursor.rowcount
                    self.variables['SQL_ROWCOUNT'] = float(row_count if row_count != -1 else 0)
                    self.variables['SQL_FOUND'] = -1.0 if row_count > 0 else 0.0
                    self.variables['SQL_NOTFOUND'] = 0.0 if row_count > 0 else -1.0
                
                if is_query:
                    return self.db_cursor.fetchall()
                return None
            except (sqlite3.Error, duckdb.Error) as e:
                self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
                if self.sql_fatal_errors: self._error(f"Fatal DB Error: {e}")
                return None
                
        # 1. Always find the bind variables from the SQL string first.
        # This gives us the expected order and count.
        bind_vars = re.findall(r':([a-zA-Z_][a-zA-Z0-9_]*\$?(?:\.[a-zA-Z_][a-zA-Z0-9_]*\$?)*)', sql_string)

        # 2. Determine the final list of parameter values.
        resolved_params = []
        if params is None:
            for var_from_sql in bind_vars:
                # Use the new variable lookup method with auto_create=False for SQL binding
                #print("DEBUG: var_from_sql=", var_from_sql)
                var_value = self._get_variable_value(var_from_sql, auto_create=False)
                if var_value is None:
                    self._error(f"Bind variable ':{var_from_sql}' not found in internal state.")
                    return # Stop execution if a variable is missing
                resolved_params.append(var_value)
        else:
            resolved_params = params

            # 3. Add a check for safety: ensure the number of variables matches the parameters.
            if len(bind_vars) != len(resolved_params):
                self._error(
                    f"Parameter mismatch: SQL expected {len(bind_vars)} variables "
                    f"({', '.join(':' + v for v in bind_vars)}), "
                    f"but {len(resolved_params)} were provided."
                )
                return # Stop execution

        # 4. Finally, always substitute the named variables with '?' for the DB driver.
        final_sql = re.sub(r':([a-zA-Z_][a-zA-Z0-9_]*\$?(?:\.[a-zA-Z_][a-zA-Z0-9_]*\$?)*)', '?', sql_string)

        #print(f"Executing SQL: {final_sql}")
        #print(f"With Parameters: {resolved_params}")

        try:
            if resolved_params:
                result = self.db_cursor.execute(final_sql, resolved_params)
            else:
                result = self.db_cursor.execute(final_sql)
            
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
            self.last_sql_statement = sql_text
            self._next_token()
            is_select = sql_text.upper().startswith(('SELECT', 'WITH', 'SUMMARIZE', 'PRAGMA'))
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
            # Peek ahead to determine the type of FOR loop without consuming tokens
            is_in_loop = False
            peek_index = self.token_index + 1
            while peek_index < len(self.tokens) and self.tokens[peek_index][0] != 'NEWLINE':
                if self.tokens[peek_index][0] == 'ASSIGN':
                    break # This is a FOR i = 1 TO 10 loop
                if self.tokens[peek_index][0] == 'IN':
                    is_in_loop = True
                    break
                peek_index += 1

            if is_in_loop:
                # The token after IN determines the loop type
                loop_type_token = self.tokens[peek_index + 1]
                if loop_type_token[0] == 'CSV':                  # iteral csv file
                    self._parse_for_in_csv_loop()
                elif loop_type_token[0] == 'JSONL':              # interate json lines file
                    self._parse_for_in_jsonl_loop()
                elif loop_type_token[0] == 'JSON':               # iterate json keys
                    self._parse_for_in_json_loop()
                elif loop_type_token[0] == 'FILES':              # loop through files
                    self._parse_for_in_files_loop()              
                else: # Default to SQL loop                      # iterate sql result set
                    self._parse_for_in_sql_loop()
            else:
                # If 'IN' was not found, it's a standard FOR i = 1 TO 10 loop
                self._parse_for_statement()
        elif token[0] == 'SORT':
            self._parse_sort_statement()
        elif token[0] == 'FILES':                                 # get directory listing
            self._parse_files_statement()
        elif token[0] == 'ID' and token[1].upper() == 'NAME':     # rename file
            self._parse_name_statement()
        elif token[0] == 'DUMP':                                  # see internals
            self._parse_dump_statement()
        elif token[0] == 'CHDIR':                                 # change directory   
            self._parse_chdir_statement()
        elif token[0] == 'MKDIR':                                 # make directory   
            self._parse_mkdir_statement()
        elif token[0] == 'RMDIR':                                 # remove directory
            self._parse_rmdir_statement()
        elif token[0] == 'KILL':                                  # delete file
            self._parse_kill_statement()
        elif token[0] == 'SHELL':                                 # invoke o/s shell
            self._parse_shell_statement() 
        elif token[0] == 'SHOW':
            self._parse_show_statement()
        elif token[0] == 'EXECUTE':                               # execute dynamic sql
            self._parse_execute_statement()
        elif token[0] == 'CHAIN':                                 # Replace current script with another DbBASIC script
            self._parse_chain_statement()
        elif token[0] == 'RUN':                                   # Run another script and come back
            self._parse_run_statement()
        elif token[0] == 'EVAL':                                  # Run script in a string
            self._parse_eval_statement()
        elif token[0] == 'ZIP':                                   # zip file to zip folder
            self._parse_zip_statement()
        elif token[0] == 'UNZIP':                                 # unzip zip folder
            self._parse_unzip_statement()
        elif token[0] == 'BROWSER':                               # invoice default browser
            self._parse_browser_statement() 
        elif token[0] == 'EXIT':                                  # EXIT a loop early
            self._parse_exit_statement()
        elif token[0] == 'ERROR':                                 # Force an error
            self._parse_error_statement()
        elif token[0] == 'FETCH':                                 # invoke URL
            self._parse_fetch_statement()
        elif token[0] == 'LOAD':                                  # LOAD data into a sql table
            self._parse_load_statement()
        elif token[0] == 'ANALYZE TEXT':
            self._parse_analyze_text_statement()
        elif token[0] == 'ANALYZE CSV':
            self._parse_analyze_csv_statement()
        elif token[0] == 'ANALYZE FIXED':
            self._parse_analyze_fixed_statement()
        elif token[0] == 'ANALYZE JSON':
            self._parse_analyze_json_statement()
        elif token[0] == 'ANALYZE JSONL':
            self._parse_analyze_jsonl_statement()
        elif token[0] == 'ANALYZE XML':
            self._parse_analyze_xml_statement()
        elif token[0] == 'PRINT':
            self._parse_print_statement()
        elif token[0] == 'ECHO':
            self._parse_echo_statement()
        elif token[0] == 'DESCRIBE':                              # describe sql table/view
            self._parse_describe_statement()
        elif token[0] == 'WRITE':                                 # write variables as csv
            self._parse_write_statement()
        elif token[0] == 'DATABASE':                              # define database in use
            self._parse_database_statement()
        elif token[0] == 'LET' or token[0] == 'ID':               # optional let var = value
             self._parse_assignment_statement()
        elif token[0] == 'DIM':                                   # declare variable
            self._parse_dim_statement()
        elif token[0] == 'REDIM':                                 # redeclare array
            self._parse_redim_statement()
        elif token[0] == 'WHILE':                                 # while loop
            self._parse_while_statement()
        elif token[0] == 'OPEN':                                  # open file
            self._parse_open_statement()
        elif token[0] == 'READ FILE':                             # read file into variable
            self._parse_read_file_statement()
        elif token[0] == 'CLOSE':                                 # close file
            self._parse_close_statement()
        elif token[0] == 'LINE INPUT':                            # read a line from file
            self._parse_line_input_statement()
        elif token[0] == 'INPUT':                                 # read input from stdin
            self._parse_input_statement()
        elif token[0] == 'GOSUB':                                 # call named subroutine
            self._parse_gosub_statement()
        elif token[0] == 'RETURN':                                # return from subroutine
            self._parse_return_statement()
        elif token[0] == 'PUSH':                                  # Push item on array
            self._parse_push_statement()
        elif token[0] == 'POP':                                   # Pop array
            self._parse_pop_statement()
        elif token[0] == 'UNSHIFT':
            self._parse_unshift_statement()
        elif token[0] == 'SHIFT':
            self._parse_shift_statement()
        elif token[0] == 'SPLICE':
            self._parse_splice_statement()
        elif token[0] == 'REVERSE':
            self._parse_reverse_statement()
        elif token[0] == 'TRON':                                  # trace on
            self._parse_tron_statement()
        elif token[0] == 'TROFF':                                 # trace off
            self._parse_troff_statement()
        elif token[0] in ['ELSE', 'ELSEIF', 'END IF', 'NEXT', 'WEND', 'END LOOP', 'LOOP']:
            self._error(f"Unexpected '{token[0]}'")
        elif token[0] == 'ID' and token[1].upper() == 'COPY':
            self._parse_copy_statement()
        elif token[0] == 'BELL':                                  # Ring a bell
            self._parse_bell_statement()
        elif token[0] == 'REDIRECT':
            self._next_token() # Consume REDIRECT
            destination_url = self._parse_expression()
            raise RedirectSignal(destination_url)
        elif token[0] == 'UNPACK':
            self._parse_unpack_statement()
        elif token[0] == 'FORM':                                   
            self._parse_form_statement()
        elif token[0] == 'OPENFORM':
            self._parse_open_form_statement()
        elif token[0] == 'GRIDEDIT':
            self._parse_gridedit_statement()
        else:
            self._error(f"Unknown statement: {token[0]}")

    def _parse_bell_statement(self):
        """Parses and executes a BELL statement."""
        self._expect('BELL')
        # The '\a' is the ASCII BEL character.
        # end='' prevents a newline, and flush=True ensures it beeps immediately.
        print('\a', end='', flush=True)
        
    def _extract_table_from_select(self, sql_string):
        """
        Uses a regex to find the first table name after a FROM clause.
        Handles quoted and unquoted identifiers. Not a full SQL parser.
        """
        # This regex looks for FROM followed by an optional quote ([ or "),
        # captures the name, then matches the optional closing quote.
        match = re.search(
            r'\bFROM\s+(?:\[([^\]]+)\]|"([^"]+)"|([a-zA-Z_][a-zA-Z0-9_]*))',
            sql_string,
            re.IGNORECASE
        )
        if match:
            # The result will be in one of the capture groups
            return next((group for group in match.groups() if group is not None), None)
        return None

    def execute(self, code_string):
        """
        Executes a string of DbBasic code using the interpreter's current state.
        This allows the interpreter to be re-used for multiple scripts.
        Currently used by dbbasicweb.py to implement scripting
        """
        self.program_terminated = False

        base_path = '.'

        processed_includes = preprocess_includes(code_string, base_path=base_path)
        processed_code = preprocess_continuations(processed_includes)
        lexer = Lexer(processed_code)

        self.tokens = lexer.tokens
        self.token_index = 0

        self.labels = {}
        self.jump_map = {}
        self._pre_scan_for_jumps()
        self._scan_for_labels()

        output_html = io.StringIO()
        old_stdout = sys.stdout

        try:
            sys.stdout = output_html

            # --- MODIFIED: Catch the RedirectSignal ---
            try:
                while self._current_token():
                    if not self._parse_line() or self.program_terminated:
                        break
            except RedirectSignal as e:
                # Restore stdout before returning the signal
                sys.stdout = old_stdout
                return ('redirect', e.args[0])

            return output_html.getvalue()

        except ProgramEnd:
            return output_html.getvalue()
        finally:
            sys.stdout = old_stdout
            
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

    def _parse_execute_statement(self):
        self._expect('EXECUTE')
        sql_string = self._parse_expression()
        if not isinstance(sql_string, str):
            self._error("Argument for EXECUTE must be a string containing SQL statement(s).")
        
        # Set up error variables
        self.variables.update({'ERR': 0.0, 'ERRMSG$': "", 'SQL_ROWCOUNT': 0.0, 'SQL_FOUND': 0.0, 'SQL_NOTFOUND': -1.0})
        
        try:
            if self.db_engine == 'sqlite':
                # Split into individual statements
                statements = self._split_sql_statements(sql_string)
                
                for i, stmt in enumerate(statements):
                    if stmt.upper().startswith('SELECT') or stmt.upper().startswith('WITH') or stmt.upper().startswith('PRAGMA'):
                        # This is a query - execute normally to get results
                        results = self._execute_sql(stmt, is_query=True)
                        if results:
                            column_names = [desc[0] for desc in self.db_cursor.description] if self.db_cursor.description else []
                            self._handle_output(results, column_names)
                    else:
                        # This is a non-query statement
                        self._execute_sql(stmt, is_query=False)
                        
            elif self.db_engine == 'duckdb':
                # DuckDB can handle multiple statements - use existing logic
                self._execute_sql(sql_string)
            else:
                # Fallback
                self._execute_sql(sql_string)
                
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            if self.sql_fatal_errors:
                self._error(f"SQL execution error: {e}")
    
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
 
    def _execute_function(self, name, args):
        name = name.upper()
        if name == 'RND':
            if not args: return random.random()
            if len(args) == 1: max_val = int(args[0]); return float(random.randint(1, max_val)) if max_val >= 1 else self._error("RND arg must be >= 1")
            self._error("RND takes 0 or 1 arguments.")
        elif name == 'UBOUND':
            if len(args) != 1 or not isinstance(args[0], list): self._error("UBOUND requires one array argument.")
            return float(len(args[0]) - 1 if args[0] else -1)
        elif name == 'LEFT$': return str(args[0])[:int(args[1])]
        elif name == 'RIGHT$': return str(args[0])[-int(args[1]):]
        elif name == 'MID$': s, st = str(args[0]), int(args[1])-1; ln = int(args[2]) if len(args)==3 else len(s); return s[st:st+ln]
        elif name == 'UCASE$': return str(args[0]).upper()
        elif name == 'LCASE$': return str(args[0]).lower()
        elif name == 'CENTER$':
            if not (2 <= len(args) <= 3):
                self._error("CENTER$ requires 2 or 3 arguments: string$, width, [pad_char$].")
            
            source_str = str(args[0])
            width = int(args[1])
            pad_char = ' ' # Default padding character
            if len(args) == 3:
                pad_char = str(args[2])
                if len(pad_char) != 1:
                    self._error("Padding character for CENTER$ must be a single character.")

            return source_str.center(width, pad_char)
        elif name == 'EXTRACT$':
            # s$ = EXTRACT#(t$,2,";") -- return the 2nd argument (1-based) in a delimited string (default ,)
            if not (2 <= len(args) <= 3):
                self._error("EXTRACT$ requires 2 or 3 arguments: source_string$, position, [delimiter$].")
            
            source_str = str(args[0])
            position = int(args[1])
            
            # Conditionally set the delimiter
            if len(args) == 3:
                delimiter = str(args[2])
            else:
                delimiter = "," # Default to a comma if not provided

            # Ensure position is 1-based
            if position <= 0:
                return ""

            try:
                parts = source_str.split(delimiter)
                # Convert 1-based position to 0-based index
                return parts[position - 1]
            except IndexError:
                # Return an empty string if the position is out of bounds
                return ""
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
        elif name == 'ARRAY':
            # The 'args' parameter is already a Python list of the evaluated arguments.
            # We simply return it, and the interpreter will assign this new list
            # to the variable.
            return args
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
        elif name == 'PARSEJSON':
            if len(args) != 1:
                self._error("PARSEJSON function requires 1 argument: the JSON string.")
            
            json_string = str(args[0])
            if not json_string.strip():
                return {} # Return an empty hash for an empty string

            try:
                parsed_data = json.loads(json_string)
            except json.JSONDecodeError as e:
                self._error(f"Invalid JSON string: {e}")
            
            # Convert the Python object to the interpreter's internal HASH/ARRAY format
            return self._python_to_basic_data(parsed_data)
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
        elif name == 'NVL':
            if len(args) < 2:
                self._error("NVL requires at least 2 arguments.")
            for value in args:
                # This simple check correctly handles 0, 0.0, and "" as empty/"falsey" values
                if value:
                    return value
            # If the loop finishes, all arguments were empty. Return an empty string.
            return ""
            
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
        elif name == 'BASENAME$':
            if len(args) != 1: self._error("BASENAME$ requires 1 string argument.")
            path = str(args[0])
            return os.path.basename(path)
        elif name == 'PATHNAME$':
            if len(args) != 1: self._error("PATHNAME$ requires 1 string argument.")
            path = str(args[0])
            return os.path.dirname(path)
        elif name == 'URL_FILENAME$':
            if len(args) != 1: self._error("URL_FILENAME$ requires 1 string argument.")
            url = str(args[0])
            path = urlparse(url).path
            return os.path.basename(path)

        elif name == 'URL_PATH$':
            if len(args) != 1: self._error("URL_PATH$ requires 1 string argument.")
            url = str(args[0])
            path = urlparse(url).path
            return os.path.dirname(path)

        elif name == 'URL_HOSTNAME$':
            if len(args) != 1: self._error("URL_HOSTNAME$ requires 1 string argument.")
            url = str(args[0])
            return urlparse(url).hostname

        elif name == 'URL_SCHEME$':
            if len(args) != 1: self._error("URL_SCHEME$ requires 1 string argument.")
            url = str(args[0])
            return urlparse(url).scheme
        elif name == 'DATE$': return datetime.now().strftime('%Y-%m-%d')
        elif name == 'TIME$': return datetime.now().strftime('%H:%M:%S')
        elif name == 'DATEADD': return (self._parse_date_string(args[0]) + timedelta(days=int(args[1]))).strftime('%Y-%m-%d')
        elif name == 'DATEDIFF': return float((self._parse_date_string(args[0]) - self._parse_date_string(args[1])).days)
        elif name == 'YEAR': return float(self._parse_date_string(args[0]).year)
        elif name == 'MONTH': return float(self._parse_date_string(args[0]).month)
        elif name == 'MONTHNAME$':
            if len(args) != 1:
                self._error("MONTHNAME$ requires 1 argument: month_number.")
            try:
                month_num = int(args[0])
                if 1 <= month_num <= 12:
                    # calendar.month_name is a list where index 1 is "January"
                    return calendar.month_name[month_num]
                else:
                    self._error("Month number must be between 1 and 12.")
            except (ValueError, TypeError):
                self._error("Invalid month number provided to MONTHNAME$.")
        elif name == 'DAY': return float(self._parse_date_string(args[0]).day)
        elif name == 'WEEKDAY': return float((self._parse_date_string(args[0]).weekday() + 1) % 7 + 1)
        elif name == 'DAYSINMONTH':
            if len(args) != 2:
                self._error("DAYSINMONTH requires 2 arguments: month, year.")
            try:
                month = int(args[0])
                year = int(args[1])
                # calendar.monthrange returns (weekday of 1st day, num_days)
                num_days = calendar.monthrange(year, month)[1]
                return float(num_days)
            except (ValueError, TypeError):
                self._error("Invalid month or year provided to DAYSINMONTH.")
        elif name == 'DAYSINYEAR':
            if len(args) != 1:
                self._error("DAYSINYEAR requires 1 argument: year.")
            try:
                year = int(args[0])
                # Return 366.0 if it's a leap year, otherwise 365.0
                days = 366 if calendar.isleap(year) else 365
                return float(days)
            except (ValueError, TypeError):
                self._error("Invalid year provided to DAYSINYEAR.")
        elif name == 'ISLEAP':
            if len(args) != 1:
                self._error("ISLEAP requires 1 argument: year.")
            try:
                year = int(args[0])
                is_leap = calendar.isleap(year)
                return -1.0 if is_leap else 0.0
            except (ValueError, TypeError):
                self._error("Invalid year provided to ISLEAP.")
        elif name == 'MONTHCAL$':
            if len(args) != 2:
                self._error("MONTHCAL$ requires 2 arguments: year, month.")
            try:
                year = int(args[0])
                month = int(args[1])
                # calendar.month() returns a pre-formatted string
                return calendar.month(year, month)
            except (ValueError, TypeError):
                self._error("Invalid year or month provided to MONTHCAL$.")
        elif name == 'YEARCAL$':
            if len(args) != 1:
                self._error("YEARCAL$ requires 1 argument: year.")
            try:
                year = int(args[0])
                # calendar.calendar() returns the formatted string for the whole year
                return calendar.calendar(year)
            except (ValueError, TypeError):
                self._error("Invalid year provided to YEARCAL$.")
        elif name == 'FORMATDATE$':
            date_obj, format_mask = self._parse_date_string(args[0]), str(args[1]).upper()
            format_map = {'YYYY': '%Y', 'YY': '%y', 'MM': '%m', 'DD': '%d', 'HH': '%H', 'MI': '%M', 'SS': '%S'}
            py_format_str = format_mask
            for b, p in format_map.items(): py_format_str = py_format_str.replace(b, p)
            return date_obj.strftime(py_format_str)
        elif name == 'NOW':
            if len(args) != 0:
                self._error("NOW function takes no arguments.")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        elif name == 'HOUR' or name == 'MINUTE' or name == 'SECOND':
            if len(args) != 1:
                self._error(f"{name} requires 1 time string argument.")
            time_str = str(args[0])
            parts = time_str.split(':')
            try:
                if name == 'HOUR':
                    return float(parts[0]) if len(parts) >= 1 else 0.0
                elif name == 'MINUTE':
                    return float(parts[1]) if len(parts) >= 2 else 0.0
                elif name == 'SECOND':
                    return float(parts[2]) if len(parts) >= 3 else 0.0
            except (ValueError, IndexError):
                return 0.0

        elif name == 'DATESERIAL':
            if len(args) != 3:
                self._error("DATESERIAL requires 3 arguments: year, month, day.")
            try:
                year, month, day = int(args[0]), int(args[1]), int(args[2])
                return datetime(year, month, day).strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                self._error("Invalid arguments for DATESERIAL.")
        
        elif name == 'ISDATE':
            if len(args) != 1:
                self._error("ISDATE requires 1 string argument.")
            date_str = str(args[0])
            # Try a few common formats
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d', '%Y%m%d'):
                try:
                    datetime.strptime(date_str, fmt)
                    return -1.0 # BASIC True
                except ValueError:
                    continue
            return 0.0 # BASIC False

        elif name == 'WEEKDAYNAME$':
            if len(args) != 1:
                self._error("WEEKDAYNAME$ requires 1 argument: day_number (1-7 for Sun-Sat).")
            try:
                day_num = int(args[0])
                if not 1 <= day_num <= 7:
                    self._error("Day number must be between 1 (Sunday) and 7 (Saturday).")
                # Map from (Sun=1...Sat=7) to Python's calendar index (Mon=0...Sun=6)
                python_index = (day_num % 7) - 1 if day_num < 7 else 6
                return calendar.day_name[python_index]
            except (ValueError, TypeError):
                self._error("Invalid day number for WEEKDAYNAME$.")
        
        # --- String & Array Functions ---
        elif name == 'INSTRREV':
            if not (2 <= len(args) <= 3):
                self._error("INSTRREV requires 2 or 3 arguments: haystack$, needle$, [start].")
            haystack, needle = str(args[0]), str(args[1])
            start = len(haystack)
            if len(args) == 3:
                start = int(args[2])
            
            # Python's rfind returns -1 if not found, we need to return 0.
            # It also needs the end position, which is what 'start' means in InStrRev.
            pos = haystack.rfind(needle, 0, start)
            return float(pos + 1)

        elif name == 'FILTER':
            if not (2 <= len(args) <= 3):
                self._error("FILTER requires 2 or 3 arguments: array, criteria$, [include_flag].")
            
            source_array, criteria = args[0], str(args[1])
            include = True # Default to include matches
            if len(args) == 3:
                include = (args[2] != 0)

            if not isinstance(source_array, list):
                self._error("First argument to FILTER must be an array.")

            result_array = []
            for item in source_array:
                item_str = str(item)
                is_match = criteria in item_str
                if (is_match and include) or (not is_match and not include):
                    result_array.append(item)
            return result_array

        # --- Utility & Type Functions ---
        elif name == 'TYPENAME$':
            if len(args) != 1:
                self._error("TYPENAME$ requires 1 argument.")
            value = args[0]
            if isinstance(value, str):
                return "STRING"
            elif isinstance(value, (int, float)):
                return "FLOAT"
            elif isinstance(value, list):
                return "ARRAY"
            elif isinstance(value, dict):
                return "HASH"
            else:
                return "UNKNOWN"
        elif name == 'LEN': return float(len(str(args[0])))
        elif name == 'SPLIT':
            if not (2 <= len(args) <= 3): self._error("SPLIT requires 2 or 3 arguments.")
            source_str, delimiter_str = str(args[0]), str(args[1])
            if not delimiter_str: return list(source_str)
            if len(args) == 3: limit = int(args[2]); return source_str.split(delimiter_str, limit - 1) if limit > 0 else self._error("Limit must be > 0")
            return source_str.split(delimiter_str)
        elif name == 'SOUNDEX$':
            if len(args) != 1: 
                self._error("SOUNDEX$ requires one string argument.")
            # Reuse the existing logic from the SQL function implementation
            return SqliteStringFunctions.soundex(str(args[0]))
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
        elif name == 'ISNUMERIC':
            if len(args) != 1: self._error("ISNUMERIC requires 1 argument.")
            try:
                float(args[0])
                return -1.0 # True
            except (ValueError, TypeError):
                return 0.0 # False
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
        elif name == 'HTMLENCODE$':
            if len(args) != 1: self._error("HTMLENCODE$ requires one string argument.")
            return html.escape(str(args[0]))
        elif name == 'HTMLDECODE$':
            if len(args) != 1: self._error("HTMLDECODE$ requires one string argument.")
            return html.unescape(str(args[0]))
        elif name == 'URLENCODE$':
            if len(args) != 1: self._error("URLENCODE$ requires one string argument.")
            return quote_plus(str(args[0]))
        elif name == 'URLDECODE$':
            if len(args) != 1: self._error("URLDECODE$ requires one string argument.")
            return unquote_plus(str(args[0]))
        elif name == 'VAL': 
            try:
                # Attempt to convert the argument to a float
                return float(args[0])
            except (ValueError, TypeError):
                # If conversion fails (e.g., for an empty or non-numeric string), return 0.0
                return 0.0
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
            #print(f"DEBUG _parse_factor: Looking up '{var_name}', variables: {list(self.variables.keys())}")
            # Handle case-insensitive BASIC variable lookup
            actual_var_name = var_name
            if var_name not in self.variables:
                # Try to find existing variable with different case
                #print("DEBUG: var_name not in self.variables")
                found = False
                for existing_var in self.variables:
                    if existing_var.upper() == var_name.upper():
                        actual_var_name = existing_var
                        found = True
                        break
                if not found:
                    #print("DEBUG: var_name not found so creating new one")
                    # Variable doesn't exist, create with uppercase name
                    actual_var_name = var_name
                    if not (self._peek_token() and self._peek_token()[0] == 'LPAREN'):
                        self.variables[actual_var_name] = "" if var_name.endswith('$') else 0.0
            
            var_name = actual_var_name
            
            if var_name.upper() in ['DATE$', 'TIME$', 'FREEFILE', 'RND', 'CURDIR$'] and not (self._peek_token() and self._peek_token()[0] == 'LPAREN'):
                self._next_token(); 
                return self._execute_function(var_name, [])
            
            self._next_token()    
            #print("DEBUG: getting current_value, var_name=", var_name)            
            current_value = self._get_variable_value(var_name, auto_create=True)
            #print("DEBUG: current_value=", current_value)
            
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
                    #print("DEBUG:", self.variables)
                    if not isinstance(current_value, dict): self._error("Dot notation only for HASH.")
                    self._next_token()
                    key_token = self._current_token()
                    if not key_token:
                        self._error("Expected a key name after '.'")

                    key_name = ""
                    # It first checks for a generic ID as before.
                    if key_token[0] == 'ID':
                        self._next_token() 
                        key_name = key_token[1]
                    # If not an ID, it checks if it's an acceptable keyword.
                    elif key_token[0] not in self.INVALID_KEY_TOKENS:
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
        elif token[0] == 'ARRAY':
            # This handles the specific case of the ARRAY() constructor function.
            # The logic is a simplified version of a function call.
            function_name = self._expect('ARRAY')[1]
            self._expect('LPAREN')
            
            args = []
            if self._current_token()[0] != 'RPAREN':
                while True:
                    args.append(self._parse_expression())
                    if self._current_token()[0] == 'RPAREN': break
                    self._expect('COMMA')
            
            self._expect('RPAREN')
            return self._execute_function(function_name, args)
        else:
            self._error(f"Unexpected token in factor: {token}")
            print("\n--- TOKEN DUMP IN LEXER ---")
            for token in self.tokens:
                print(token)
            print("--------------------\n")     
            
    def _parse_power(self):
        res = self._parse_factor()
        while self._current_token() and self._current_token()[0] == 'CARET':
            self._next_token()
            right = self._parse_factor()
            res = pow(res, right)
        return res 
        
    def _parse_term(self):
        res = self._parse_power()
        while self._current_token() and self._current_token()[0] == 'OP' and self._current_token()[1] in '*/':
            op = self._current_token()[1]
            self._next_token()
            right = self._parse_power()
            try:
                # --- FIX: Convert both operands to numbers before the operation ---
                numeric_res = float(res)
                numeric_right = float(right)

                if op == '*':
                    # --- FIX: Perform numeric multiplication ---
                    res = numeric_res * numeric_right
                elif op == '/':
                    # --- FIX: Perform numeric division ---
                    res = numeric_res / numeric_right
            except ZeroDivisionError:
                raise RuntimeError("Division by zero")
            except (ValueError, TypeError):
                # --- FIX: Catch errors if a value can't be converted to a number ---
                raise RuntimeError(f"Type mismatch: cannot perform arithmetic on '{res}' and '{right}'.")
        return res
        
    def _parse_expression(self):
        res = self._parse_term()
        while self._current_token() and ((self._current_token()[0] == 'OP' and self._current_token()[1] in '+-') or self._current_token()[0] == 'AMPERSAND'):
            op_token = self._current_token()
            op = op_token[1]
            op_type = op_token[0]
            self._next_token()
            right = self._parse_term()
            
            if op == '+':
                # '+' is special: it means concatenation if either side is a string
                res = self._to_string(res) + self._to_string(right) if isinstance(res, str) or isinstance(right, str) else res + right
            elif op_type == 'AMPERSAND':
                # '&' ALWAYS concatenates strings
                res = self._to_string(res) + self._to_string(right)
            elif op == '-':
                # --- FIX: Subtraction should attempt numeric conversion ---
                try:
                    numeric_res = float(res)
                    numeric_right = float(right)
                    res = numeric_res - numeric_right
                except (ValueError, TypeError):
                    raise RuntimeError(f"Type mismatch: cannot perform subtraction on '{res}' and '{right}'.")
        return res
        
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
        if token and token[0] == 'IN':
            self._next_token()  # Consume 'IN'
            self._expect('LPAREN')

            # Case 1: Subquery, e.g., IN (SELECT ...)
            if self._current_token() and self._current_token()[0] == 'SQL_STRING':
                sql_query = self._expect('SQL_STRING')[1]
                self._expect('RPAREN')
                results = self._execute_sql(sql_query, is_query=True)
                # Flatten list of tuples into a set for efficient lookup
                value_set = {row[0] for row in results}
                is_member = left in value_set
                return -1.0 if is_member else 0.0
            
            # Case 2: Static list, e.g., IN ("a", "b", 123)
            else:
                value_list = []
                if self._current_token()[0] != 'RPAREN':
                    while True:
                        value_list.append(self._parse_expression())
                        if self._current_token()[0] == 'RPAREN':
                            break
                        self._expect('COMMA')
                self._expect('RPAREN')
                is_member = left in value_list
                return -1.0 if is_member else 0.0
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
        global g_null_handling_default
        self._expect('SET')
        token = self._current_token()
        
        if token[0] == 'ID' and token[1].upper() == 'NULL_HANDLING':
            self._next_token() # Consume NULL_HANDLING
            
            # Check if this is a global or column-specific setting
            if self._current_token() and self._current_token()[0] == 'FOR':
                # --- Column-Specific Setting ---
                self._next_token() # Consume FOR
                table_column_str = self._parse_expression()
                self._expect('TO')
                option_token = self._expect('ID')
                option = option_token[1].upper()

                if option not in ['NULL','CONVERT_EMPTY_TO_NULL', 'PRESERVE_EMPTY_STRINGS', 'EMPTY']:
                    self._error(f"Invalid option for NULL_HANDLING: {option}")

                g_null_handling_settings[table_column_str.upper()] = option
                print(f"Set null handling for '{table_column_str}' to '{option}'")
        elif token[0] == 'ID' and token[1].upper() == 'SQL_FATAL_ERRORS':
            self._next_token()
            setting_token = self._current_token()
            if not setting_token or setting_token[0] != 'ID' or setting_token[1].upper() not in ['ON', 'OFF']:
                self._error("Expected ON or OFF after SET SQL_FATAL_ERRORS")
            self.sql_fatal_errors = (setting_token[1].upper() == 'ON')
            self._next_token()

        elif token[0] == 'ID' and token[1].upper() == 'HASH_KEYS':
            self._next_token()
            mode_token = self._current_token()
            if not mode_token or mode_token[0] != 'ID' or mode_token[1].upper() not in ['PRESERVE_CASE', 'IGNORE_CASE']:
                self._error("Expected PRESERVE_CASE or IGNORE_CASE after SET HASH_KEYS")
            self.hash_keys_mode = mode_token[1].upper()
            self._next_token()

        elif token[0] == 'OUTPUT':
            self._next_token()
            token = self._current_token()
            
            if token and token[0] == 'ID' and token[1].upper() == 'FORMAT':
                g_output_config.mode = "CONSOLE"
            elif token and token[0] == 'ID':
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
            
            token = self._current_token()
            if token and token[0] == 'ID' and token[1].upper() == 'FORMAT':
                self._next_token()
                format_token = self._current_token()
                if format_token and format_token[0] in ['ID', 'TEXT', 'CSV', 'JSON', 'JSONL', 'XML', 'HTML', 'FIXED', "EXCEL", "SQL"]:
                    output_format = format_token[1].upper()
                    if output_format in ["TEXT", "CSV", "JSON", "JSONL", 'XML', "HTML", "FIXED", "EXCEL", "SQL"]: 
                        g_output_config.format = output_format
                        self._next_token()
                        
                        # Generic OPTIONS parsing for TEXT and SQL ---
                        g_output_config.sql_options = {} # Reset options for any format
                        
                        # Check for SQL-specific mode keywords first (for backward compatibility)
                        mode_keywords = ['INSERT', 'UPDATE', 'MERGE', 'REPLACE', 'UPSERT']
                        mode_token = self._current_token()
                        if output_format == 'SQL' and mode_token and mode_token[0] in mode_keywords:
                            g_output_config.sql_options['mode'] = mode_token[1].lower()
                            self._next_token()

                        # Now, check for the general OPTIONS clause for all formats
                        if self._current_token() and self._current_token()[0] == 'OPTIONS':
                            self._next_token()
                            options_str = self._parse_expression()
                            # Start with any already parsed options (like SQL mode)
                            temp_options = g_output_config.sql_options 
                            
                            key_matches = list(re.finditer(r'\b(\w+)=', options_str))
                            for i, match in enumerate(key_matches):
                                key = match.group(1).lower()
                                start_pos = match.end()
                                end_pos = key_matches[i+1].start() if i + 1 < len(key_matches) else len(options_str)
                                value = options_str[start_pos:end_pos].strip().strip(',').strip("'\"")
                                temp_options[key] = value
                            
                            g_output_config.sql_options = temp_options
                    else: 
                        self._error(f"Unknown format type '{output_format}'")
                else: 
                    self._error("Missing or invalid format type after FORMAT")


    def _handle_output(self, results, column_names):
        if g_output_config.mode == "CONSOLE":
            if g_output_config.format == "EXCEL":
                self._error("Excel output requires FILE mode. Use: SET OUTPUT FILE \"filename.xlsx\" FORMAT EXCEL")
                return
            writer_function = getattr(self, f"_write_as_{g_output_config.format.lower()}")
            writer_function(results, column_names, sys.stdout, g_output_config.sql_options)
        elif g_output_config.mode == "FILE":
            try:
                with open(g_output_config.file_path, "w", encoding="utf-8", newline='') as f:
                    writer_function = getattr(self, f"_write_as_{g_output_config.format.lower()}")
                    writer_function(results, column_names, f)
                print(f"{len(results)} rows written to {g_output_config.file_path}")
            except IOError as e: self._error(f"Error writing to file: {e}")

    def _write_as_text(self, results, headers, stream, options={}):
        if not results:
            stream.write("(0 rows returned)\n")
            return

        style = options.get('box_style', 'ASCII').upper()
        BOX_CHARS = {'h': '─', 'v': '│', 'tl': '┌', 'tc': '┬', 'tr': '┐', 'ml': '├', 'mc': '┼', 'mr': '┤', 'bl': '└', 'bc': '┴', 'br': '┘'}
        ASCII_CHARS = {'h': '-', 'v': '|', 'tl': '+', 'tc': '+', 'tr': '+', 'ml': '+', 'mc': '+', 'mr': '+', 'bl': '+', 'bc': '+', 'br': '+'}
        chars = BOX_CHARS if style == 'BOX' else ASCII_CHARS

        # --- FIX: Two-Pass Approach ---
        # --- Pass 1: Calculate column widths without storing data ---
        widths = {h: len(h) for h in headers}
        # The results object is a list of tuples, so we can iterate it multiple times
        for row in results:
            for i, h in enumerate(headers):
                if i < len(row):
                    cell_content = str(row[i]) if row[i] is not None else "NULL"
                    max_line_len = max(len(line) for line in cell_content.splitlines()) if cell_content else len("NULL")
                    widths[h] = max(widths[h], max_line_len)

        # --- Pass 2: Print the table, streaming the data ---
        def build_separator(left, join, right):
            parts = [chars['h'] * (widths[h] + 2) for h in headers]
            return f"{left}{join.join(parts)}{right}\n"

        # Print top border and header
        stream.write(build_separator(chars['tl'], chars['tc'], chars['tr']))
        header_parts = [f" {h:^{widths[h]}} " for h in headers]
        stream.write(f"{chars['v']}{chars['v'].join(header_parts)}{chars['v']}\n")
        stream.write(build_separator(chars['ml'], chars['mc'], chars['mr']))

        # Print data rows one by one
        for row in results:
            row_data = [(str(cell) if cell is not None else "NULL") for cell in row]
            cell_lines = [cell.splitlines() for cell in row_data]
            
            # Ensure empty cells are handled correctly for multi-line output
            for cell in cell_lines:
                if not cell: cell.append("")

            max_lines_in_row = max(len(lines) for lines in cell_lines) if any(cell_lines) else 1
            for i in range(max_lines_in_row):
                row_parts = [f" {(cell_lines[j][i] if i < len(cell_lines[j]) else ''):<{widths[h]}} " for j, h in enumerate(headers)]
                stream.write(f"{chars['v']}{chars['v'].join(row_parts)}{chars['v']}\n")

        # Print bottom border and row count
        stream.write(build_separator(chars['bl'], chars['bc'], chars['br']))
        stream.write(f"({len(results)} rows returned)\n")
        
    def _write_as_text_old(self, results, headers, stream, options={}):
        if not results:
            stream.write("(0 rows returned)\n")
            return

        # Define character sets based on the 'box_style' option
        style = options.get('box_style', 'ASCII').upper()
        
        BOX_CHARS = {'h': '─', 'v': '│', 'tl': '┌', 'tc': '┬', 'tr': '┐', 'ml': '├', 'mc': '┼', 'mr': '┤', 'bl': '└', 'bc': '┴', 'br': '┘'}
        ASCII_CHARS = {'h': '-', 'v': '|', 'tl': '+', 'tc': '+', 'tr': '+', 'ml': '+', 'mc': '+', 'mr': '+', 'bl': '+', 'bc': '+', 'br': '+'}
        
        chars = BOX_CHARS if style == 'BOX' else ASCII_CHARS

        # 1. Calculate column widths (without padding first)
        widths = {h: len(h) for h in headers}
        # Pre-process all data to strings to calculate widths accurately
        all_data_rows = []
        for row in results:
            data_row = []
            for i, h in enumerate(headers):
                cell_content = str(row[i]) if row[i] is not None else "NULL"
                data_row.append(cell_content)
                # Check width against all lines in a multi-line cell
                max_line_len = max(len(line) for line in cell_content.splitlines()) if cell_content else len("NULL")
                widths[h] = max(widths[h], max_line_len)
            all_data_rows.append(data_row)
        
        # 2. Helper to build separator lines with padding
        def build_separator(left, join, right):
            # Add 2 for padding: ' ' on each side
            parts = [chars['h'] * (widths[h] + 2) for h in headers]
            return f"{left}{join.join(parts)}{right}\n"
        
        # 3. Print top border
        stream.write(build_separator(chars['tl'], chars['tc'], chars['tr']))
        
        # 4. Print header (centered)
        header_parts = [f" {h:^{widths[h]}} " for h in headers]
        stream.write(f"{chars['v']}{chars['v'].join(header_parts)}{chars['v']}\n")

        # 5. Print header separator
        stream.write(build_separator(chars['ml'], chars['mc'], chars['mr']))

        # 6. Print data rows
        if not all_data_rows:
             # If there's no data, we still need to draw the bottom border.
             pass
        else:
            for row_data in all_data_rows:
                cell_lines = [cell.splitlines() for cell in row_data]
                for cell in cell_lines:
                    if not cell: cell.append("")

                max_lines_in_row = max(len(lines) for lines in cell_lines) if any(cell_lines) else 1

                for i in range(max_lines_in_row):
                    # Left-align content within the padded width
                    row_parts = [f" {(cell_lines[j][i] if i < len(cell_lines[j]) else ''):<{widths[h]}} " for j, h in enumerate(headers)]
                    stream.write(f"{chars['v']}{chars['v'].join(row_parts)}{chars['v']}\n")

        # 7. Print bottom border
        stream.write(build_separator(chars['bl'], chars['bc'], chars['br']))
        stream.write(f"({len(results)} rows returned)\n")

    def _write_as_csv(self, results, headers, stream, options={}):
        csv_writer = csv.writer(stream); csv_writer.writerow(headers); csv_writer.writerows(results)
    
    def _write_as_json(self, results, headers, stream, options={}):
        json.dump([dict(zip(headers, row)) for row in results], stream, indent=2)
    
    def _write_as_jsonl(self, results, headers, stream, options={}):
        for row in results: stream.write(json.dumps(dict(zip(headers, row))) + "\n")
    
    def _write_as_xml(self, results, headers, stream, options={}):
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
    
    def _write_as_html(self, results, headers, stream, options={}):
        """Writes query results as a basic HTML table."""
        is_full = options.get('full', '')
        if is_full:
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
            if is_full:
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
            if is_full:
                stream.write(f"<p style='text-align: center; font-style: italic;'>({len(results)} rows returned)</p>\n")

        if is_full:
            stream.write("</body>\n</html>\n")
        
    def _write_as_fixed(self, results, headers, stream, options={}):
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

    def _write_as_excel(self, results, headers, stream, options={}):
        """Writes query results as an Excel file."""
        # For Excel output, we need a file path, not a stream
        if g_output_config.mode == "CONSOLE":
            self._error("Excel output requires FILE mode. Use: SET OUTPUT FILE \"filename.xlsx\" FORMAT EXCEL")
            return
        
        filename = g_output_config.file_path
        if not filename.lower().endswith(('.xlsx', '.xls')):
            filename += '.xlsx'
        
        # Create a new workbook and worksheet
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Query Results"
        
        # Define styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # Write headers
        for col_idx, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # Write data rows
        for row_idx, row in enumerate(results, 2):
            for col_idx, value in enumerate(row, 1):
                # Handle None values
                if value is None:
                    value = ""
                # Convert to appropriate Excel data types
                elif isinstance(value, (int, float)):
                    # Keep numeric values as numbers
                    pass
                else:
                    # Convert everything else to string
                    value = str(value)
                
                worksheet.cell(row=row_idx, column=col_idx, value=value)
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Add freeze panes to keep headers visible
        worksheet.freeze_panes = "A2"
        
        # Save the workbook
        try:
            workbook.save(filename)
            #print(f"{len(results)} rows written to Excel file: {filename}")
        except Exception as e:
            self._error(f"Error writing Excel file: {e}")

    def _write_as_sql(self, results, headers, stream, options={}):
        if not results:
            stream.write("-- (0 rows returned)\n")
            return

        # 1. Determine the SOURCE table name for schema inspection.
        source_table_name = options.get('tablename')
        if not source_table_name:
            source_table_name = self._extract_table_from_select(self.last_sql_statement)

        # 2. Determine the TARGET table name for the output SQL.
        #    It defaults to the source table name if not explicitly provided.
        target_table_name = options.get('target_tablename', source_table_name)
        
        if not target_table_name:
            # We need at least a target table to generate SQL.
            self._error("FORMAT SQL requires a 'target_tablename' in OPTIONS or a simple FROM clause.")
            return
            
        vendor = options.get('vendor', self.db_engine).lower()    
        mode = options.get('mode', 'insert').lower()
        pk_column = options.get('pk')
        if not pk_column and mode in ('upsert', 'update', 'merge'):
            pk_column = self._get_primary_key(source_table_name) or "rowid"
            if not pk_column:
                self._error(f"Failed to auto-discover primary key for {source_table_name}: {e}")
                
        # --- Value formatting helper ---
        def format_value(value):
            if value is None: return "NULL"
            if isinstance(value, (int, float)): return str(value)
            # 1. Convert the original value to a string.
            string_value = str(value)
            
            # 2. Escape any single quotes by replacing them with two single quotes.
            escaped_string = string_value.replace("'", "''")
            
            # 3. Add the single quotes around the outside and return.
            return "'" + escaped_string + "'"

        if mode in ('insert', 'replace'):
            # This is the existing logic for INSERT and INSERT OR REPLACE
            command_prefix = f"INSERT OR REPLACE INTO {self._quote_identifier(target_table_name)}" if mode == 'replace' else f"INSERT INTO {self._quote_identifier(table_name)}"
            quoted_headers = ', '.join([self._quote_identifier(h) for h in headers])
            for row in results:
                values_str = ', '.join([format_value(v) for v in row])
                stream.write(f"{command_prefix} ({quoted_headers}) VALUES ({values_str});\n")

        elif mode == 'update':
            try:
                pk_index = [h.lower() for h in headers].index(pk_column.lower())
            except ValueError:
                self._error(f"Primary key '{pk_column}' not found in the SELECT statement's results.")
                return

            for row in results:
                pk_value = row[pk_index]
                set_clauses = []
                for i, header in enumerate(headers):
                    if i == pk_index: continue
                    set_clauses.append(f"{self._quote_identifier(header)} = {format_value(row[i])}")
                if not set_clauses:
                    set_clauses.append(f"{self._quote_identifier(pk_column)} = {format_value(pk_value)}")
                stream.write(f"UPDATE {self._quote_identifier(target_table_name)} SET {', '.join(set_clauses)} WHERE {self._quote_identifier(pk_column)} = {format_value(pk_value)};\n")

        elif mode == 'upsert':
            if not pk_column: self._error("mode='upsert' requires the 'pk' option to be set.")
            quoted_headers = ', '.join([self._quote_identifier(h) for h in headers])
            
            # --- START of Vendor-Specific Logic ---
            if vendor == 'mysql':
                # MySQL uses ON DUPLICATE KEY UPDATE
                update_clauses = [f"{self._quote_identifier(h)} = VALUES({self._quote_identifier(h)})" for h in headers if h.lower() != pk_column.lower()]
                for row in results:
                    values_str = ', '.join([format_value(v) for v in row])
                    stream.write(
                        f"INSERT INTO {self._quote_identifier(target_table_name)} ({quoted_headers}) VALUES ({values_str}) "
                        f"ON DUPLICATE KEY UPDATE {', '.join(update_clauses)};\n"
                    )
            else:
                # SQLite, DuckDB, and PostgreSQL use ON CONFLICT
                update_clauses = [f"{self._quote_identifier(h)} = excluded.{self._quote_identifier(h)}" for h in headers if h.lower() != pk_column.lower()]
                for row in results:
                    values_str = ', '.join([format_value(v) for v in row])
                    stream.write(
                        f"INSERT INTO {self._quote_identifier(target_table_name)} ({quoted_headers}) VALUES ({values_str}) "
                        f"ON CONFLICT ({self._quote_identifier(pk_column)}) DO UPDATE SET {', '.join(update_clauses)};\n"
                    )
            # --- END of Vendor-Specific Logic ---

        elif mode == 'merge':
            if not pk_column: self._error("mode=merge requires the 'pk' option to be set.")
            quoted_headers = ', '.join([self._quote_identifier(h) for h in headers])
            update_clauses = [f"T.{self._quote_identifier(h)} = S.{self._quote_identifier(h)}" for h in headers if h.lower() != pk_column.lower()]
            insert_s_cols = ', '.join([f"S.{self._quote_identifier(h)}" for h in headers])
            
            for row in results:
                values_str = ', '.join([format_value(v) for v in row])

                # --- START of Vendor-Specific Logic ---
                if vendor == 'oracle':
                    # Oracle uses SELECT ... FROM DUAL for the source
                    using_selects = [f"{format_value(row[i])} AS {self._quote_identifier(h)}" for i, h in enumerate(headers)]
                    using_clause = f"USING (SELECT {', '.join(using_selects)} FROM DUAL) S"
                else:
                    # SQL Server and DuckDB use VALUES
                    using_clause = f"USING (VALUES ({values_str})) AS S({quoted_headers})"
                # --- END of Vendor-Specific Logic ---

                merge_statement = (
                    f"MERGE INTO {self._quote_identifier(target_table_name)} T "
                    f"{using_clause} "
                    f"ON (T.{self._quote_identifier(pk_column)} = S.{self._quote_identifier(pk_column)}) "
                    f"\n   WHEN MATCHED THEN UPDATE SET {', '.join(update_clauses)} "
                    f"\n   WHEN NOT MATCHED THEN INSERT ({quoted_headers}) VALUES ({insert_s_cols});\n"
                )
                stream.write(merge_statement)
        
        else:
            self._error(f"Invalid mode '{mode}'. Use 'insert', 'replace', 'update', 'upsert', or 'merge'.")
                   
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

    def _to_string(self, value):
        """Converts a value to a string, formatting floats that are whole numbers as integers."""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
        
    def _format_output_value(self, value):
        # First, convert the number to the desired base string format ("1" not "1.0")
        string_value = self._to_string(value)
        
        # Then, apply PRINT's special rule: add a leading space for positive numbers
        if isinstance(value, (int, float)) and value >= 0:
            return " " + string_value
        return string_value
        
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

    def _dump_tokens(self):
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
            self._dump_tokens()
                
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
    
    def _parse_echo_statement(self):
        """
        Parses an ECHO statement. Assumes pre-processing has wrapped the
        content in a single STRING token.
        """
        self._expect('ECHO')

        # If ECHO is on a line by itself, print a blank line.
        if not self._current_token() or self._current_token()[0] in ['NEWLINE', 'COLON', 'END']:
            print()
            # Consume the NEWLINE token if it's there
            if self._current_token() and self._current_token()[0] == 'NEWLINE':
                self._next_token()
            return
        
        # The content is now a single, well-formed STRING token.
        token_value = self._expect('STRING')[1]
        
        # Un-escape the content: strip outer quotes and convert "" back to "
        output_string = token_value[1:-1].replace('""', '"')
        
        print(output_string)
        
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
            suppress_nl = False
            if self._current_token() and self._current_token()[0] == 'SEMICOLON':
                self._next_token()
                suppress_nl = True
            formatted_output = Formatter.format(format_string, values)
            if target == sys.stdout:
                print(formatted_output, end="" if suppress_nl else "\n")
            else:
                target.write(formatted_output)
                if not suppress_nl:
                    target.write('\n')
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
        self.variables['ERR'] = 0.0
        self._expect('FILES')
        
        path_arg = "."
        if self._current_token() and self._current_token()[0] not in ['NEWLINE', 'INTO', 'ID', 'WITH DETAILS', 'WITH FULLPATH', 'WITH FOLDERSONLY', 'WITH FILESONLY']:
            path_arg = self._parse_expression()

        into_array_name = None
        with_details, is_recursive, with_fullpath = False, False, False
        filter_mode = None # Can be 'folders' or 'files'
        
        while self._current_token() and self._current_token()[0] != 'NEWLINE':
            token_type = self._current_token()[0]
            token_value = self._current_token()[1].upper()

            if token_type == 'INTO':
                self._next_token(); into_array_name = self._expect('ID')[1]
                if into_array_name not in self.variables or not isinstance(self.variables.get(into_array_name), list):
                    self._error(f"'{into_array_name}' is not a dimensioned array.")
            elif token_type == 'WITH DETAILS':
                with_details = True; self._next_token()
            elif token_type == 'WITH FULLPATH':
                with_fullpath = True; self._next_token()
            elif token_type == 'ID' and token_value == 'RECURSIVE':
                is_recursive = True; self._next_token()
            elif token_type == 'WITH FOLDERSONLY':
                filter_mode = 'folders'; self._next_token()
            elif token_type == 'WITH FILESONLY':
                filter_mode = 'files'; self._next_token()
            else:
                break 

        if is_recursive:
            try:
                path_pattern = os.path.expanduser(str(path_arg))
                if os.path.isdir(path_pattern):
                    start_dir, pattern = path_pattern, '*'
                else:
                    start_dir, pattern = os.path.split(path_pattern)
                    if not start_dir: start_dir = '.'
                
                if not os.path.isdir(start_dir):
                    if into_array_name is None: print("Directory not found"); return

                found_items_for_array = []
                for dirpath, dirnames, filenames in os.walk(start_dir):
                    # Process directories if they are not being filtered out
                    if filter_mode != 'files':
                        for dirname in sorted(dirnames):
                            full_path = os.path.join(dirpath, dirname)
                            if into_array_name is None:
                                name_to_print = os.path.abspath(full_path) if with_fullpath else os.path.basename(full_path)
                                if with_details:
                                    try:
                                        stats = os.stat(full_path); size_str = "<DIR>"
                                        date_str = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                                        print(f"{name_to_print:<70}\t{size_str:>12}\t{date_str}")
                                    except OSError: continue
                                else:
                                    print(name_to_print)
                            else:
                                found_items_for_array.append(full_path)

                    # Process files if they are not being filtered out
                    if filter_mode != 'folders':
                        for filename in sorted(filenames):
                            if fnmatch.fnmatch(filename, pattern):
                                full_path = os.path.join(dirpath, filename)
                                if into_array_name is None:
                                    name_to_print = os.path.abspath(full_path) if with_fullpath else os.path.basename(full_path)
                                    if with_details:
                                        try:
                                            stats = os.stat(full_path); size_str = str(stats.st_size)
                                            date_str = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                                            print(f"{name_to_print:<70}\t{size_str:>12}\t{date_str}")
                                        except OSError: continue
                                    else:
                                        print(name_to_print)
                                else:
                                    found_items_for_array.append(full_path)
                
                if into_array_name is not None:
                    if with_details:
                        detailed_list = []
                        for fp in found_items_for_array:
                            try:
                                stats = os.stat(fp)
                                detailed_list.append({"name": os.path.abspath(fp) if with_fullpath else os.path.basename(fp),"size": float(stats.st_size),"date": datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),"isdir": -1.0 if os.path.isdir(fp) else 0.0})
                            except OSError: continue
                        self.variables[into_array_name] = detailed_list
                    else:
                        self.variables[into_array_name] = [os.path.abspath(p) if with_fullpath else os.path.basename(p) for p in found_items_for_array]
            except Exception as e:
                self._error(f"An error occurred during recursive file search: {e}")
        else:
            # --- NON-RECURSIVE PATH ---
            try:
                glob_pattern = os.path.expanduser(str(path_arg))
                if os.path.isdir(glob_pattern):
                    glob_pattern = os.path.join(glob_pattern, '*')
                
                file_list = sorted(glob.glob(glob_pattern))
                
                if filter_mode == 'files':
                    file_list = [p for p in file_list if os.path.isfile(p)]
                elif filter_mode == 'folders':
                    file_list = [p for p in file_list if os.path.isdir(p)]

                if into_array_name is None:
                    if not file_list: print("File not found"); return
                    if with_details:
                        name_width = 70 if with_fullpath else 25
                        for fp in file_list:
                            try:
                                name = os.path.abspath(fp) if with_fullpath else os.path.basename(fp)
                                stats = os.stat(fp)
                                date_str = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                                size_str = "<DIR>" if os.path.isdir(fp) else str(stats.st_size)
                                print(f"{name:<{name_width}}\t{size_str:>12}\t{date_str}")
                            except OSError: continue
                    else:
                        for fp in file_list:
                            print(os.path.abspath(fp) if with_fullpath else os.path.basename(fp))
                else:
                    if with_details:
                        detailed_list = []
                        for fp in file_list:
                            try:
                                stats = os.stat(fp)
                                detailed_list.append({"name": os.path.abspath(fp) if with_fullpath else os.path.basename(fp),"size": float(stats.st_size),"date": datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),"isdir": -1.0 if os.path.isdir(fp) else 0.0})
                            except OSError: continue
                        self.variables[into_array_name] = detailed_list
                    else: 
                        self.variables[into_array_name] = [os.path.abspath(p) if with_fullpath else os.path.basename(p) for p in file_list]
            except Exception as e:
                self._error(f"An error occurred during file search: {e}")              

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
                
    def _parse_for_in_files_loop(self):
        """Parses a FOR...IN FILES(...) loop to iterate over file paths, with optional keywords."""
        self._expect('FOR')
        loop_var_name = self._expect('ID')[1]
        self._expect('IN')
        self._expect('FILES')
        
        self._expect('LPAREN')
        pattern = self._parse_expression()
        
        # --- NEW: Parse all optional keywords inside the parentheses ---
        is_recursive = False
        with_fullpath = False
        filter_mode = None # Can be 'folders' or 'files'
        
        while self._current_token() and self._current_token()[0] != 'RPAREN':
            token_type = self._current_token()[0]
            token_value = self._current_token()[1].upper()

            if token_type == 'ID' and token_value == 'RECURSIVE':
                is_recursive = True; self._next_token()
            elif token_type == 'WITH FULLPATH':
                with_fullpath = True; self._next_token()
            elif token_type == 'WITH FOLDERSONLY':
                filter_mode = 'folders'; self._next_token()
            elif token_type == 'WITH FILESONLY':
                filter_mode = 'files'; self._next_token()
            else:
                self._error(f"Unexpected token '{self._current_token()[1]}' inside FILES().")
        
        self._expect('RPAREN')
        
        if not isinstance(pattern, str):
            self._error("Argument for FILES() in a FOR loop must be a string pattern.")
            
        try:
            glob_pattern = os.path.expanduser(str(pattern))
            if os.path.isdir(glob_pattern):
                wildcard = os.path.join('**', '*') if is_recursive else '*'
                glob_pattern = os.path.join(glob_pattern, wildcard)
            elif is_recursive and '**' not in glob_pattern:
                dir_part, file_part = os.path.split(glob_pattern)
                glob_pattern = os.path.join(dir_part, '**', file_part)
            
            file_list = sorted(glob.glob(glob_pattern, recursive=is_recursive))

            # --- NEW: Filter the results based on the chosen mode ---
            if filter_mode == 'files':
                file_list = [p for p in file_list if os.path.isfile(p)]
            elif filter_mode == 'folders':
                file_list = [p for p in file_list if os.path.isdir(p)]

        except Exception as e:
            self._error(f"Invalid pattern for FILES loop: {e}")

        loop_body_start_index = self.token_index
        original_value = self.variables.get(loop_var_name)

        try:
            if not file_list:
                self.token_index = loop_body_start_index
                self._skip_block('FOR', 'NEXT')
                return

            for filepath in file_list:
                value_to_assign = os.path.abspath(filepath) if with_fullpath else os.path.basename(filepath)
                self.variables[loop_var_name] = value_to_assign

                self.token_index = loop_body_start_index
                if self._current_token() and self._current_token()[0] == 'NEWLINE': self._next_token()
                self.run_block(end_tokens={'NEXT'})
                
                self._expect('NEXT')
                if self._current_token() and self._current_token()[0] == 'ID':
                    self._next_token()

        except LoopExit as e:
            if e.args[0] == 'FOR':
                self._skip_block('FOR', 'NEXT')
            else:
                raise e
        finally:
            if original_value is not None:
                self.variables[loop_var_name] = original_value
            elif loop_var_name in self.variables:
                del self.variables[loop_var_name]
                
                
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
    # In the Interpreter class

    def _parse_eval_statement(self):
        """Parses and executes a string of DbBasic code dynamically."""
        self._expect('EVAL')
        code_string = self._parse_expression()
        self._execute_basic_string(code_string)
    
    def _execute_basic_string(self, code_string):
        """A reusable helper to execute a string of DbBasic code."""
        if not isinstance(code_string, str):
            self._error("Argument for dynamic execution must be a string.")
        if not code_string.strip():
            return

        try:
            processed_code = preprocess_continuations(code_string + '\n')
            eval_lexer = Lexer(processed_code)
            
            eval_interpreter = Interpreter(eval_lexer,
                                           self.command_args,
                                           debug=self.debug_mode,
                                           shared_db_connection=self.db_connection)

            eval_interpreter.variables = self.variables
            eval_interpreter.file_handles = self.file_handles

            eval_interpreter.run()

        except Exception as e:
            self._error(f"Error during dynamic execution: {e}, code: {processed_code}")
            
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

    def _parse_unpack_statement(self):
        '''
        Create stand-alone variables from a hash.
        '''
        self._expect('UNPACK')
        hash_variable = self._parse_expression()

        if not isinstance(hash_variable, dict):
            self._error("UNPACK statement requires a HASH variable.")

        for key, value in hash_variable.items():
            if value is None:
                value = ""
            var_name = str(key).strip()
            
            # Skip keys that are not valid variable names
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var_name.rstrip('$')):
                continue

            # Strip any existing suffix to avoid duplication (e.g., name$$)
            base_var_name = var_name.rstrip('$')

            # Add the '$' suffix only if the value is a string
            if isinstance(value, str):
                final_var_name = f"{base_var_name}$"
            else:
                final_var_name = base_var_name
            
            # Use the existing helper to correctly create/overwrite the variable
            self._set_variable_value(final_var_name, value)
            
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
                    self._next_token(); hash_name = self._expect('ID')[1]
                    headers_hash = self.variables.get(hash_name)
                    if self._current_token() and self._current_token()[0] == 'LPAREN': 
                        self._next_token(); self._expect('RPAREN')
                else: self._error("Expected FILE or HEADERS after USING")
            else: self._error(f"Unexpected token '{clause[0]}' in FETCH statement")
        destination_token = self._current_token()
        if not destination_token: self._error("FETCH statement requires an INTO or TO FILE clause.")
        final_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        if headers_hash:
            final_headers.update(headers_hash) # User headers override defaults
        
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
                        files = {upload_file_info[0]: f}
                        response = requests.post(url, data=post_data_hash, headers=headers_hash, files=files, timeout=30)
                elif method == 'POST': response = requests.post(url, data=post_data_hash, headers=headers_hash, timeout=15)
                else: response = requests.get(url, headers=headers_hash, timeout=15)
                self.variables['ERR'] = float(response.status_code)
                try: self.variables[dest_var] = response.content.decode('utf-8')
                except UnicodeDecodeError: self.variables[dest_var] = "Binary data received"
            else: self._error("FETCH statement requires an INTO or TO FILE clause.")
        except FileNotFoundError: self.variables['ERR'] = -2.0
        except requests.exceptions.RequestException: self.variables['ERR'] = -1.0

    def _clean_and_deduplicate_headers(self, headers: List[str]) -> List[str]:
        """
        Takes a list of header strings and returns a new list where:
        1. Characters that conflict with quoting ([]) are removed.
        2. Duplicate names are made unique by appending a suffix (_2, _3, etc.).
        """
        final_headers = []
        header_counts = {}
        for header in headers:
            # Step 1: Perform minimal cleaning. Just remove characters that would break quoting.
            clean_header = str(header).replace('[', '').replace(']', '').strip()
            
            # Step 2: Check for duplicates and create a unique name.
            if clean_header in header_counts:
                header_counts[clean_header] += 1
                unique_header = f"{clean_header}_{header_counts[clean_header]}"
            else:
                unique_header = clean_header
            
            final_headers.append(unique_header)
            # Always update the count for the original clean name to track it.
            header_counts[clean_header] = header_counts.get(clean_header, 0) + 1
            
        return final_headers

    def _perform_batch_upsert(self, target_table, key_column, headers, data_iterator, batch_size=10000):
        """
        Performs a batch UPSERT using a temporary staging table with a highly-compatible
        two-step UPDATE-then-INSERT approach.
        """
        cursor = self.db_cursor
        
        staging_table = f"__staging_{target_table}_{random.randint(1000, 9999)}"
        quoted_headers = [self._quote_identifier(h) for h in headers]
        quoted_target_table = self._quote_identifier(target_table)
        quoted_staging_table = self._quote_identifier(staging_table)
        quoted_key_column = self._quote_identifier(key_column)

        cols_def = ', '.join([f"{h} TEXT" for h in quoted_headers])
        cursor.execute(f"CREATE TEMP TABLE {quoted_staging_table} ({cols_def});")

        try:
            # Step 1: Load all data into the staging table (same as before)
            insert_sql = f"INSERT INTO {quoted_staging_table} ({', '.join(quoted_headers)}) VALUES ({', '.join(['?'] * len(headers))});"
            batch = []
            total_rows_processed = 0
            for row in data_iterator:
                batch.append(row)
                total_rows_processed += 1
                if len(batch) >= batch_size:
                    cursor.executemany(insert_sql, batch)
                    batch = []
            if batch:
                cursor.executemany(insert_sql, batch)

            # --- NEW, MORE COMPATIBLE LOGIC ---

            # Step 2: UPDATE rows that already exist in the target table
            update_set_clauses = [f"{h} = (SELECT {h} FROM {quoted_staging_table} WHERE {quoted_staging_table}.{quoted_key_column} = {quoted_target_table}.{quoted_key_column})"
                                  for h in quoted_headers if h.lower() != quoted_key_column.lower()]
            
            if update_set_clauses: # Only run update if there are non-key columns
                update_sql = (
                    f"UPDATE {quoted_target_table} SET {', '.join(update_set_clauses)} "
                    f"WHERE {quoted_key_column} IN (SELECT {quoted_key_column} FROM {quoted_staging_table})"
                )
                #print("DEBUG:", update_sql)
                cursor.execute(update_sql)

            # Step 3: INSERT rows that are new
            insert_new_sql = (
                f"INSERT INTO {quoted_target_table} ({', '.join(quoted_headers)}) "
                f"SELECT {', '.join(quoted_headers)} FROM {quoted_staging_table} "
                f"WHERE {quoted_key_column} NOT IN (SELECT {quoted_key_column} FROM {quoted_target_table})"
            )
            #print("DEBUG:", insert_new_sql)
            cursor.execute(insert_new_sql)
            
            if self.db_engine == 'sqlite': self.db_connection.commit()
            
            return total_rows_processed

        finally:
            # Step 4: Clean up
            cursor.execute(f"DROP TABLE IF EXISTS {quoted_staging_table};")
        
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
   
    def _parse_load_destination_clause(self):
        """
        Parses the destination clause (CREATE TABLE or INTO TABLE) for a LOAD statement.
        Returns a dictionary containing the destination mode, target table,
        database mode (APPEND/TRUNCATE/UPSERT), and the key column for upserts.
        """
        dest_info = {
            'mode': None, 
            'target': None, 
            'db_mode': None, 
            'key_column': None
        }

        token = self._current_token()
        if not token:
            self._error("Expected CREATE TABLE or INTO TABLE clause after filename.")

        if token[0] == 'CREATE':
            dest_info['mode'] = 'CREATE_TABLE'
            self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE':
                self._next_token()
            dest_info['target'] = self._parse_table_name()

        elif token[0] == 'INTO':
            dest_info['mode'] = 'INTO_TABLE'
            self._next_token()
            if self._current_token() and self._current_token()[0] == 'TABLE':
                self._next_token()
            dest_info['target'] = self._parse_table_name()
            
            mode_token = self._current_token()
            if mode_token and mode_token[0] in ['APPEND', 'TRUNCATE', 'UPSERT']:
                dest_info['db_mode'] = mode_token[1].upper()
                self._next_token()

                if dest_info['db_mode'] == 'UPSERT':
                    if not (self._current_token() and self._current_token()[0] == 'USING'):
                        self._error("UPSERT mode requires a 'USING KEY' clause.")
                    self._next_token() # Consume USING
                    if not (self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'KEY'):
                        self._error("Expected KEY after USING.")
                    self._next_token() # Consume KEY
                    dest_info['key_column'] = self._parse_expression()
            else: 
                self._error("Expected APPEND, TRUNCATE, or UPSERT for INTO TABLE clause.")
        else: 
            self._error("Expected CREATE TABLE or INTO TABLE clause after filename.")

        return dest_info

    def _parse_load_options(self):
        """
        Parses an optional OPTIONS "key=value, key2=value2" clause.
        Returns a dictionary of the parsed options with lowercase keys.
        If no OPTIONS clause is present, returns an empty dictionary.
        """
        parsed_options = {}
        if not (self._current_token() and self._current_token()[0] == 'OPTIONS'):
            return parsed_options # No options clause, return empty dict

        self._next_token() # Consume OPTIONS
        options_str = self._parse_expression()
        
        if not isinstance(options_str, str):
            self._error("Argument for OPTIONS must be a string.")

        # Use regex to find all "key=" patterns to correctly split values
        key_matches = list(re.finditer(r'\b(\w+)=', options_str))
        for i, match in enumerate(key_matches):
            key = match.group(1).lower()
            start_pos = match.end()
            
            # The value is everything from the end of the current match to the start of the next one
            end_pos = key_matches[i+1].start() if i + 1 < len(key_matches) else len(options_str)
            
            # Clean up the extracted value
            value = options_str[start_pos:end_pos].strip().strip(',')
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1].replace('""', '"')
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1].replace("''", "'")
                
            parsed_options[key] = value

        return parsed_options
     
    def _csv_extractor(self, filename, options):
        """
        Extractor for CSV files. Yields headers first, then a dict for each data row.
        """
        with open(filename, 'r', newline='', encoding=options.get('encoding', 'utf-8')) as infile:
            # Handle delimiter sniffing
            delimiter = options.get('delimiter', 'auto')
            if delimiter == 'auto':
                try:
                    sample = infile.read(8192)
                    infile.seek(0)
                    delimiter = csv.Sniffer().sniff(sample).delimiter
                except csv.Error:
                    delimiter = ',' # Default if sniffing fails

            # Handle skipping initial lines
            skip = int(options.get('skip', 0))
            for _ in range(skip):
                try:
                    next(infile)
                except StopIteration:
                    break

            reader = csv.reader(infile, delimiter=delimiter)

            # Determine and yield headers
            headers = []
            header_option = options.get('header', 'auto')
            has_header = False
            if header_option == 'auto':
                try:
                    sample = ""
                    for i, line in enumerate(infile):
                        if i >= 5: break
                        sample += line
                    infile.seek(0) # Rewind fully after sampling
                    # Re-skip lines
                    for _ in range(skip): next(infile)
                    has_header = csv.Sniffer().has_header(sample)
                except csv.Error:
                    has_header = False
            else:
                has_header = str(header_option).lower() in ['true', '1', 'y']

            if has_header:
                try:
                    headers = next(reader)
                except StopIteration:
                    pass # Handle empty file
            else:
                # If no header, we must peek at the first data row to find column count
                try:
                    first_row = next(reader)
                    headers = [f"C{i+1}" for i in range(len(first_row))]
                    # Since we consumed the first row, we need to manually yield it later
                    # A cleaner way is to combine generators, but this is simpler for now.
                    # We'll reset and re-read, which is slightly inefficient but robust.
                    infile.seek(0)
                    for _ in range(skip): next(infile)
                    reader = csv.reader(infile, delimiter=delimiter)
                except StopIteration:
                    pass

            yield {'type': 'headers', 'data': headers}

            # --- Yield each data row ---
            row_num = 0
            limit = int(options.get('limit', -1))
            for row in reader:
                if limit != -1 and row_num >= limit:
                    break
                
                yield {
                    'type': 'data',
                    'data': row,
                    'physical_line_num': reader.line_num,
                    'logical_line_num': row_num + 1
                }
                row_num += 1
 
    def _excel_extractor(self, filename, options):
        """
        Extractor for Excel files (.xls, .xlsx). Yields headers, then a dict for each data row.
        """
        try:
            workbook = xlrd3.open_workbook(filename)
            sheet = None

            # --- 1. Select the correct sheet ---
            sheet_name_opt = options.get('sheetname')
            if sheet_name_opt:
                # Find sheet by name, case-insensitively
                target_sheet_name = sheet_name_opt.lower()
                sheet_names_lower = [name.lower() for name in workbook.sheet_names()]
                if target_sheet_name in sheet_names_lower:
                    sheet = workbook.sheet_by_index(sheet_names_lower.index(target_sheet_name))
                else:
                    self._error(f"Excel file '{filename}' does not have a sheet named '{sheet_name_opt}'.")
            else:
                # Default to the sheet index specified, or the very first sheet
                sheet_index = int(options.get('sheetindex', 0))
                if sheet_index >= workbook.nsheets:
                    self._error(f"Excel sheet index {sheet_index} is out of bounds.")
                sheet = workbook.sheet_by_index(sheet_index)

            # --- 2. Determine and yield headers ---
            start_row = int(options.get('skip', 0))
            has_header = str(options.get('header', 'true')).lower() in ['true', '1', 'y']
            
            headers = []
            if has_header:
                if start_row < sheet.nrows:
                    # Clean up header names and generate fallbacks for empty cells
                    raw_headers = [str(sheet.cell_value(start_row, col)) for col in range(sheet.ncols)]
                    for i, header in enumerate(raw_headers):
                        cleaned_header = header.strip()
                        headers.append(cleaned_header if cleaned_header else f"C{i+1}")
                    start_row += 1 # Move to the first data row
                # If file is empty or only has skipped rows, headers will be empty
            else:
                # No header row, so generate default column names
                if sheet.ncols > 0:
                    headers = [f"C{i+1}" for i in range(sheet.ncols)]
            
            yield {'type': 'headers', 'data': headers}

            # --- 3. Yield each data row ---
            row_num = 0
            limit = int(options.get('limit', -1))
            for row_idx in range(start_row, sheet.nrows):
                if limit != -1 and row_num >= limit:
                    break

                # Convert all cell values to strings, handling different types from xlrd3
                data_row = []
                for col_idx in range(sheet.ncols):
                    cell_value = sheet.cell_value(row_idx, col_idx)
                    # Convert floats that are whole numbers (e.g., 123.0) to clean integers
                    if isinstance(cell_value, float) and cell_value.is_integer():
                        data_row.append(str(int(cell_value)))
                    else:
                        data_row.append(str(cell_value) if cell_value is not None else "")
                
                yield {
                    'type': 'data',
                    'data': data_row,
                    'physical_line_num': row_idx + 1, # Excel rows are 1-based for users
                    'logical_line_num': row_num + 1
                }
                row_num += 1

        except FileNotFoundError:
            self._error(f"File not found: {filename}")
        except xlrd3.biffh.XLRDError as e:
            self._error(f"Error reading Excel file '{filename}': {e}")
            
    def _fixed_extractor(self, filename, options):
        """
        Extractor for fixed-width text files. Yields headers, then data rows.
        Requires a 'fields' option specifying column names and positions (e.g., "ID:1-5,Name:6-20").
        """
        fields_spec = options.get('fields')
        if not fields_spec:
            self._error("LOAD FIXED requires a 'fields' option specifying column positions.")

        field_definitions = []
        try:
            for field_def in fields_spec.split(','):
                name, positions = field_def.strip().split(':', 1)
                start, end = positions.split('-', 1)
                # Convert from 1-based inclusive to 0-based exclusive for Python slicing
                start_pos = int(start.strip()) - 1
                end_pos = int(end.strip())
                field_definitions.append({'name': name.strip(), 'start': start_pos, 'end': end_pos})
        except ValueError as e:
            self._error(f"Invalid 'fields' specification for LOAD FIXED: {e}")

        # --- 1. Yield headers from the parsed field definitions ---
        headers = [field['name'] for field in field_definitions]
        yield {'type': 'headers', 'data': headers}

        # --- 2. Open file and yield each data row ---
        try:
            with open(filename, 'r', encoding=options.get('encoding', 'utf-8')) as infile:
                skip = int(options.get('skip', 0))
                for _ in range(skip):
                    next(infile)

                row_num = 0
                limit = int(options.get('limit', -1))
                
                # Use enumerate to get the physical line number
                for i, line in enumerate(infile, start=skip + 1):
                    if limit != -1 and row_num >= limit:
                        break
                    
                    line = line.rstrip('\n\r')
                    
                    # Skip blank lines in the source file
                    if not line.strip():
                        continue

                    record = [line[field['start']:field['end']].strip() for field in field_definitions]
                    
                    yield {
                        'type': 'data',
                        'data': record,
                        'physical_line_num': i,
                        'logical_line_num': row_num + 1
                    }
                    row_num += 1
        except FileNotFoundError:
            self._error(f"File not found: {filename}")
           
    def _jsonl_extractor(self, filename, options):
        """
        Extractor for JSON Lines files (.jsonl). Yields headers, then a dict for each data row.
        Headers are inferred by sampling the first N records.
        """
        try:
            # --- 1. Infer headers by sampling the file ---
            sample_size = int(options.get('samplesize', 1000))
            headers = []
            seen_keys = set()
            with open(filename, 'r', encoding=options.get('encoding', 'utf-8')) as infile:
                for i, line in enumerate(infile):
                    if i >= sample_size:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if isinstance(record, dict):
                            for key in record:
                                if key not in seen_keys:
                                    seen_keys.add(key)
                                    headers.append(key)
                    except json.JSONDecodeError:
                        continue # Ignore invalid JSON in the sample

            yield {'type': 'headers', 'data': headers}

            # --- 2. Open file again and yield each data row ---
            with open(filename, 'r', encoding=options.get('encoding', 'utf-8')) as infile:
                skip = int(options.get('skip', 0))
                for _ in range(skip):
                    next(infile)

                row_num = 0
                limit = int(options.get('limit', -1))
                
                for i, line in enumerate(infile, start=skip + 1):
                    if limit != -1 and row_num >= limit:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)
                        if not isinstance(record, dict):
                            print(f"Warning: Skipping non-object JSON on line {i}", file=sys.stderr)
                            continue
                        
                        # Build the row in the same order as the inferred headers
                        data_row = []
                        for h in headers:
                            val = record.get(h)
                            if isinstance(val, float) and val.is_integer():
                                data_row.append(str(int(val)))
                            elif isinstance(val, (dict, list)):
                                data_row.append(json.dumps(val))
                            else:
                                data_row.append(str(val) if val is not None else "")

                        yield {
                            'type': 'data',
                            'data': data_row,
                            'physical_line_num': i,
                            'logical_line_num': row_num + 1
                        }
                        row_num += 1

                    except json.JSONDecodeError:
                        print(f"Warning: Skipping invalid JSON on line {i}", file=sys.stderr)
                        continue

        except FileNotFoundError:
            self._error(f"File not found: {filename}")

    def _text_extractor(self, filename, options):
        """
        Extractor for plain text files. Yields a single-column record for each line.
        """
        try:
            # --- 1. Determine headers ---
            add_line_num = str(options.get('linenum', 'false')).lower() in ['true', '1', 'y']
            headers = ['line_text']
            if add_line_num:
                headers.append('_linenum')
            
            yield {'type': 'headers', 'data': headers}

            # --- 2. Open file and yield each data row ---
            with open(filename, 'r', encoding=options.get('encoding', 'utf-8'), errors='replace') as infile:
                skip = int(options.get('skip', 0))
                for _ in range(skip):
                    next(infile)

                skip_blank = str(options.get('skipblank', 'false')).lower() in ['true', '1', 'y']
                row_num = 0
                limit = int(options.get('limit', -1))

                for i, line in enumerate(infile, start=skip + 1):
                    if limit != -1 and row_num >= limit:
                        break
                    
                    line_content = line.rstrip('\n\r')

                    # Handle skipping blank lines within the extractor
                    if skip_blank and not line_content.strip():
                        continue

                    data_row = [line_content]
                    if add_line_num:
                        data_row.append(i)
                    
                    yield {
                        'type': 'data',
                        'data': data_row,
                        'physical_line_num': i,
                        'logical_line_num': row_num + 1
                    }
                    row_num += 1

        except FileNotFoundError:
            self._error(f"File not found: {filename}")
 
    def _html_extractor(self, filename, options):
        """
        Extractor for HTML files. Can extract tables, links, or images.
        Uses the 'element_type' option ('TABLES', 'LINKS', 'IMAGES').
        """
        try:
            with open(filename, 'r', encoding=options.get('encoding', 'utf-8')) as infile:
                soup = BeautifulSoup(infile, 'lxml')

            element_type = options.get('element_type', 'TABLES').upper()
            source_url = options.get('source_url', filename)
            
            add_line_num = str(options.get('linenum', 'false')).lower() in ['true', '1', 'y']

            if element_type == 'TABLES':
                tables = soup.find_all('table')
                table_index = int(options.get('table_index', 0))
                if table_index >= len(tables):
                    self._error(f"HTML table index {table_index} is out of bounds.")
                
                target_table = tables[table_index]
                headers = ['source']
                has_header = str(options.get('header', 'true')).lower() in ['true', '1', 'y']
                
                rows = target_table.find_all('tr')
                start_row_idx = 0
                if has_header and rows:
                    header_cells = rows[0].find_all(['th', 'td'])
                    headers.extend([cell.get_text(strip=True) for cell in header_cells])
                    start_row_idx = 1

                # --- FIX: Add _linenum to headers if requested ---
                if add_line_num:
                    headers.append('_linenum')

                yield {'type': 'headers', 'data': self._clean_and_deduplicate_headers(headers)}

                for i, row_element in enumerate(rows[start_row_idx:]):
                    cells = row_element.find_all('td')
                    data_row = [source_url] + [cell.get_text(strip=True) for cell in cells]
                    
                    # --- FIX: Append the line number to the data row ---
                    if add_line_num:
                        data_row.append(i + 1)

                    yield {'type': 'data', 'data': data_row, 'physical_line_num': 0, 'logical_line_num': i + 1}

            elif element_type == 'LINKS':
                headers = ['source', 'text', 'href']
                if add_line_num: headers.append('_linenum')
                yield {'type': 'headers', 'data': headers}
                
                links = soup.find_all('a', href=True)
                for i, link in enumerate(links):
                    data_row = [source_url, link.get_text(strip=True), link.get('href')]
                    if add_line_num: data_row.append(i + 1)
                    yield {'type': 'data', 'data': data_row, 'physical_line_num': 0, 'logical_line_num': i + 1}

            elif element_type == 'IMAGES':
                headers = ['source', 'src', 'alt', 'title']
                if add_line_num: headers.append('_linenum')
                yield {'type': 'headers', 'data': headers}

                images = soup.find_all('img', src=True)
                for i, img in enumerate(images):
                    data_row = [source_url, img.get('src'), img.get('alt', ''), img.get('title', '')]
                    if add_line_num: data_row.append(i + 1)
                    yield {'type': 'data', 'data': data_row, 'physical_line_num': 0, 'logical_line_num': i + 1}
            else:
                self._error(f"Unsupported 'element_type' for LOAD HTML: {element_type}")

        except FileNotFoundError:
            self._error(f"File not found: {filename}")
            
    def _execute_load_pipeline(self, filename, dest_info, options, extractor_func):
        """
        Handles the generic TRANSFORM and LOAD parts of the ETL process.
        """
        try:
            extractor = extractor_func(filename, options)

            # --- Get headers from the first yield of the extractor ---
            header_info = next(extractor)
            original_headers = header_info['data']

            # --- 1. Parse Transform and Validate Rules from Options ---
            transform_rules = {}
            transform_spec = options.get('transform')
            if transform_spec:
                for rule in transform_spec.split(';'):
                    parts = rule.strip().split(':')
                    if len(parts) == 2:
                        col_name = parts[0].strip().strip('[]')
                        func_def = parts[1].strip()
                        transform_rules[col_name.lower()] = func_def
                    elif len(parts) == 1:
                        transform_rules[parts[0].lower()] = True
            #print("DEBUG: TRANSFORM RULES:", transform_rules)
            validation_rules = {}
            validate_spec = options.get('validate')
            if validate_spec:
                for rule_group in validate_spec.split(';'):
                    parts = rule_group.strip().split(':', 1)
                    if len(parts) == 2:
                        col_name, rule_defs = parts[0].strip('[]'), parts[1]
                        validation_rules[col_name] = rule_defs.split(':')

            # --- 2. Generic Field Mapping (`FIELDS` clause) ---
            final_headers, column_map = original_headers, list(range(len(original_headers)))

            if dest_info['load_type'] in ['CSV', 'EXCEL', 'JSONL']: 
                fields_spec = options.get('fields')
                if fields_spec:
                    field_specs = fields_spec.split(',')
                    header_lookup = {h.lower(): i for i, h in enumerate(original_headers)}
                    new_headers, new_map = [], []

                    for spec in field_specs:
                        spec = spec.strip()
                        original_name = spec
                        new_name = spec

                        if ':' in spec:
                            original_name, new_name = spec.split(':', 1)
                            original_name = original_name.strip()
                            new_name = new_name.strip()
                            if not new_name:
                                new_name = original_name
                        if original_name.lower() not in header_lookup:
                            self._error(f"Field '{original_name}' not found in source headers.")

                        new_map.append(header_lookup[original_name.lower()])
                        new_headers.append(new_name)
                    
                    final_headers, column_map = new_headers, new_map
            
            if transform_rules:
                # Get a lowercase set of all headers that will be in the final table
                final_header_set = {h.lower() for h in final_headers}
                
                # Check each column mentioned in the transform rules
                for col_name in transform_rules.keys():
                    # The keys in transform_rules are already lowercase
                    # Exclude global rules like 'trimall' from this check
                    if col_name not in final_header_set and col_name not in ['trimall', 'upperall', 'lowerall', 'properall']:
                        print(f"Warning: TRANSFORM rule for column '{col_name}' will have no effect because no such column exists in the final field list.", file=sys.stderr)


            # --- Prepare script from options ---
            process_script = None
            if options.get('process_by'):
                script_var = options['process_by']
                if script_var not in self.variables or not isinstance(self.variables.get(script_var), str):
                    self._error(f"PROCESS_BY variable '{script_var}' not found or not a string.")
                process_script = self.variables[script_var]

            # --- Generic Database Setup ---
            cursor = self.db_cursor
            if dest_info['mode'] == 'CREATE_TABLE':
                if self._table_exists(dest_info['target']):
                    self._error(f"Table '{dest_info['target']}' already exists. Use INTO TABLE ... TRUNCATE to overwrite.")
                cols_def = ', '.join([f"{self._quote_identifier(h)} {'INTEGER' if h == '_linenum' else 'TEXT'}" for h in final_headers])
                cursor.execute(f"CREATE TABLE {self._quote_identifier(dest_info['target'])} ({cols_def});")
            
            if dest_info.get('db_mode') == 'TRUNCATE':
                cursor.execute(f"DELETE FROM {self._quote_identifier(dest_info['target'])};")

            # --- Reusable Row Processing Generator ---
            def process_rows(row_extractor):
                for row_info in row_extractor:
                    raw_row = row_info['data']
                    processed_row = [raw_row[i] for i in column_map if i < len(raw_row)]

                    # --- 3. Apply TRANSFORM Rules ---
                    if transform_rules:
                        if transform_rules.get('trimall'):
                            processed_row = [str(field).strip() if field is not None else '' for field in processed_row]
                        if transform_rules.get('upperall'):
                            processed_row = [str(field).upper() if field is not None else '' for field in processed_row]

                        if transform_rules.get('lowerall'):
                            processed_row = [str(field).lower() if field is not None else '' for field in processed_row]

                        if transform_rules.get('properall'):
                            processed_row = [str(field).title() if field is not None else '' for field in processed_row]

                        for i, header_name in enumerate(final_headers):
                            rule = transform_rules.get(header_name.lower())
                            if rule and i < len(processed_row):
                                val = str(processed_row[i]) if processed_row[i] is not None else ''
                                #print("DEBUG:",header_name.lower(),rule,val)
                                # --- NEW: Logic for the FORMAT AND ROUND rule ---
                                format_match = re.match(r"format\((.*)\)", str(rule), re.IGNORECASE)
                                round_match = re.match(r"round\((\d+)\)", str(rule), re.IGNORECASE)
                                date_match = re.match(r"date\((.*),(.*)\)", str(rule), re.IGNORECASE)
                                
                                if format_match:
                                    format_mask = format_match.group(1)
                                    # (The quote-stripping logic remains here)
                                    if (format_mask.startswith("'") and format_mask.endswith("'")) or \
                                       (format_mask.startswith('"') and format_mask.endswith('"')):
                                        format_mask = format_mask[1:-1]

                                    # First, try to treat the value as a number
                                    try:
                                        value_to_format = float(val.strip())
                                    except (ValueError, TypeError):
                                        # If it's not a number, use the original string
                                        value_to_format = val
                                    
                                    # Now, call the formatter with the correctly typed value
                                    formatted_val = Formatter.format(format_mask, [value_to_format])
                                    processed_row[i] = formatted_val.strip()
                                
                                elif round_match:
                                    num_decimals = int(round_match.group(1))
                                    try:
                                        # Treat empty or whitespace-only strings as 0.0
                                        numeric_val = float(val.strip()) if val.strip() else 0.0
                                        # Use a simple f-string for clean numeric formatting
                                        processed_row[i] = f"{numeric_val:.{num_decimals}f}"
                                    except (ValueError, TypeError):
                                        # If it's not a number (e.g., "N/A"), default to a formatted zero
                                        processed_row[i] = f"{0.0:.{num_decimals}f}"

                                elif date_match: 
                                    in_format_str = date_match.group(1).strip().upper()
                                    out_format_str = date_match.group(2).strip().upper()
                                    
                                    format_map = {
                                        'YYYY': '%Y', 'YY': '%y', 'MM': '%m', 'DD': '%d',
                                        'HH': '%H', 'MI': '%M', 'SS': '%S'
                                    }
                                     # Define an explicit order to prevent incorrect substring replacement (e.g., 'YYYY' becoming '%y%y')
                                    replace_order = ['YYYY', 'YY', 'MM', 'DD', 'HH', 'MI', 'SS']

                                    py_in_format = in_format_str
                                    py_out_format = out_format_str
                                    for key in replace_order:
                                        if key in format_map:
                                            py_in_format = py_in_format.replace(key, format_map[key])
                                            py_out_format = py_out_format.replace(key, format_map[key])
                                    try:
                                        if val.strip():
                                            date_obj = None
                                            # First, try to parse with the full format string
                                            try:
                                                date_obj = datetime.strptime(val.strip(), py_in_format)
                                            except ValueError:
                                                # If that fails, AND the format contains a time part (indicated by a space),
                                                # try parsing again with just the date part of the format string.
                                                if ' ' in in_format_str:
                                                    date_part_format = py_in_format.split(' ')[0]
                                                    try:
                                                        date_obj = datetime.strptime(val.strip(), date_part_format)
                                                    except ValueError:
                                                        pass # If this also fails, we give up and leave the original value
                                            
                                            if date_obj:
                                                processed_row[i] = date_obj.strftime(py_out_format)
                                    except (TypeError):
                                        pass
                                
                                elif rule is True: # Handles global rules like trimall
                                    pass
                                elif rule == 'upper': processed_row[i] = val.upper()
                                elif rule == 'lower': processed_row[i] = val.lower()
                                elif rule == 'trim': processed_row[i] = val.strip()
                                elif rule == 'proper': processed_row[i] = val.title()

                                
                    # --- 4. Apply Validation Rules ---
                    is_row_valid = True
                    if validation_rules:
                        # Create a dictionary of the current row's data for easy lookup by column name
                        row_dict = dict(zip(final_headers, processed_row))
                        
                        for col_name, rules in validation_rules.items():
                            if col_name in row_dict:
                                val = str(row_dict[col_name]) # Ensure value is a string for checks
                                
                                for rule in rules:
                                    # Use regex to parse rules like "MINLENGTH(10)" into name and argument
                                    match = re.match(r'(\w+)(?:\((.*)\))?', rule.strip())
                                    if not match: continue
                                    
                                    rule_name, rule_arg = match.groups()
                                    rule_name = rule_name.upper()
                                    
                                    # The REQUIRED rule is the only one that checks empty strings
                                    if rule_name == 'REQUIRED':
                                        if not val.strip():
                                            print(f"Validation failed on line {row_info['physical_line_num']}: Column '{col_name}' is REQUIRED but is empty.", file=sys.stderr)
                                            is_row_valid = False
                                    
                                    # Other rules should only apply to non-empty values
                                    elif val.strip():
                                        if rule_name == 'ISINTEGER':
                                            try:
                                                int(val)
                                            except ValueError:
                                                print(f"Validation failed on line {row_info['physical_line_num']}: Column '{col_name}' value '{val}' is not an integer.", file=sys.stderr)
                                                is_row_valid = False
                                        
                                        elif rule_name == 'ISNUMERIC':
                                            try:
                                                float(val)
                                            except ValueError:
                                                print(f"Validation failed on line {row_info['physical_line_num']}: Column '{col_name}' value '{val}' is not a number.", file=sys.stderr)
                                                is_row_valid = False

                                        elif rule_name == 'MINLENGTH':
                                            if len(val) < int(rule_arg):
                                                print(f"Validation failed on line {row_info['physical_line_num']}: Column '{col_name}' value '{val}' (length {len(val)}) is shorter than min length {rule_arg}.", file=sys.stderr)
                                                is_row_valid = False

                                        elif rule_name == 'MAXLENGTH':
                                            if len(val) > int(rule_arg):
                                                print(f"Validation failed on line {row_info['physical_line_num']}: Column '{col_name}' value '{val}' (length {len(val)}) is longer than max length {rule_arg}.", file=sys.stderr)
                                                is_row_valid = False

                                        elif rule_name == 'IN':
                                            valid_values = {item.strip() for item in rule_arg.split(',')}
                                            if val not in valid_values:
                                                print(f"Validation failed on line {row_info['physical_line_num']}: Column '{col_name}' value '{val}' is not in the allowed set {valid_values}.", file=sys.stderr)
                                                is_row_valid = False

                                        elif rule_name == 'REGEX':
                                            if not re.match(rule_arg, val):
                                                print(f"Validation failed on line {row_info['physical_line_num']}: Column '{col_name}' value '{val}' does not match pattern '{rule_arg}'.", file=sys.stderr)
                                                is_row_valid = False
                                    
                                    # If any rule for this column fails, stop checking other rules for it
                                    if not is_row_valid:
                                        break
                            
                            # If any column has failed, stop checking other columns for this row
                            if not is_row_valid:
                                break
                    
                    # If the row is invalid, skip it entirely
                    if not is_row_valid:
                        continue

                    # --- 5. Apply PROCESS_BY Script ---
                    if process_script:
                        rec_hash = dict(zip(final_headers, processed_row))
                        self.variables['rec'] = rec_hash
                        self.variables['physical_line_num'] = float(row_info['physical_line_num'])
                        self.variables['logical_line_num'] = float(row_info['logical_line_num'])
                        self._execute_basic_string(process_script)
                        updated_rec = self.variables.get('rec', {})
                        del self.variables['rec'], self.variables['physical_line_num'], self.variables['logical_line_num']

                        if updated_rec.get('is_valid', -1.0) == 0.0:
                            continue
                        processed_row = [updated_rec.get(h) for h in final_headers]

                    yield processed_row
            
            # --- Generic Database Loading ---
            row_iterator = process_rows(extractor)
            
            if dest_info.get('db_mode') == 'UPSERT':
                key_column = dest_info['key_column']
                if not key_column: self._error("UPSERT mode requires a 'key_column' to be specified.")
                if key_column not in final_headers: self._error(f"UPSERT key column '{key_column}' not found in final headers.")
                
                total_rows = self._perform_batch_upsert(dest_info['target'], key_column, final_headers, row_iterator)
                print(f"{total_rows} records upserted into table {dest_info['target']}")

            else: # APPEND or TRUNCATE logic
                batchsize = int(options.get('batchsize', 10000))
                insert_sql = f"INSERT INTO {self._quote_identifier(dest_info['target'])} ({', '.join([self._quote_identifier(h) for h in final_headers])}) VALUES ({', '.join(['?'] * len(final_headers))})"
                batch = []
                total_rows = 0
                self.db_connection.execute('BEGIN TRANSACTION;')
                try:
                    for processed_row in row_iterator:
                        batch.append(processed_row)
                        total_rows += 1
                        if len(batch) >= batchsize:
                            cursor.executemany(insert_sql, batch)
                            batch = []
                    
                    if batch: cursor.executemany(insert_sql, batch)
                    self.db_connection.execute('COMMIT;')
                    print(f"{total_rows} records loaded into table {dest_info['target']}")
                except Exception as e:
                    self.db_connection.execute('ROLLBACK;')
                    raise e
            
        except FileNotFoundError:
            self._error(f"File not found: {filename}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during the LOAD operation: {e}")

    def _parse_load_statement(self):
        """
        New master function to handle all LOAD commands.
        """
        self._expect('LOAD')
        token = self._current_token()
        valid_load_types = {'CSV', 'EXCEL', 'FIXED', 'JSON', 'JSONL', 'XML', 'HTML', 'TEXT'}

        if not token or token[0] not in valid_load_types:
            self._error(f"Expected a valid LOAD type (e.g., CSV, EXCEL) but got '{token[0] if token else 'None'}'.")
        
        load_type = token[1].upper()
        self._next_token() # Consume the type token (e.g., CSV)

        refactored_types = {'CSV', 'EXCEL', 'FIXED', 'JSONL', 'TEXT', 'HTML'}
        if load_type in refactored_types:
            # Define which extractor to use for each file type
            extractor_map = {
                'CSV': self._csv_extractor,
                'EXCEL': self._excel_extractor,
                'FIXED': self._fixed_extractor,
                'JSONL': self._jsonl_extractor,
                'TEXT': self._text_extractor,
                'HTML': self._html_extractor,
                # Add xxxxx: self._xxxxxx_extractor, etc. here
            }

            if load_type not in extractor_map:
                self._error(f"Unsupported LOAD type: {load_type}")

            # --- All common parsing happens here ---
            filename = self._parse_expression()
            
            # You can move the destination and options parsing into helper methods
            dest_info = self._parse_load_destination_clause() 
            dest_info['load_type'] = load_type 
            options = self._parse_load_options()

            # Get the correct extractor function for the specified file type
            extractor_func = extractor_map[load_type]

            # --- Hand off to the unified pipeline ---
            self._execute_load_pipeline(filename, dest_info, options, extractor_func)
        else:
            if load_type == 'JSON':
                self._parse_load_json_statement()
            elif load_type == 'XML':
                self._parse_load_xml_statement()           

    def _parse_load_json_normalize(self, json_filename, root_table='main'):
        """Normalizes JSON data into multiple related tables."""

        # Parse options (defaults)
        options = {
            'max_depth': 5,
            'array_threshold': 5,
            'prefix': '',
            'drop_existing': True,
            'batchsize': 1000,
            'keep_objects': False,
            'keep_arrays': False,
        }

        # Allow user overrides (from OPTIONS token)
        if self._current_token() and self._current_token()[0] == 'OPTIONS':
            self._next_token()
            options_str = self._parse_expression()

            # Parse key=value pairs
            for match in re.finditer(r'(\w+)\s*=\s*([^,\s]+)', options_str):
                key, value = match.groups()
                key = key.lower()

                if key == 'max_depth':
                    options['max_depth'] = int(value)
                elif key == 'array_threshold':
                    options['array_threshold'] = int(value)
                elif key == 'prefix':
                    options['prefix'] = value.strip('"\'')
                elif key == 'drop_existing':
                    options['drop_existing'] = value is None or value.lower() in ['true', '1', 'yes']
                elif key == 'batchsize':
                    options['batchsize'] = int(value)
                elif key == 'keep_objects':
                    options['keep_objects'] = value is None or value.lower() in ['true', '1', 'yes']
                elif key == 'keep_arrays':
                    options['keep_arrays'] = value is None or value.lower() in ['true', '1', 'yes']

        try:
            # Load JSON file
            with open(json_filename, 'r', encoding='utf-8') as infile:
                data = json.load(infile)

            # Ensure list of records
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                self._error("JSON file must contain an array of objects or a single object.")
                return
            if not data:
                print("0 records loaded (JSON is empty).")
                return

            # Initialize the new normalizer
            normalizer = JSONToSQLiteNormalizer(
                db_path=":memory:",
                root_table=root_table,
                array_threshold=options['array_threshold'],
                keep_objects=options['keep_objects'],
                keep_arrays=options['keep_arrays'],
            )
            if self.db_connection is not None:
                # Close the temporary connection to avoid leaving it open
                normalizer.conn.close()
                # Now, use the interpreter's main database connection
                normalizer.conn = self.db_connection
                normalizer.cursor = self.db_connection.cursor()

            normalizer.load_json(data)

            print(f"JSON normalization complete:")
            print(f"  - Processed {len(data)} root records")

            # Report tables and row counts
            self.db_connection.commit()
            
            tables = self._get_table_list()
            print(f"  - Created {len(tables)} tables:")
            for table in tables:
                self.db_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = self.db_cursor.fetchone()[0]
                print(f"    * {table}: {count} records")

        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {json_filename}")
        except json.JSONDecodeError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, f"JSON parsing error: {e}"
            self._error(f"JSON parsing error: {e}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during JSON normalization: {e}")
            
    def _parse_load_json_statement(self):
        """Loads a JSON file (array of objects) into a database table with data type inference."""
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        #self._expect('LOAD')
        #self._expect('JSON')

        # --- 1. PARSE CLAUSES ---
        json_filename = self._parse_expression()
        destination_mode, destination_target, db_mode = None, None, None

        dest_info = self._parse_load_destination_clause()
        destination_mode = dest_info["mode"]
        destination_target = dest_info["target"]
        db_mode = dest_info["db_mode"]
        key_column = dest_info["key_column"]

        if self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'NORMALIZE':
            self._next_token()
            return self._parse_load_json_normalize(json_filename, destination_target)
        
        options = {
            'batchsize': 10000, 'fields': '', 'transform': '', 'skip': 0, 
            'limit': None, 'trimall': False,'upperall': False,'lowerall': False,'properall': False, 'process_by': None
        }
        add_line_num = False
        process_script = None
        temp_options = self._parse_load_options()
        options.update(temp_options)

        for key, value in temp_options.items():
            if key in ['batchsize', 'skip', 'limit']:
                options[key] = int(value)
            elif key == 'linenum':
                add_line_num = value is None or value.lower() in ['true', 'y', '1']
            elif key in ('trimall', 'upperall', 'lowerall', 'properall'):
                options[key] = value is None or value.lower() in ['true', 'y', '1']
            else:
                options[key] = value
        # --- 2. READ AND PROCESS DATA ---
        try:
            with open(json_filename, 'r', encoding='utf-8') as infile:
                data = json.load(infile)

            if isinstance(data, dict): data = [data]
            if not isinstance(data, list): self._error("JSON file must contain an array or a single object."); return
            if not data: print("0 records loaded (JSON is empty)."); return
            
            # --- Schema Inference ---
            inferred_headers, seen_keys, col_types = [], set(), {}
            for record in data:
                if not isinstance(record, dict): self._error("Elements of the JSON array must be objects.")
                for key, value in record.items():
                    if key not in seen_keys:
                        seen_keys.add(key); inferred_headers.append(key); col_types[key] = 'INTEGER'
                    
                    current_type = col_types[key]
                    if value is None or current_type == 'TEXT': continue
                    if isinstance(value, str): col_types[key] = 'TEXT'
                    elif isinstance(value, float): col_types[key] = 'REAL'
                    elif not isinstance(value, int): col_types[key] = 'TEXT'

            # --- Process Fields and Transforms ---
            original_headers = inferred_headers
            final_headers = original_headers
            header_key_map = {h: h for h in original_headers}

            if options['fields']:
                field_specs = re.split(r',\s*(?![^\[]*\])', options['fields'])
                header_lookup = {h.lower(): h for h in original_headers}
                new_headers, new_key_map = [], {}
                for spec in field_specs:
                    match = re.match(r'\[([^\]]*)\](?:\s+as\s+([\w\d_]+))?', spec.strip(), re.IGNORECASE)
                    if not match: self._error(f"Invalid FIELDS specification: {spec}")
                    original_name, new_name = match.groups()
                    if original_name.lower() not in header_lookup:
                        self._error(f"Field '{original_name}' not found in JSON keys.")
                    original_key_cased = header_lookup[original_name.lower()]
                    final_field_name = new_name or original_key_cased
                    new_headers.append(final_field_name)
                    new_key_map[final_field_name] = original_key_cased
                final_headers = new_headers
                header_key_map = new_key_map
            
            if options['process_by']:
                script_var_name = options['process_by']
                if script_var_name not in self.variables or not isinstance(self.variables.get(script_var_name), str):
                    self._error(f"Script variable '{script_var_name}' for PROCESS_BY not found or not a string.")
                process_script = self.variables[script_var_name]
            
            transform_rules = {}
            if options.get('transform'):
                for rule in options['transform'].split(','):
                    parts = rule.strip().split(':')
                    if len(parts) == 2:
                        col_name, func_name = parts
                        transform_rules[col_name.lower()] = func_name.lower()
                    elif len(parts) == 1:
                        transform_rules[parts[0].lower()] = True
            
            # --- Database Operations ---
            cursor = self.db_cursor
            if destination_mode == 'CREATE_TABLE':
                if self._table_exists(destination_target):
                    self._error(f"Table '{destination_target}' already exists. Use INTO TABLE ... REPLACE to overwrite its contents.")
                cols_def = ', '.join([f'{self._quote_identifier(h)} {col_types.get(header_key_map.get(h, h), "TEXT")}' for h in final_headers])
                cursor.execute(f'CREATE TABLE {self._quote_identifier(destination_target)} ({cols_def});')

            if db_mode == 'TRUNCATE':
                cursor.execute(f'DELETE FROM {self._quote_identifier(destination_target)};')

            placeholders = ', '.join(['?'] * len(final_headers))
            quoted_headers = ', '.join([f'{self._quote_identifier(h)}' for h in final_headers])
            insert_sql = f'INSERT INTO {self._quote_identifier(destination_target)} ({quoted_headers}) VALUES ({placeholders});'
            
            batch_size = options['batchsize']
            total_rows_processed = 0
            
            self.db_connection.execute('BEGIN TRANSACTION;')
            try:
                batch = []
                for record in data:
                    processed_row = []
                    for h in final_headers:
                        original_key = header_key_map[h]
                        value = record.get(original_key)
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        processed_row.append(value)
                    
                    # Apply processing script if specified
                    if process_script:
                        # Create 'rec' hash for the current row
                        rec_hash = dict(zip(data_headers, processed_row))
                        self.variables['rec'] = rec_hash

                        # Execute the user's script
                        self._execute_basic_string(process_script)

                        # Check validation and retrieve modified data
                        updated_rec = self.variables.get('rec', {})
                        if updated_rec.get('is_valid', -1.0) == 0.0:
                            del self.variables['rec']
                            line_counter += 1
                            continue  # Skip this row

                        # Rebuild row from modified hash
                        processed_row = [updated_rec.get(h) for h in data_headers]
                        del self.variables['rec']

                    if transform_rules.get('trimall') or options.get('trimall'): 
                        processed_row = [str(field).strip() if field is not None else None for field in processed_row]
                    if transform_rules.get('upperall') or options.get('upperall'): 
                        processed_row = [str(field).upper() if field is not None else None for field in processed_row]
                    if transform_rules.get('lowerall') or options.get('lowerall'): 
                        processed_row = [str(field).lower() if field is not None else None for field in processed_row]
                    if transform_rules.get('properall') or options.get('properall'): 
                        processed_row = [str(field).title() if field is not None else None for field in processed_row]
                    
                    for i, header_name in enumerate(final_headers):
                        rule = transform_rules.get(header_name.lower())
                        if rule and isinstance(rule, str) and i < len(processed_row) and processed_row[i] is not None:
                            original_value = str(processed_row[i])
                            if rule == 'upper': processed_row[i] = original_value.upper()
                            elif rule == 'lower': processed_row[i] = original_value.lower()
                            elif rule == 'proper': processed_row[i] = original_value.title()
                            elif rule == 'trim': processed_row[i] = original_value.strip()

                    batch.append(processed_row)
                    total_rows_processed += 1
                    if options.get('limit', None) and total_rows_processed >= options.get('limit')*1:
                            break
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

        
    def _parse_load_xml_statement(self):
        """Loads data from an XML file into a database table using a streaming parser."""
        from collections import Counter # Local import for this specific function
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        #self._expect('LOAD')
        #self._expect('XML')

        # --- 1. Parse Clauses ---
        xml_filename = self._parse_expression()
        dest_info = self._parse_load_destination_clause()
        destination_mode = dest_info["mode"]
        destination_target = dest_info["target"]
        db_mode = dest_info["db_mode"]
        key_column = dest_info["key_column"]

        if self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'NORMALIZE':
            self._next_token()
            return self._parse_load_xml_normalize(xml_filename, destination_target)

        # --- 2. Parse Options ---
        options = {'record_tag': None, 'fields': None, 'batchsize': 10000, 'transform': ''}
        temp_options = self._parse_load_options()
        options.update(temp_options)

        try:
            # --- 3. Infer Structure (Record Tag and All Available Fields) ---
            record_tag = options.get('record_tag')
            is_single_record_mode = False
            
            tree = ET.parse(xml_filename)
            root = tree.getroot()
            
            if not record_tag:
                if len(root) == 0: self._error("Cannot infer 'record_tag': XML file has an empty root element.")
                child_tags = [child.tag for child in root]
                tag_counts = Counter(child_tags)
                all_tags_are_unique = all(count == 1 for count in tag_counts.values())

                if all_tags_are_unique and len(child_tags) > 1:
                    record_tag = root.tag
                    is_single_record_mode = True
                elif 'row' in child_tags: record_tag = 'row'
                elif 'record' in child_tags: record_tag = 'record'
                else: record_tag, _ = tag_counts.most_common(1)[0]
                print(f"Notice: 'record_tag' not specified. Inferred '<{record_tag}>'.", file=sys.stderr)

            if is_single_record_mode:
                inferred_fields = [child.tag for child in root]
            else:
                first_record_element = root.find(record_tag)
                if first_record_element is None: self._error(f"Could not find any elements with the tag '<{record_tag}>'.")
                inferred_fields = [child.tag for child in first_record_element]
            
            if not inferred_fields: self._error(f"Inferred record tag '<{record_tag}>' has no child elements to use as fields.")
            if not options['fields']: print(f"Notice: 'fields' not specified, inferred columns: {', '.join(inferred_fields)}", file=sys.stderr)

            # --- 4. Process Fields and Transforms ---
            # 1. Create a map from the clean name to the original, full namespaced tag
            header_key_map = {re.sub(r'\{.*\}', '', tag): tag for tag in inferred_fields}
            
            # 2. The final headers for the table are the clean keys from our new map
            final_headers = list(header_key_map.keys())
            original_headers = final_headers

            if options['fields']:
                field_specs = re.split(r',\s*(?![^\[]*\])', options['fields'])
                header_lookup = {h.lower(): h for h in original_headers}
                new_headers, new_key_map = [], {}
                for spec in field_specs:
                    match = re.match(r'\[([^\]]*)\](?:\s+as\s+([\w\d_]+))?', spec.strip(), re.IGNORECASE)
                    if not match: self._error(f"Invalid FIELDS specification: {spec}")
                    
                    original_name, new_name = match.groups()
                    if original_name.lower() not in header_lookup:
                        self._error(f"Field '{original_name}' not found in inferred XML tags.")
                    
                    original_key_cased = header_lookup[original_name.lower()]
                    final_field_name = new_name or original_key_cased
                    
                    new_headers.append(final_field_name)
                    new_key_map[final_field_name] = original_key_cased
                
                final_headers = new_headers
                header_key_map = new_key_map

            transform_rules = {}
            if options.get('transform'):
                for rule in options['transform'].split(','):
                    parts = rule.strip().split(':')
                    if len(parts) == 2:
                        col_name, func_name = parts
                        transform_rules[col_name.lower()] = func_name.lower()
                    elif len(parts) == 1:
                        transform_rules[parts[0].lower()] = True
                        
            # --- 5. Database Setup ---
            cursor = self.db_cursor
            if destination_mode == 'CREATE_TABLE':
                if self._table_exists(destination_target):
                    self._error(f"Table '{destination_target}' already exists. Use INTO TABLE ... REPLACE to overwrite its contents.")
                cols_def = ', '.join([f'{self._quote_identifier(h)} TEXT' for h in final_headers])
                #print("DEBUG: LOAD XML, Table Name=", destination_target, "QUOTED:", self._quote_identifier(destination_target))
                #print("DEBUG: LOAD XML, Column Names=", cols_def)
                cursor.execute(f'CREATE TABLE {self._quote_identifier(destination_target)} ({cols_def});')

            if db_mode == 'TRUNCATE':
                cursor.execute(f'DELETE FROM {self._quote_identifier(destination_target)};')

            # --- 6. Stream and Load Data ---
            placeholders = ', '.join(['?'] * len(final_headers))
            quoted_headers = ', '.join([f'{self._quote_identifier(h)}' for h in final_headers])
            insert_sql = f'INSERT INTO {self._quote_identifier(destination_target)} ({quoted_headers}) VALUES ({placeholders});'
            
            self.db_connection.execute('BEGIN TRANSACTION;')
            try:
                batch = []
                total_rows_processed = 0
                context = ET.iterparse(xml_filename, events=('end',))
                for _, element in context:
                    if element.tag == record_tag:
                        processed_row = []
                        for h in final_headers:
                            original_tag = header_key_map.get(h, h)
                            child_element = element.find(original_tag)
                            
                            if child_element is not None:
                                # If the element has children of its own, it's complex
                                if len(child_element) > 0 or child_element.attrib:
                                    # Serialize the complex element to a JSON string
                                    value = json.dumps(self._xml_element_to_dict(child_element))
                                else:
                                    # Otherwise, it's a simple element, just get its text
                                    value = child_element.text or ""
                            else:
                                value = "" # Handle missing tags
                            processed_row.append(value)

                        
                        if transform_rules.get('trimall'):
                            processed_row = [str(field).strip() for field in processed_row]
                        if transform_rules.get('upperall'):
                            processed_row = [str(field).upper() for field in processed_row]
                        if transform_rules.get('lowerall'):
                            processed_row = [str(field).lower() for field in processed_row] 
                        if transform_rules.get('properall'):
                            processed_row = [str(field).title() for field in processed_row] 
                        
                        for i, header_name in enumerate(final_headers):
                            rule = transform_rules.get(header_name.lower())
                            if rule and isinstance(rule, str) and i < len(processed_row):
                                original_value = str(processed_row[i])
                                if rule == 'upper': processed_row[i] = original_value.upper()
                                elif rule == 'lower': processed_row[i] = original_value.lower()
                                elif rule == 'proper': processed_row[i] = original_value.title()
                                elif rule == 'trim': processed_row[i] = original_value.strip()

                        batch.append(processed_row)
                        total_rows_processed += 1
                        if options.get('limit', None) and total_rows_processed >= options.get('limit')*1:
                            break
                        if len(batch) >= options['batchsize']:
                            cursor.executemany(insert_sql, batch)
                            batch = []
                        
                        element.clear()
                
                if batch: cursor.executemany(insert_sql, batch)
                self.db_connection.execute('COMMIT;')
                print(f"{total_rows_processed} records loaded into table {destination_target}")

            except Exception as e:
                self.db_connection.execute('ROLLBACK;'); raise e

        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {xml_filename}")
        except ET.ParseError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, f"XML parsing error: {e}"
            self._error(f"XML parsing error: {e}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during XML load: {e}")

    def _value_converter(self, value):
        """Tries to convert a string value to int or float."""
        if not isinstance(value, str): return value
        try:
            # If it contains a decimal, it's a float. Otherwise, try integer.
            return float(value) if '.' in value else int(value)
        except (ValueError, TypeError):
            return value # Not a number, return the original string

    def _xml_element_to_dict(self, element):
        """A helper that recursively converts an XML element to a dictionary."""
        node = {}
        # Convert attributes (attributes are always kept as strings)
        for key, value in element.attrib.items():
            node[f"@{key}"] = value

        # Convert child elements
        for child in element:
            child_dict = self._xml_element_to_dict(child)
            if child.tag in node:
                if not isinstance(node[child.tag], list):
                    node[child.tag] = [node[child.tag]]
                node[child.tag].append(child_dict)
            else:
                node[child.tag] = child_dict
        
        text = element.text.strip() if element.text else ""

        if not node and not element.attrib:
            # This is a leaf node (like <id>1</id>). Convert its value.
            return self._value_converter(text)

        if text:
            # This is mixed content. Convert the text part.
            node['#text'] = self._value_converter(text)

        return node
        

    def _parse_load_xml_normalize(self, xml_filename, root_table_name='main'):
        """Converts an XML file to a list of dicts and uses the JSON normalizer."""
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        
        from collections import Counter # Local import
        
        try:
            tree = ET.parse(xml_filename)
            root = tree.getroot()

            if len(root) == 0:
                self._error("Cannot normalize: XML file has an empty root or is not record-oriented.")
            
            # Heuristic: The most frequent tag directly under the root is the "record" tag.
            child_tags = [child.tag for child in root]
            tag_counts = Counter(child_tags)
            record_tag, _ = tag_counts.most_common(1)[0]
            print(f"Notice: Inferred record tag '<{record_tag}>' for normalization.", file=sys.stderr)

            list_of_records = []
            for record_element in root.findall(record_tag):
                record_dict = self._xml_element_to_dict(record_element)
                list_of_records.append(record_dict)

            if not list_of_records:
                print("0 records found to normalize.")
                return
            #print("DEBUG:","Running Normalizers on data", file=sys.stderr)
            # --- Reuse the existing JSON Normalizer ---
            normalizer = JSONToSQLiteNormalizer(
                db_path=":memory:",
                root_table=root_table_name or 'main',
            )
            if self.db_connection is not None:
                normalizer.conn.close()
                normalizer.conn = self.db_connection
                normalizer.cursor = self.db_connection.cursor()
            #print("DEBUG:", "Running load_json on data:", list_of_records, file=sys.stderr)
            normalizer.load_json(list_of_records)
            
            # --- Reporting Logic (copied from JSON normalize) ---
            print(f"XML normalization complete:")
            print(f"  - Processed {len(list_of_records)} root records")
            self.db_connection.commit()
            
            tables = self._get_table_list()
            print(f"  - Created {len(tables)} tables:")
            for table in tables:
                self.db_cursor.execute(f"SELECT COUNT(*) FROM {self._quote_identifier(table)}")
                count = self.db_cursor.fetchone()[0]
                print(f"    * {table}: {count} records")

        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {xml_filename}")
        except ET.ParseError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, f"XML parsing error: {e}"
            self._error(f"XML parsing error: {e}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during XML normalization: {e}")
            
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
        self._expect('DIM')
        while True:
            var_name = self._expect('ID')[1]
            token_after_var = self._current_token()

            # Case 1: Array with specific size, e.g., DIM x(10)
            if token_after_var and token_after_var[0] == 'LPAREN':
                self._expect('LPAREN')
                if self._current_token() and self._current_token()[0] == 'RPAREN':
                    self._expect('RPAREN')
                    self.variables[var_name] = []
                else:
                    size = int(self._parse_expression())
                    self._expect('RPAREN')
                    default_value = "" if var_name.endswith('$') else 0.0
                    self.variables[var_name] = [default_value] * (size + 1)

            # Case 2: HASH or dynamic ARRAY, e.g., DIM x AS HASH
            elif token_after_var and token_after_var[0] == 'AS':
                self._next_token()
                type_token = self._current_token()
                if not type_token or type_token[0] not in ['HASH', 'ARRAY']:
                    self._error(f"Expected HASH or ARRAY after AS")
                self._next_token()
                if type_token[0] == 'HASH':
                    self.variables[var_name] = {}
                elif type_token[0] == 'ARRAY':
                    self.variables[var_name] = []
            
            # Case 3: Simple scalar variable, e.g., DIM x
            else:
                if var_name.endswith('$'):
                    self.variables[var_name] = ""
                else:
                    self.variables[var_name] = 0.0

            # Check if another variable declaration follows on the same line
            token_after_decl = self._current_token()
            if token_after_decl and token_after_decl[0] == 'COMMA':
                self._next_token()  # Consume the comma and continue the loop
            else:
                break  # No comma, so the DIM statement is finished
            
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
            # This is the corrected block for single and multi-level dot notation.

            # Step 1: Ensure the base variable is a hash. Auto-create if it doesn't exist.
            if var_name not in self.variables or not isinstance(self.variables.get(var_name), dict):
                self.variables[var_name] = {}
            
            current_hash_level = self.variables[var_name]
            final_key_name = None

            # Step 2: Loop through the chain of .key tokens until the assignment is found.
            while True:
                if not (self._current_token() and self._current_token()[0] == 'DOT'):
                    self._error("Invalid dot notation syntax.")
                self._next_token() # Consume the '.'
                
                key_token = self._current_token()
                if not key_token or key_token[0] in self.INVALID_KEY_TOKENS:
                    self._error(f"Invalid token '{key_token[1]}' used as a key name.")
                self._next_token() # Consume the key token
                current_key = self._normalize_hash_key(key_token[1])
                # Step 3: Check what token comes AFTER the key we just consumed.
                if self._current_token() and self._current_token()[0] == 'DOT':
                    # If another dot follows, this key must lead to another hash.
                    if current_key not in current_hash_level or not isinstance(current_hash_level.get(current_key), dict):
                        current_hash_level[current_key] = {}
                    # Traverse one level deeper for the next loop iteration.
                    current_hash_level = current_hash_level[current_key]
                elif self._current_token() and self._current_token()[0] == 'ASSIGN':
                    # If an equals sign follows, this is the final key.
                    final_key_name = current_key
                    break # Exit the loop to perform the assignment.
                else:
                    self._error("Invalid token after dot notation path.")

            # Step 4: Assign the value to the final key. The '=' token is the current token.
            self._expect('ASSIGN')
            value = self._parse_expression()
            
            if final_key_name is not None:
                current_hash_level[final_key_name] = value
            else:
                # This case should be unreachable with the checks inside the loop.
                self._error("Dot notation assignment failed: final key not identified.")
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
        
        # --- FIX STARTS HERE: Restructured parsing logic ---
        options = {'header': 'auto', 'delimiter': 'auto', 'constraints': '', 'limit': None}
        into_hash_name = None
        
        # Use a loop to parse optional clauses in any order
        while self._current_token() and self._current_token()[0] in ['INTO', 'OPTIONS']:
            if self._current_token()[0] == 'INTO':
                if into_hash_name is not None:
                    self._error("INTO clause specified more than once.")
                self._next_token()
                into_hash_name = self._expect('ID')[1]
                if into_hash_name not in self.variables or not isinstance(self.variables.get(into_hash_name), dict):
                    self._error(f"'{into_hash_name}' is not a dimensioned hash for use with ANALYZE INTO.")
            
            elif self._current_token()[0] == 'OPTIONS':
                self._next_token()
                options_str = self._parse_expression()
                temp_options = {}
                key_matches = list(re.finditer(r'\b(\w+)=', options_str))
                for i, match in enumerate(key_matches):
                    key = match.group(1).lower()
                    start_pos = match.end()
                    end_pos = key_matches[i+1].start() if i + 1 < len(key_matches) else len(options_str)
                    value = options_str[start_pos:end_pos].strip().strip(',').strip()
                    if value.startswith('"') and value.endswith('"'): value = value[1:-1]
                    temp_options[key] = value

                for key, value in temp_options.items():
                    if key == 'header':
                        if value is None or value.lower() in ['true', '1', 'y']: options['header'] = True
                        elif value.lower() in ['false', '0', 'n']: options['header'] = False
                    elif key == 'constraints': options['constraints'] = value
                    elif key == 'limit': options['limit'] = int(value)
                    else: options[key] = value
                    
        # --- 2. PARSE CONSTRAINTS ---
        parsed_constraints = {}
        if options['constraints']:
            rules = options['constraints'].split(';')
            for rule in rules:
                if ':' not in rule: continue
                col_spec, constraint_def = rule.split(':', 1)
                col_name = col_spec.strip('[]')
                
                match = re.match(r'(\w+)(?:\((.*)\))?', constraint_def.strip())
                if not match: continue
                
                constraint_type, value = match.groups()
                constraint_type = constraint_type.upper()
                
                constraint_obj = {'type': constraint_type, 'def': constraint_def}
                
                if constraint_type in ['MINLENGTH', 'MAXLENGTH']:
                    try:
                        constraint_obj['value'] = int(value)
                    except (ValueError, TypeError):
                        self._error(f"Invalid integer value for {constraint_type}: {value}")
                elif constraint_type == 'REGEX':
                    constraint_obj['value'] = value
                elif constraint_type == 'IN':
                    constraint_obj['value'] = {item.strip() for item in value.split(',')}
                elif constraint_type == 'ISDATE':
                    # Convert BASIC date format to Python's strptime format
                    py_format = value.replace('MM', '%m').replace('DD', '%d').replace('YYYY', '%Y')
                    constraint_obj['value'] = py_format
                if col_name not in parsed_constraints:
                    parsed_constraints[col_name] = []
                parsed_constraints[col_name].append(constraint_obj)

        report = {}
        constraint_failures = []
        try:
            with open(filename, 'r', newline='', encoding='utf-8', errors='replace') as infile:
                # --- FILE PRE-ANALYSIS ---
                sample = infile.read(8192); infile.seek(0)
                sniffer = csv.Sniffer()

                if options['delimiter'] == 'auto':
                    try: report['DELIMITER'] = sniffer.sniff(sample).delimiter
                    except csv.Error: report['DELIMITER'] = ','
                else: report['DELIMITER'] = options['delimiter']
                
                has_header = options['header']
                if has_header == 'auto':
                    try: has_header = sniffer.has_header(sample)
                    except csv.Error: has_header = False
                report['HEADER_ROW'] = -1.0 if has_header else 0.0
                
                reader = csv.reader(infile, delimiter=report['DELIMITER'])
                headers = []
                line_num = 0
                if has_header:
                    try: headers = next(reader); line_num += 1
                    except StopIteration: pass
                
                # --- 3. APPLY CONSTRAINTS (IF ANY) ---
                if parsed_constraints:
                    limit = options.get('limit')
                    for row in reader:
                        line_num += 1
                        if limit is not None and (line_num - (1 if has_header else 0)) > limit: break
                        if not headers: headers = [f"Field_{j+1}" for j in range(len(row))]

                        for i, field_val in enumerate(row):
                            if i >= len(headers): continue
                            col_name = headers[i]
                            if col_name in parsed_constraints:
                                for const in parsed_constraints[col_name]:
                                    is_valid = True
                                    rule_type = const['type']
                                    if rule_type == 'REQUIRED' and not field_val.strip():
                                        is_valid = False
                                    elif field_val.strip():
                                        if rule_type == 'ISDIGITS' and not field_val.isdigit(): is_valid = False
                                        elif rule_type == 'MINLENGTH' and len(field_val) < const['value']: is_valid = False
                                        elif rule_type == 'MAXLENGTH' and len(field_val) > const['value']: is_valid = False
                                        elif rule_type == 'REGEX' and not re.match(const['value'], field_val): is_valid = False
                                        elif rule_type == 'IN' and field_val not in const['value']: is_valid = False
                                        elif rule_type == 'ISDATE':
                                            try: datetime.strptime(field_val, const['value'])
                                            except ValueError: is_valid = False
                                    
                                    if not is_valid:
                                        constraint_failures.append({
                                            'LINE': line_num, 'COLUMN': col_name,
                                            'VALUE': field_val, 'FAILED_RULE': const['def']
                                        })
                
                # --- 4. REPORTING LOGIC ---
                if constraint_failures:
                    if into_hash_name:
                        self.variables[into_hash_name] = self._python_to_basic_data({'CONSTRAINT_FAILURES': constraint_failures})
                    else:
                        print(f"Constraint Violations found in '{filename}':")
                        for failure in constraint_failures:
                            print(f"  - Line {failure['LINE']}, Column '{failure['COLUMN']}': Value '{failure['VALUE']}' failed rule '{failure['FAILED_RULE']}'")
                    return # Stop after reporting failures

                # --- 5. STATISTICAL ANALYSIS (IF NO CONSTRAINT FAILURES) ---
                infile.seek(0) # Rewind file to read from the start
                reader = csv.reader(infile, delimiter=report['DELIMITER'])
                if has_header:
                    headers = next(reader)
                
                record_count = 0
                field_counts = {}
                col_stats = {}
                date_formats_to_try = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y%m%d", "%Y-%m-%dT%H:%M:%S"]
                logical_trues = {'true', 't', 'y', 'yes', '1'}
                logical_falses = {'false', 'f', 'n', 'no', '0'}

                limit = options.get('limit')
                for i, row in enumerate(reader):
                    if limit is not None and i >= limit: break
                    record_count += 1
                    num_fields = len(row)
                    field_counts[num_fields] = field_counts.get(num_fields, 0) + 1

                    if not headers and row: headers = [f"Field_{j+1}" for j in range(num_fields)]
                    
                    for j, field in enumerate(row):
                        if j >= len(headers): continue
                        h = headers[j]
                        if h not in col_stats:
                            col_stats[h] = {'MIN_LEN': None, 'MAX_LEN': 0, 'EMPTY_COUNT': 0, 'INTEGER_COUNT': 0, 'FLOAT_COUNT': 0, 'DATE_COUNT': 0, 'LOGICAL_COUNT': 0, 'STRING_COUNT': 0, 'MAX_DECIMALS': 0, 'MIN_VALUE': None, 'MAX_VALUE': None}

                        field_len = len(field)
                        if col_stats[h]['MIN_LEN'] is None or field_len < col_stats[h]['MIN_LEN']: col_stats[h]['MIN_LEN'] = field_len
                        if field_len > col_stats[h]['MAX_LEN']: col_stats[h]['MAX_LEN'] = field_len
                        
                        field = field.strip()
                        if not field:
                            col_stats[h]['EMPTY_COUNT'] += 1; continue
                        
                        cleaned_field = field.replace('$', '').replace(',', '')
                        if not cleaned_field:
                            col_stats[h]['EMPTY_COUNT'] += 1; continue

                        try:
                            int_val = int(cleaned_field)
                            col_stats[h]['INTEGER_COUNT'] += 1
                            current_min, current_max = col_stats[h]['MIN_VALUE'], col_stats[h]['MAX_VALUE']
                            if isinstance(current_min, (int, float, type(None))):
                                if current_min is None or int_val < current_min: col_stats[h]['MIN_VALUE'] = int_val
                            if isinstance(current_max, (int, float, type(None))):
                                if current_max is None or int_val > current_max: col_stats[h]['MAX_VALUE'] = int_val
                            continue
                        except (ValueError, TypeError): pass

                        try:
                            float_val = float(cleaned_field)
                            col_stats[h]['FLOAT_COUNT'] += 1
                            if '.' in cleaned_field:
                                decimals = len(cleaned_field.split('.')[1])
                                if decimals > col_stats[h]['MAX_DECIMALS']: col_stats[h]['MAX_DECIMALS'] = decimals
                            current_min, current_max = col_stats[h]['MIN_VALUE'], col_stats[h]['MAX_VALUE']
                            if isinstance(current_min, (int, float, type(None))):
                                if current_min is None or float_val < current_min: col_stats[h]['MIN_VALUE'] = float_val
                            if isinstance(current_max, (int, float, type(None))):
                                if current_max is None or float_val > current_max: col_stats[h]['MAX_VALUE'] = float_val
                            continue
                        except (ValueError, TypeError): pass

                        lower_field = field.lower()
                        if lower_field in logical_trues or lower_field in logical_falses:
                            col_stats[h]['LOGICAL_COUNT'] += 1; continue
                        
                        is_a_date = False
                        for fmt in date_formats_to_try:
                            try:
                                date_val = datetime.strptime(field, fmt)
                                col_stats[h]['DATE_COUNT'] += 1
                                current_min, current_max = col_stats[h]['MIN_VALUE'], col_stats[h]['MAX_VALUE']
                                if isinstance(current_min, (datetime, type(None))):
                                    if current_min is None or date_val < current_min: col_stats[h]['MIN_VALUE'] = date_val
                                if isinstance(current_max, (datetime, type(None))):
                                    if current_max is None or date_val > current_max: col_stats[h]['MAX_VALUE'] = date_val
                                is_a_date = True; break
                            except (ValueError, TypeError): pass
                        if is_a_date: continue
                        
                        col_stats[h]['STRING_COUNT'] += 1
                        current_min, current_max = col_stats[h]['MIN_VALUE'], col_stats[h]['MAX_VALUE']
                        if isinstance(current_min, (str, type(None))):
                            if current_min is None or field < current_min: col_stats[h]['MIN_VALUE'] = field
                        if isinstance(current_max, (str, type(None))):
                            if current_max is None or field > current_max: col_stats[h]['MAX_VALUE'] = field

                for h, stats in col_stats.items():
                    if stats['STRING_COUNT'] > 0: stats['SUGGESTED_DATA_TYPE'] = 'TEXT'
                    elif stats['DATE_COUNT'] > 0 and stats['INTEGER_COUNT'] == 0 and stats['FLOAT_COUNT'] == 0: stats['SUGGESTED_DATA_TYPE'] = 'DATE'
                    elif stats['FLOAT_COUNT'] > 0: stats['SUGGESTED_DATA_TYPE'] = 'REAL'
                    elif stats['INTEGER_COUNT'] > 0 or stats['LOGICAL_COUNT'] > 0: stats['SUGGESTED_DATA_TYPE'] = 'INTEGER'
                    else: stats['SUGGESTED_DATA_TYPE'] = 'TEXT'
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
                    if parsed_constraints: print("  (No constraint violations found)")
                    print(f"  Delimiter Detected : '{report.get('DELIMITER', 'N/A')}'")
                    print(f"  Header Row Detected: {'Yes' if report.get('HEADER_ROW') else 'No'}")
                    print(f"  Total Data Records : {report.get('DATA_RECORDS', 0)}")
                    if report.get('FIELD_COUNT_DISTRIBUTION'):
                        print("  Field Count Distribution:")
                        for count, num_rows in report['FIELD_COUNT_DISTRIBUTION'].items():
                            print(f"    - {int(num_rows)} record(s) with {count} field(s)")

                    if report.get('COLUMN_STATISTICS'):
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
                            if stats.get('FLOAT_COUNT', 0) > 0: print(f"      Max Decimals     : {int(stats.get('MAX_DECIMALS', 0))}")
                            if stats.get('MIN_VALUE') is not None: print(f"      Value Range      : {stats.get('MIN_VALUE')} to {stats.get('MAX_VALUE')}")

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

    def _parse_gridedit_statement(self):
        self._expect('GRIDEDIT')

        table_name = ""
        token = self._current_token()

        if token[0] == 'STRING':
            table_name = token[1][1:-1]
            self._next_token()
        elif token[0] == 'ID':
            var_name = token[1]
            if self._find_variable_key(var_name) is not None:
                table_name_value = self._parse_expression()
                if not isinstance(table_name_value, str) or not table_name_value.strip():
                    self._error(f"GRIDEDIT table name variable '{var_name}' did not resolve to a non-empty string.")
                table_name = table_name_value.strip()
            else:
                table_name = var_name
                self._next_token()
        else:
            self._error("GRIDEDIT expects a table name (as a quoted string, variable, or unquoted literal).")
        
        if not table_name:
             self._error("Could not determine table name for GRIDEDIT.")

        user_columns = None
        base_where_clause = ""
        order_clause = ""
        search_config = {'enabled': False, 'fields': []}
        lookup_definitions = {}
        is_readonly = False
        
        while self._current_token() and self._current_token()[0] not in ['NEWLINE', 'END', 'COLON']:
            token = self._current_token()
            if token[0] == 'ID' and token[1].upper() == 'FIELDS':
                self._next_token()
                temp_columns = []
                if self._current_token() and self._current_token()[0] not in ['NEWLINE', 'END', 'COLON', 'SEARCH', 'WHERE', 'ORDER', 'READONLY', 'LOOKUP']:
                    while True:
                        field_name_expr = self._parse_expression()
                        temp_columns.append(str(field_name_expr))
                        if not (self._current_token() and self._current_token()[0] == 'COMMA'):
                            break
                        self._next_token()
                if not temp_columns: self._error("FIELDS clause requires at least one column name.")
                if len(temp_columns) == 1 and ',' in temp_columns[0]:
                    user_columns = [field.strip() for field in temp_columns[0].split(',')]
                else:
                    user_columns = temp_columns
            elif token[0] == 'WHERE' or (token[0] == 'ID' and token[1].upper() == 'WHERE'):
                self._next_token(); where_condition = self._parse_expression()
                base_where_clause = f" WHERE {where_condition}"
            elif token[0] == 'ID' and token[1].upper() == 'ORDER':
                self._next_token()
                if not (self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'BY'):
                    self._error("Expected BY after ORDER")
                self._next_token(); order_expression = self._parse_expression()
                order_clause = f" ORDER BY {order_expression}"
            elif token[0] == 'SEARCH':
                self._next_token(); search_config['enabled'] = True
                if self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'ON':
                    self._next_token()
                    temp_search_cols = []
                    if self._current_token() and self._current_token()[0] not in ['NEWLINE', 'END', 'COLON', 'FIELDS', 'WHERE', 'ORDER', 'READONLY', 'LOOKUP']:
                        while True:
                            col_name_expr = self._parse_expression()
                            temp_search_cols.append(str(col_name_expr))
                            if not (self._current_token() and self._current_token()[0] == 'COMMA'):
                                break
                            self._next_token()
                    if not temp_search_cols: self._error("SEARCH ON clause requires at least one column name.")
                    search_config['fields'] = temp_search_cols
            elif token[0] == 'LOOKUP':
                self._next_token()
                lookup_field = self._expect('ID')[1]
                query = self._extract_sql_from_parens()
                self._expect('RETURNS')
                returns_col = self._parse_table_name()
                display_col = returns_col
                if self._current_token() and self._current_token()[0] == 'DISPLAY':
                    self._next_token()
                    display_col = self._parse_table_name()
                lookup_definitions[lookup_field] = {"query": query, "returns": returns_col, "display": display_col} 
            elif token[0] == 'READONLY':
                self._next_token()
                is_readonly = True
            else:
                break

        metadata = self._get_table_metadata(table_name)
        pk_column = metadata['pk']
        all_column_names = metadata['columns']
        column_types = metadata['types']
        numeric_types = {'INTEGER', 'REAL', 'NUMERIC', 'INT', 'BIGINT', 'FLOAT', 'DOUBLE', 'DECIMAL'}
        
        if pk_column and pk_column.lower() not in [c.lower() for c in all_column_names]:
            all_column_names.insert(0, pk_column)

        display_columns = user_columns if user_columns else [col for col in all_column_names if col.lower() != 'rowid']

        select_cols_ordered = []
        seen_cols = set()
        def add_col_if_new(col_name):
            if col_name and col_name.lower() not in seen_cols:
                select_cols_ordered.append(col_name)
                seen_cols.add(col_name.lower())

        add_col_if_new(pk_column)
        for col in all_column_names:
            add_col_if_new(col)
        
        # Build elements for the EDIT form (PK is readonly)
        entry_form_elements = []
        for col in all_column_names:
            field_def = { 
                "type": "FIELD", "name": col, "label": f"{col.replace('_', ' ').title()}", 
                "readonly": is_readonly or (col.lower() == pk_column.lower()) 
            }
            if col in lookup_definitions: 
                field_def["lookup"] = lookup_definitions[col]
            entry_form_elements.append(field_def)
        
        # Build elements for the NEW form (PK is editable)
        new_form_elements = []
        for col in all_column_names:
            is_pk = (col.lower() == pk_column.lower())
            pk_is_autogen = False

            # Check for the conditions that indicate an auto-generated key
            if is_pk:
                pk_type = column_types.get(pk_column.upper(), '')
                # It's auto-generated if it's the implicit 'rowid' OR
                # if it's an INTEGER PRIMARY KEY in SQLite (which is an alias for rowid).
                if pk_column.lower() == 'rowid' or ('INTEGER' in pk_type and self.db_engine == 'sqlite'):
                    pk_is_autogen = True

            field_def = { 
                "type": "FIELD", "name": col, "label": f"{col.replace('_', ' ').title()}", 
                # The field is readonly ONLY if it is the PK AND it is auto-generated
                "readonly": is_pk and pk_is_autogen
            }
            if col in lookup_definitions: 
                field_def["lookup"] = lookup_definitions[col]
            new_form_elements.append(field_def)
        # --- END MODIFICATION ---
            
        entry_buttons = [{"name": "OK", "action": "CANCEL"}] if is_readonly else [{"name": "Save", "action": "UPDATE"}, {"name": "Cancel", "action": "CANCEL"}]
        
        entry_form_def = {
            "name": f"{table_name}_entry", 
            "title": f"Viewing: {table_name}" if is_readonly else f"Editing: {table_name}", 
            "elements": entry_form_elements, # Use edit-specific elements
            "buttons": entry_buttons
        }
        
        new_form_def = {
             "name": f"{table_name}_new", "title": f"New Record for {table_name}", 
             "elements": new_form_elements, # Use new-specific elements
             "buttons": [{"name": "Create", "action": "INSERT"}, {"name": "Cancel", "action": "CANCEL"}]
        }

        current_search_term = ""
        while True:
            quoted_base_table = self._quote_identifier(table_name)
            
            final_select_list = []
            for col in select_cols_ordered:
                if col in lookup_definitions:
                    config = lookup_definitions[col]
                    from_match = re.search(r'\bFROM\s+([a-zA-Z0-9_"]+)', config['query'], re.IGNORECASE)
                    if not from_match: self._error(f"Could not parse table name from LOOKUP query: {config['query']}")
                    lookup_table = from_match.group(1)
                    subquery = (f"(SELECT {self._quote_identifier(config['display'])} FROM {lookup_table} "
                                f"WHERE {self._quote_identifier(config['returns'])} = {quoted_base_table}.{self._quote_identifier(col)})")
                    final_select_list.append(f"{subquery} AS {self._quote_identifier(col)}")
                else:
                    final_select_list.append(f"{quoted_base_table}.{self._quote_identifier(col)}")

            final_where_clause, params = base_where_clause, []
            if search_config['enabled'] and current_search_term:
                search_on_cols = search_config['fields'] or display_columns
                search_conditions = []
                for col in search_on_cols:
                    if col in lookup_definitions:
                        config = lookup_definitions[col]
                        from_match = re.search(r'\bFROM\s+([a-zA-Z0-9_"]+)', config['query'], re.IGNORECASE)
                        if not from_match: continue
                        lookup_table = from_match.group(1)
                        subquery = (f"(SELECT {self._quote_identifier(config['display'])} FROM {lookup_table} "
                                    f"WHERE {self._quote_identifier(config['returns'])} = {quoted_base_table}.{self._quote_identifier(col)})")
                        search_conditions.append(f"LOWER(CAST({subquery} AS TEXT)) LIKE ?")
                    elif col in all_column_names:
                        search_conditions.append(f"LOWER(CAST({quoted_base_table}.{self._quote_identifier(col)} AS TEXT)) LIKE ?")

                if search_conditions:
                    search_sql_part = f"({' OR '.join(search_conditions)})"
                    final_where_clause = f"{base_where_clause} AND {search_sql_part}" if base_where_clause else f" WHERE {search_sql_part}"
                    params.extend([f"%{current_search_term.lower()}%"] * len(search_conditions))

            quoted_select_list_str = ', '.join(final_select_list)
            grid_query = f"SELECT {quoted_select_list_str} FROM {quoted_base_table}{final_where_clause}{order_clause}"
            
            rows = self._execute_sql(grid_query, is_query=True, params=params)
            headers = [desc[0] for desc in self.db_cursor.description] if self.db_cursor.description else []
            initial_grid_data = {"headers": headers, "rows": rows}
            
            grid_buttons = [{"name": "View", "action": "EDIT"}, {"name": "Close", "action": "CLOSE"}] if is_readonly else [{"name": "Edit", "action": "EDIT"}, {"name": "New", "action": "NEW"}, {"name": "Delete", "action": "DELETE"}, {"name": "Close", "action": "CLOSE"}]
            
            grid_form_def = {
                'name': f'{table_name}_grid', 'title': f'Viewing: {table_name}' if is_readonly else f'Editing: {table_name}',
                'buttons': grid_buttons, 'elements': [{"type": "FIELD", "name": col, 'label': col.title()} for col in display_columns]
            }
            
            list_runner = FormRunner(
                form_def=grid_form_def, initial_data=initial_grid_data, view_mode='grid', 
                pk_column_name=pk_column, search_config=search_config, current_search_term=current_search_term
            )
                 
            list_results = list_runner.run()
            
            action, current_search_term, selected_id = list_results.get("action", "").upper(), list_results.get("search_term", ""), list_results.get("selected_id")
            
            if action in ["UPDATE", "INSERT"] and not is_readonly:
                form_data = list_results.get("data", {})
                if not form_data:
                    continue

                if action == "UPDATE":
                    # This entire block should be replaced by the final, correct logic from the previous step
                    # For clarity, I'm pasting the correct, final "UPDATE" logic here.
                    pk_value = selected_id
                    
                    raw_select_list_for_update = [f"{quoted_base_table}.{self._quote_identifier(col)}" for col in select_cols_ordered]
                    quoted_raw_select_list_for_update = ', '.join(raw_select_list_for_update)
                    single_query_raw_for_update = f"SELECT {quoted_raw_select_list_for_update} FROM {quoted_base_table} WHERE {quoted_base_table}.{self._quote_identifier(pk_column)} = ?"
                    
                    original_row_data_list = self._execute_sql(single_query_raw_for_update, is_query=True, params=[selected_id])
                    original_db_data = dict(zip(select_cols_ordered, original_row_data_list[0])) if original_row_data_list else {}
                    
                    initial_display_data_snapshot = list_runner.get_initial_display_data()

                    data_to_save = {}
                    for key in all_column_names:
                        if key.lower() == pk_column.lower(): continue
                        
                        submitted_value = form_data.get(key)
                        
                        if key in lookup_definitions:
                            initial_display_value = initial_display_data_snapshot.get(key)
                            if str(submitted_value) != str(initial_display_value):
                                data_to_save[key] = submitted_value
                            else:
                                data_to_save[key] = original_db_data.get(key)
                        else:
                            data_to_save[key] = submitted_value

                    final_changed_data = {}
                    for key, new_value in data_to_save.items():
                        original_value = original_db_data.get(key)
                        if str(new_value) != str(original_value):
                            final_value = new_value
                            if new_value == "":
                                col_type = column_types.get(key.upper(), 'TEXT')
                                if any(num_type in col_type for num_type in numeric_types): final_value = None
                            final_changed_data[key] = final_value
                    
                    if final_changed_data:
                        set_clauses = [f"{self._quote_identifier(k)} = ?" for k in final_changed_data.keys()]
                        update_params = list(final_changed_data.values())
                        update_params.append(pk_value)
                        update_sql = f"UPDATE {self._quote_identifier(table_name)} SET {', '.join(set_clauses)} WHERE {self._quote_identifier(pk_column)} = ?"
                        self._execute_sql(update_sql, False, update_params)
                        if self.db_engine == 'sqlite': self.db_connection.commit()

                elif action == "INSERT":
                    # --- MODIFICATION: Allow PK to be included in INSERT ---
                    insert_columns = [col for col in all_column_names if col in form_data and form_data[col] != '']
                    if insert_columns:
                        column_placeholders = ', '.join(['?'] * len(insert_columns))
                        quoted_columns = ', '.join([self._quote_identifier(col) for col in insert_columns])
                        insert_values = []
                        for col in insert_columns:
                           new_value = form_data[col]
                           final_value = new_value
                           col_type = column_types.get(col.upper(), 'TEXT')
                           if new_value == "":
                                if any(num_type in col_type for num_type in numeric_types): final_value = None
                           insert_values.append(final_value)

                        insert_sql = f"INSERT INTO {self._quote_identifier(table_name)} ({quoted_columns}) VALUES ({column_placeholders})"
                        self._execute_sql(insert_sql, False, insert_values)
                        if self.db_engine == 'sqlite': self.db_connection.commit()
                continue

            if action == "SEARCH": continue
            if action == "CLOSE" or not action: break

            if action == "EDIT":
                if selected_id is None: continue
                self.variables['GRIDEDIT_ID'] = selected_id
                
                quoted_select_list_str = ', '.join(final_select_list)
                single_query = f"SELECT {quoted_select_list_str} FROM {quoted_base_table} WHERE {quoted_base_table}.{self._quote_identifier(pk_column)} = :GRIDEDIT_ID"
                
                row_data_list = self._execute_sql(single_query, is_query=True)
                if not row_data_list: continue
                
                current_headers = [desc[0] for desc in self.db_cursor.description]
                initial_entry_data = dict(zip(current_headers, row_data_list[0]))
                
                # Snapshot of the data as it was first displayed
                initial_display_data_snapshot = initial_entry_data.copy()
                
                while True:
                    entry_runner = FormRunner(entry_form_def, initial_data=initial_entry_data, view_mode='single', pk_column_name=pk_column)
                    entry_results = entry_runner.run()
                    
                    if entry_results.get("action") == "RUN_LOOKUP":
                        lookup_field_name = entry_results.get("lookup_field")
                        field_def = next((e for e in entry_form_elements if e.get("name") == lookup_field_name), None)
                        if not field_def or not field_def.get("lookup"): continue
                        lookup_config = field_def["lookup"]
                        try:
                            rows = self._execute_sql(lookup_config["query"], is_query=True)
                            headers = [desc[0] for desc in self.db_cursor.description] if self.db_cursor.description else []
                            form_data = entry_results.get("data", {})
                            initial_entry_data.update(form_data)
                            lookup_runner = FormRunner(form_def={"buttons": [{"name": "Select", "action": "SELECT"}, {"name": "Cancel", "action": "CANCEL"}]}, initial_data={"headers": headers, "rows": rows}, view_mode='grid', pk_column_name=headers[0] if headers else 'id')
                            lookup_results = lookup_runner.run()
                            if lookup_results.get("action") == "SELECT":
                                selected_row_pk = lookup_results.get("selected_id")
                                selected_row = next((r for r in rows if r[0] == selected_row_pk), None)
                                if selected_row:
                                    header_map = {h: i for i, h in enumerate(headers)}
                                    return_col, display_col = lookup_config["returns"], lookup_config["display"]
                                    if return_col in header_map: initial_entry_data[lookup_field_name] = selected_row[header_map[return_col]]
                                    if display_col in header_map and display_col != return_col: initial_entry_data[display_col] = selected_row[header_map[display_col]]
                        except Exception as e:
                            print(f"DEBUG: Query failed: {e}", file=sys.stderr)
                        continue
                    
                    if entry_results.get("action") == "UPDATE" and not is_readonly:
                        updated_data_from_form = entry_results.get("data", {})

                        raw_select_list_for_update = [f"{quoted_base_table}.{self._quote_identifier(col)}" for col in select_cols_ordered]
                        quoted_raw_select_list_for_update = ', '.join(raw_select_list_for_update)
                        single_query_raw_for_update = f"SELECT {quoted_raw_select_list_for_update} FROM {quoted_base_table} WHERE {quoted_base_table}.{self._quote_identifier(pk_column)} = ?"
                        
                        original_row_data_list = self._execute_sql(single_query_raw_for_update, is_query=True, params=[selected_id])
                        original_db_data = dict(zip(select_cols_ordered, original_row_data_list[0])) if original_row_data_list else {}

                        data_to_save = {}
                        for key in all_column_names:
                            if key.lower() == pk_column.lower(): continue
                            
                            submitted_value = updated_data_from_form.get(key)
                            
                            if key in lookup_definitions:
                                initial_display_value = initial_display_data_snapshot.get(key)
                                if str(submitted_value) != str(initial_display_value):
                                    data_to_save[key] = submitted_value
                                else:
                                    data_to_save[key] = original_db_data.get(key)
                            else:
                                data_to_save[key] = submitted_value

                        final_changed_data = {}
                        for key, new_value in data_to_save.items():
                            original_value = original_db_data.get(key)
                            if str(new_value) != str(original_value):
                                final_value = new_value
                                if new_value == "":
                                    col_type = column_types.get(key.upper(), 'TEXT')
                                    if any(num_type in col_type for num_type in numeric_types): final_value = None
                                final_changed_data[key] = final_value
                        
                        if final_changed_data:
                            set_clauses = [f"{self._quote_identifier(k)} = ?" for k in final_changed_data.keys()]
                            update_params = list(final_changed_data.values())
                            pk_value = selected_id
                            update_params.append(pk_value)
                            update_sql = f"UPDATE {self._quote_identifier(table_name)} SET {', '.join(set_clauses)} WHERE {self._quote_identifier(pk_column)} = ?"
                            self._execute_sql(update_sql, False, update_params)
                            if self.db_engine == 'sqlite': self.db_connection.commit()
                    break

            elif action == "NEW" and not is_readonly:
                initial_entry_data = {col: "" for col in all_column_names}

                while True:
                    entry_runner = FormRunner(new_form_def, initial_data=initial_entry_data, 
                                              view_mode='single', pk_column_name=pk_column)
                    entry_results = entry_runner.run()
                    if entry_results.get("action") == "RUN_LOOKUP":
                        lookup_field_name = entry_results.get("lookup_field")
                        field_def = next((e for e in new_form_elements if e.get("name") == lookup_field_name), None)
                        if field_def and field_def.get("lookup"):
                            lookup_config = field_def["lookup"]
                            try:
                                rows = self._execute_sql(lookup_config["query"], is_query=True)
                                headers = [desc[0] for desc in self.db_cursor.description] if self.db_cursor.description else []
                                form_data = entry_results.get("data", {})
                                initial_entry_data.update(form_data)
                                lookup_runner = FormRunner(form_def={"buttons": [{"name": "Select", "action": "SELECT"}, {"name": "Cancel", "action": "CANCEL"}]}, initial_data={"headers": headers, "rows": rows}, view_mode='grid', pk_column_name=headers[0] if headers else 'id')
                                lookup_results = lookup_runner.run()
                                if lookup_results.get("action") == "SELECT":
                                    selected_row_pk = lookup_results.get("selected_id")
                                    selected_row = next((r for r in rows if r[0] == selected_row_pk), None)
                                    if selected_row:
                                        header_map = {h: i for i, h in enumerate(headers)}
                                        return_col, display_col = lookup_config["returns"], lookup_config["display"]
                                        if return_col in header_map: initial_entry_data[lookup_field_name] = selected_row[header_map[return_col]]
                                        if display_col in header_map and display_col != return_col: initial_entry_data[display_col] = selected_row[header_map[display_col]]
                            except Exception as e:
                                print(f"DEBUG: Query failed: {e}")
                        continue

                    if entry_results.get("action") == "INSERT":
                        new_data = entry_results.get("data", {})
                        insert_columns = [col for col in all_column_names if col in new_data and new_data[col] != '']
                        if insert_columns:
                            column_placeholders = ', '.join(['?'] * len(insert_columns))
                            quoted_columns = ', '.join([self._quote_identifier(col) for col in insert_columns])
                            insert_values = []
                            for col in insert_columns:
                               new_value = new_data[col]
                               final_value = new_value
                               col_type = column_types.get(col.upper(), 'TEXT')
                               if new_value == "":
                                    if any(num_type in col_type for num_type in numeric_types): final_value = None
                               insert_values.append(final_value)

                            insert_sql = f"INSERT INTO {self._quote_identifier(table_name)} ({quoted_columns}) VALUES ({column_placeholders})"
                            self._execute_sql(insert_sql, False, insert_values)
                            if self.db_engine == 'sqlite': self.db_connection.commit()
                    break

            elif action == "DELETE" and not is_readonly:
                if selected_id is None: continue
                delete_sql = f"DELETE FROM {self._quote_identifier(table_name)} WHERE {self._quote_identifier(pk_column)} = ?"
                self._execute_sql(delete_sql, False, [selected_id])
                if self.db_engine == 'sqlite': self.db_connection.commit()
                
                
    def _parse_form_statement(self):
        self._expect('FORM')
        form_name = self._expect('ID')[1]

        form_def = {
            "name": form_name,
            "title": form_name, # Default title to form name
            "source": None,
            "display_rows": 1,
            "elements": [],
            "buttons": []
        }

        # Parse form-level attributes like DISPLAY and SOURCE first
        parsing_attributes = True
        while self._current_token():
            tok = self._current_token()
            if tok[0] == 'TITLE':
                self._next_token()
                form_def["title"] = self._parse_expression()
            elif tok[0] == 'DISPLAY':
                self._next_token()
                form_def["display_rows"] = int(self._parse_expression())
            elif tok[0] == 'SOURCE':
                self._next_token()
                form_def["source"] = {"type": "SQL", "query": self._extract_sql_from_parens()}
            elif tok[0] == 'NEWLINE':
                self._next_token() # Consume blank lines
            else:
                parsing_attributes = False
                # If it's not a form-level attribute, break to process elements
                break 

        # Now, loop through the rest of the form elements until ENDFORM
        while self._current_token() and self._current_token()[0] != 'ENDFORM':
            tok = self._current_token()

            INVALID_KEY_TOKENS = {
                'ASSIGN', 'LPAREN', 'RPAREN', 'COMMA', 'STRING', 'NUMBER',
                'OP', 'RELOP', 'DOT', 'SEMICOLON', 'COLON', 'NEWLINE', 'HASH_SYM'
            }

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
                field_name_token = self._current_token()
                
                INVALID_NAME_TOKENS = {
                    'ASSIGN', 'LPAREN', 'RPAREN', 'COMMA', 'STRING', 'NUMBER',
                    'OP', 'RELOP', 'DOT', 'SEMICOLON', 'COLON', 'NEWLINE', 'HASH_SYM'
                }

                if not field_name_token or field_name_token[0] in INVALID_NAME_TOKENS:
                    self._error(f"Invalid token '{field_name_token[1]}' used as a FIELD name.")

                field_name = field_name_token[1]
                self._next_token() # Consume the field name token

                
                self._expect('TYPE')
                type_token = self._current_token()
                if not type_token or type_token[0] in INVALID_KEY_TOKENS:
                    self._error(f"Expected a valid field type name but got '{type_token[1]}'")
                field_type = type_token[1].upper()
                self._next_token() # Consume the type token

                field_def = {
                    "type": "FIELD", "name": field_name, "field_type": field_type,
                    "label": field_name, "placeholder": "", "readonly": False,
                    "validations": {}
                }
                
                # This is the full, restored logic for parsing all field attributes
                while self._current_token() and self._current_token()[0] not in ['NEWLINE', 'ENDFORM', 'FIELD', 'BUTTON', 'HEADING', 'SEPARATOR']:
                    attr_tok = self._current_token()
                    
                    if attr_tok[0] == 'LOOKUP':
                        self._next_token() # Consume LOOKUP
                        lookup_query = self._extract_sql_from_parens()
                        self._expect('RETURNS')
                        returns_col = self._parse_expression()
                        display_col = returns_col # Default display to returns
                        if self._current_token() and self._current_token()[0] == 'DISPLAY':
                            self._next_token()
                            display_col = self._parse_expression()

                        field_def["lookup"] = {
                            "query": lookup_query,
                            "returns": returns_col,
                            "display": display_col
                        }
                    elif attr_tok[0] == 'READONLY':
                        self._next_token()
                        field_def["readonly"] = True
                    elif attr_tok[0] == 'LABEL':
                        self._next_token()
                        field_def["label"] = self._expect('STRING')[1].strip('"')
                    elif attr_tok[0] == 'SOURCE':
                        self._next_token() # Consume SOURCE
                        source_var_name = self._expect('ID')[1]
                        field_def["source_array"] = source_var_name
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
                self._next_token() # Consume BUTTON
                button_tok = self._current_token()
                if button_tok[0] == 'STRING':
                    button_name = button_tok[1].strip('"')
                else:
                    button_name = button_tok[1]
                self._next_token() # Consume the name token

                self._expect('ACTION') # Consume the ACTION keyword.

                action_tok = self._current_token()
                action = ""
                if action_tok[0] == 'STRING':
                    action = action_tok[1].strip('"')
                else:
                    action = action_tok[1]
                self._next_token() # Consume the action value token
                
                form_def["buttons"].append({"name": button_name, "action": action.upper()})

            elif tok[0] == 'NEWLINE':
                self._next_token()

            else:
                self._error(f"Unexpected token '{tok[1]}' inside FORM definition.")

        self._expect('ENDFORM')
        
        if form_name in self.form_definitions:
            self._error(f"Duplicate FORM definition: '{form_name}'")
        
        # This debug print is very helpful, you may want to keep it
        #print("DEBUG", form_def)
        self.form_definitions[form_name] = form_def
    
    def _parse_open_form_statement(self):
        self._expect('OPENFORM')
        form_name = self._expect('ID')[1]

        record_id = None
        if self._current_token() and self._current_token()[0] == 'USING':
            self._next_token() # Consume USING
            record_id = self._parse_expression()
        
        if form_name not in self.form_definitions:
            self._error(f"FORM '{form_name}' is not defined.")
        
        form_def = self.form_definitions[form_name]

        # Inject choices for CHOICE fields from variables
        for element in form_def.get("elements", []):
            if element.get("type") == "FIELD" and element.get("field_type") == "CHOICE":
                source_array_name = element.get("source_array")
                if source_array_name and isinstance(self.variables.get(source_array_name), list):
                    element["choices"] = self.variables[source_array_name]

        # Safely get the source object to check if it exists
        source_info = form_def.get("source")

        # Case 1: Handle data-bound forms that have a SOURCE clause
        if source_info and source_info.get("query"):
            source_query = source_info.get("query")
            table_name = self._extract_table_from_select(source_query)
            pk_column_name = self._get_primary_key(table_name) if table_name else 'id'
            
            current_view_mode = 'grid' if form_def.get("display_rows", 1) > 1 else 'single'

            nav_query = f"SELECT {self._quote_identifier(pk_column_name)} FROM ({source_query}) AS t"
            all_ids_result = self._execute_sql(nav_query, is_query=True)
            record_ids = [row[0] for row in all_ids_result]
            
            current_index = -1
            if record_id is not None and record_id in record_ids:
                current_index = record_ids.index(record_id)
                current_view_mode = 'single'
            elif record_ids and current_view_mode == 'single':
                current_index = 0

            current_data = {}

            # Main Controller Loop for data-bound forms
            while True:
                nav_info = {"has_prev": current_index > 0, "has_next": current_index < len(record_ids) - 1}

                if current_view_mode == 'single':
                    if current_index != -1 and not current_data:
                        current_id = record_ids[current_index]
                        self.variables['FORM_PK_ID'] = current_id
                        single_query = f"SELECT * FROM ({source_query}) AS t WHERE {self._quote_identifier(pk_column_name)} = :FORM_PK_ID"
                        row_data = self._execute_sql(single_query, is_query=True)
                        if row_data and self.db_cursor.description:
                            headers = [desc[0] for desc in self.db_cursor.description]
                            current_data = dict(zip(headers, row_data[0]))
                else:
                    rows = self._execute_sql(source_query, is_query=True)
                    headers = [desc[0] for desc in self.db_cursor.description] if self.db_cursor.description else []
                    current_data = {"headers": headers, "rows": rows}

                runner = FormRunner(form_def, current_data, nav_info, view_mode=current_view_mode, pk_column_name=pk_column_name)
                results = runner.run()
                action = results.get("action")
                
                if current_view_mode == 'single':
                    current_data.update(results.get("data", {}))

                if action == "RUN_LOOKUP":
                    lookup_field_name = results.get("lookup_field")
                    field_def = next((e for e in form_def.get("elements", []) if e.get("name") == lookup_field_name), None)
                    if not field_def or not field_def.get("lookup"): continue

                    lookup_config = field_def["lookup"]
                    rows = self._execute_sql(lookup_config["query"], is_query=True)
                    headers = [desc[0] for desc in self.db_cursor.description] if self.db_cursor.description else []
                    
                    lookup_runner = FormRunner(
                        form_def={"buttons": [{"name": "Select", "action": "SELECT"}, {"name": "Cancel", "action": "CANCEL"}]},
                        initial_data={"headers": headers, "rows": rows},
                        view_mode='grid', pk_column_name=headers[0] if headers else 'id'
                    )
                    lookup_results = lookup_runner.run()

                    if lookup_results.get("action") == "SELECT":
                        selected_row_pk = lookup_results.get("selected_id")
                        selected_row = next((r for r in rows if r[0] == selected_row_pk), None)
                        if selected_row:
                            header_map = {h: i for i, h in enumerate(headers)}
                            return_col, display_col = lookup_config["returns"], lookup_config["display"]
                            if return_col in header_map:
                                current_data[lookup_field_name] = selected_row[header_map[return_col]]
                            if display_col in header_map:
                                current_data[display_col] = selected_row[header_map[display_col]]
                    continue

                elif action == "VIEW_GRID": current_data = {}; current_view_mode = 'grid'; continue
                elif action == "VIEW_SINGLE":
                    selected_id = results.get("selected_id")
                    if selected_id in record_ids: current_index = record_ids.index(selected_id)
                    current_data = {}; current_view_mode = 'single'; continue
                elif action == "NEXT_RECORD":
                    if current_index < len(record_ids) - 1: current_index += 1
                    current_data = {}; continue
                elif action == "PREV_RECORD":
                    if current_index > 0: current_index -= 1
                    current_data = {}; continue
                elif action == "FIRST_RECORD":
                    if record_ids: current_index = 0
                    current_data = {}; continue
                elif action == "LAST_RECORD":
                    if record_ids: current_index = len(record_ids) - 1
                    current_data = {}; continue
                
                self.variables["FORM_RESULT$"] = str(action).upper() if action is not None else ""
                self.variables["FORM_SELECTED_ID"] = float(results.get("pk") or results.get("selected_id") or record_id or 0.0)
                self.variables["FORM_DATA"] = self._python_to_basic_data(current_data)
                break

        # Case 2: Handle transient forms that have NO SOURCE clause
        else:
            # This is a simple data entry form, like the signup example.
            if form_def.get("display_rows", 1) > 1:
                self._error(f"FORM '{form_name}' with 'display_rows > 1' requires a SOURCE clause.")
            if record_id is not None:
                 self._error(f"USING clause is only valid for forms with a SOURCE clause.")

            runner = FormRunner(
                    form_def,
                    initial_data={},
                    nav_info={},
                    view_mode='single',
                    pk_column_name='id'
                )
            results = runner.run()

            # After the form closes, set the system variables with the results
            action = results.get("action")
            data = results.get("data", {})
            self.variables["FORM_RESULT$"] = str(action).upper() if action is not None else ""
            self.variables["FORM_SELECTED_ID"] = 0.0 # No ID for new, transient records
            self.variables["FORM_DATA"] = self._python_to_basic_data(data)

            # Also, populate top-level variables from the form data
            if isinstance(data, dict):
                for key, value in data.items():
                    # Create variable names with a '$' suffix if the value is a string
                    var_name = f"{key}$" if isinstance(value, str) else key
                    self._set_variable_value(var_name, value)
            
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

    def _parse_analyze_text_statement(self):
        """Performs a detailed statistical analysis of a text file, including encoding and newlines."""
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        # I changed the name of this function
        self._expect('ANALYZE TEXT')
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
            
            # --- NEW: Encoding and Newline Detection ---
            encoding = 'unknown'
            newline_type = 'N/A'
            with open(filename, 'rb') as f_binary:
                # Encoding detection: Check for BOM, then try UTF-8 decode.
                bom = f_binary.read(3)
                if bom == b'\xef\xbb\xbf':
                    encoding = 'UTF-8 (with BOM)'
                else:
                    f_binary.seek(0)
                    try:
                        f_binary.read().decode('utf-8')
                        encoding = 'UTF-8 (no BOM)'
                    except UnicodeDecodeError:
                        encoding = 'ANSI / Western (e.g., Latin-1, CP-1252)'
                
                # Newline detection
                f_binary.seek(0)
                content_sample = f_binary.read(8192) # Read a sample
                if b'\r\n' in content_sample:
                    newline_type = 'CRLF (Windows)'
                elif b'\n' in content_sample:
                    newline_type = 'LF (Unix/macOS)'
            
            report['ENCODING'] = encoding
            report['NEWLINE_TYPE'] = newline_type
            
            # --- More efficient content analysis ---
            with open(filename, 'r', encoding='utf-8', errors='replace') as f:
                full_content = f.read()
            
            lines = full_content.splitlines()
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
                print(f"--- Text File Analysis Report for: {filename} ---")
                print(f"  File Size       : {self._format_bytes(file_size)}")
                print(f"  Encoding        : {report['ENCODING']}")
                print(f"  Newline Style   : {report['NEWLINE_TYPE']}")
                print(f"  Total Lines     : {report['TOTAL_LINES']}")
                print(f"  Empty Lines     : {report['EMPTY_LINES']}")
                print(f"  Total Chars     : {report['TOTAL_CHARACTERS']}")
                print(f"  Total Words     : {report['TOTAL_WORDS']}")

        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {filename}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during file analysis: {e}")

    def _describe_json_node(self, node, indent=""):
        """A recursive helper to print the structure of a JSON node."""
        if isinstance(node, dict):
            print(f"{indent}(Object)")
            for key, value in node.items():
                print(f"{indent}  - \"{key}\": ", end="")
                self._describe_json_node(value, indent + "    ")
        elif isinstance(node, list):
            print(f"{indent}(Array)")
            if not node:
                print(f"{indent}  (empty)")
                return

            # NEW: Check if the array contains objects we can merge for a complete view
            if any(isinstance(item, dict) for item in node):
                merged_object = {}
                for item in node:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            # Add key to the merged object if we haven't seen it yet
                            if key not in merged_object:
                                merged_object[key] = value
                
                # Describe the synthetic merged object, marked with [*]
                print(f"{indent}  - [*]: ", end="")
                self._describe_json_node(merged_object, indent + "       ")
            else:
                # It's a simple array (e.g., of strings), so just describe the first element
                print(f"{indent}  - [0]: ", end="")
                self._describe_json_node(node[0], indent + "       ")

        elif isinstance(node, str):
            print("(String)")
        elif isinstance(node, bool):
            print("(Boolean)")
        elif isinstance(node, int) or isinstance(node, float):
            print("(Number)")
        elif node is None:
            print("(Null)")
        else:
            print("(Unknown Type)")
            
    def _parse_analyze_json_statement(self):
        """Parses and executes ANALYZE JSON, reporting on structural consistency and format."""
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
            records_to_analyze = data if isinstance(data, list) else [data]

            report['TOTAL_RECORDS'] = len(records_to_analyze)
            
            # Analyze the consistency of keys across all objects
            key_sets = [tuple(sorted(d.keys())) for d in records_to_analyze if isinstance(d, dict)]
            key_distribution = {}
            for ks in key_sets:
                key_distribution[ks] = key_distribution.get(ks, 0) + 1
            
            report['IS_CONSISTENT'] = -1.0 if len(key_distribution) <= 1 else 0.0
            report['KEY_SET_DISTRIBUTION'] = self._python_to_basic_data(key_distribution)
            
            if into_hash_name:
                self.variables[into_hash_name] = self._python_to_basic_data(report)
            else:
                print(f"--- JSON Analysis Report for: {filename} ---")
                print(f"  --- Consistency Check ---")
                print(f"  Total Records (Objects) : {report['TOTAL_RECORDS']}")
                print(f"  Is Consistent           : {'Yes' if report['IS_CONSISTENT'] else 'No'}")
                if report['KEY_SET_DISTRIBUTION']:
                    print("  Key Set Distribution:")
                    for key_set, count in report['KEY_SET_DISTRIBUTION'].items():
                        print(f"    - {int(count)} record(s) with keys: {key_set}")
                
                # --- NEW: Automatically print the structure map ---
                print(f"\n  --- Simplified Structure ---")
                self._describe_json_node(data)


        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {filename}")
        except json.JSONDecodeError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"JSON parsing error: {e}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during JSON analysis: {e}")

    def _parse_analyze_jsonl_statement(self):
        """Analyzes a JSON Lines file for validity and structural consistency."""
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('ANALYZE JSONL')
        filename = self._parse_expression()

        into_hash_name = None
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token()
            into_hash_name = self._expect('ID')[1]
            if into_hash_name not in self.variables or not isinstance(self.variables.get(into_hash_name), dict):
                 self._error(f"'{into_hash_name}' is not a dimensioned hash for use with ANALYZE INTO.")

        report = {}
        key_distribution = {}
        total_lines, valid_records, invalid_records = 0, 0, 0
        all_records = []
        
        try:
            with open(filename, 'r', encoding='utf-8', errors='replace') as infile:
                for line in infile:
                    total_lines += 1
                    line = line.strip()
                    if not line:
                        continue # Skip empty lines but count them

                    try:
                        record = json.loads(line)
                        all_records.append(record) # Store valid records for structure analysis
                        valid_records += 1
                        if isinstance(record, dict):
                            key_set = tuple(sorted(record.keys()))
                            key_distribution[key_set] = key_distribution.get(key_set, 0) + 1
                    except json.JSONDecodeError:
                        invalid_records += 1

            # Build the final report
            report['TOTAL_RECORDS'] = total_lines
            report['VALID_JSON_RECORDS'] = valid_records
            report['INVALID_JSON_RECORDS'] = invalid_records
            report['IS_CONSISTENT'] = -1.0 if len(key_distribution) <= 1 and valid_records > 0 else 0.0
            
            # Store key distribution for both INTO and print modes
            report['KEY_SET_DISTRIBUTION'] = self._python_to_basic_data(key_distribution)

            if into_hash_name:
                self.variables[into_hash_name] = self._python_to_basic_data(report)
            else:
                print(f"--- JSONL Analysis Report for: {filename} ---")
                print(f"  --- Consistency Check ---")
                print(f"  Total Lines Read        : {report['TOTAL_RECORDS']}")
                print(f"  Valid JSON Objects      : {report['VALID_JSON_RECORDS']}")
                print(f"  Invalid JSON Lines      : {report['INVALID_JSON_RECORDS']}")
                print(f"  Consistent Structure    : {'Yes' if report['IS_CONSISTENT'] else 'No'}")
                
                # Use the unconverted key_distribution for printing
                if key_distribution:
                    print("  Key Set Distribution:")
                    for key_set, count in key_distribution.items():
                        key_str = ", ".join(f"'{k}'" for k in key_set)
                        print(f"    - {int(count)} record(s) with keys: ({key_str})")
                
                # --- NEW: Automatically print the structure map ---
                if all_records:
                    print(f"\n  --- Simplified Structure ---")
                    # The file represents an array, so we pass the list of records
                    self._describe_json_node(all_records)

        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {filename}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during JSONL analysis: {e}")

    def _describe_xml_node(self, element, indent=""):
        """A recursive helper to print a reduced structure of an XML node."""
        print(f"{indent}<{element.tag}>")

        # Display attributes of the current element
        if element.attrib:
            for key in element.attrib:
                print(f"{indent}  - @{key} (Attribute)")
        
        # Find unique child tags to describe the structure without repetition
        processed_child_tags = set()
        for child in element:
            if child.tag not in processed_child_tags:
                # Recurse on the first instance of each unique child tag
                self._describe_xml_node(child, indent + "  ")
                processed_child_tags.add(child.tag)
                
    def _parse_analyze_xml_statement(self):
        """Analyzes an XML file to determine its structure."""
        from collections import Counter # Local import for this specific function
        self.variables.update({'ERR': 0.0, 'ERRMSG$': ""})
        self._expect('ANALYZE XML')
        filename = self._parse_expression()

        into_hash_name = None
        if self._current_token() and self._current_token()[0] == 'INTO':
            self._next_token()
            into_hash_name = self._expect('ID')[1]
            if into_hash_name not in self.variables or not isinstance(self.variables.get(into_hash_name), dict):
                 self._error(f"'{into_hash_name}' is not a dimensioned hash for use with ANALYZE INTO.")
        
        try:
            report = {}
            tree = ET.parse(filename)
            root = tree.getroot()

            report['ROOT_ELEMENT'] = root.tag
            report['TOTAL_CHILD_ELEMENTS'] = len(root)

            predominant_tag, record_count, inferred_fields = "N/A", 0, []

            if len(root) > 0:
                child_tags = [child.tag for child in root]
                tag_counts = Counter(child_tags)
                all_tags_are_unique = all(count == 1 for count in tag_counts.values())

                if all_tags_are_unique and len(child_tags) > 1:
                    predominant_tag = root.tag
                    record_count = 1
                    inferred_fields = sorted(child_tags)
                else:
                    predominant_tag, record_count = tag_counts.most_common(1)[0]
                    fields_set = set()
                    sample_limit = 100 
                    records_sampled = 0
                    for child in root:
                        if child.tag == predominant_tag:
                            if records_sampled >= sample_limit: break
                            for field in child: fields_set.add(field.tag)
                            records_sampled += 1
                    inferred_fields = sorted(list(fields_set))

            report['PREDOMINANT_RECORD_TAG'] = predominant_tag
            report['RECORD_COUNT'] = record_count
            report['INFERRED_FIELDS'] = inferred_fields

            if into_hash_name:
                self.variables[into_hash_name] = self._python_to_basic_data(report)
            else:
                print(f"--- XML Analysis Report for: {filename} ---")
                print(f"  --- Heuristic Analysis ---")
                print(f"  Root Element            : <{report['ROOT_ELEMENT']}>")
                print(f"  Total Direct Children   : {report['TOTAL_CHILD_ELEMENTS']}")
                print(f"  Inferred Record Tag     : <{report['PREDOMINANT_RECORD_TAG']}>")
                print(f"  Record Count            : {report['RECORD_COUNT']}")
                if report['INFERRED_FIELDS']:
                    fields_str = ", ".join(f"<{f}>" for f in report['INFERRED_FIELDS'])
                    print(f"  Inferred Record Fields  : {fields_str}")
                else:
                    print(f"  Inferred Record Fields  : (No child fields found in record tag)")

                # --- NEW: Automatically print the structure map ---
                print(f"\n  --- Simplified Structure ---")
                self._describe_xml_node(root)


        except FileNotFoundError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 2.0, str(e)
            self._error(f"File not found: {filename}")
        except ET.ParseError as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, f"XML parsing error: {e}"
            self._error(f"XML parsing error: {e}")
        except Exception as e:
            self.variables['ERR'], self.variables['ERRMSG$'] = 1.0, str(e)
            self._error(f"An error occurred during XML analysis: {e}")

    '''
    SHOW TABLES;
    SHOW INDEXES [ON table_name];
    SHOW CREATE TABLE [table_name];
    '''
    def _parse_show_statement(self):
        self._expect('SHOW')
        if self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'TABLES':
            self._next_token()
            if self._current_token() and self._current_token()[0] == 'SEMICOLON':
                self._next_token()
            results = self._get_table_list()
            if results:
                for row in results:
                    print(row)
            else:
                print("No tables found.")
        
        elif self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'INDEXES':
            self._next_token() # Consume INDEXES
            
            on_table = None
            if self._current_token() and self._current_token()[0] == 'ID' and self._current_token()[1].upper() == 'ON':
                self._next_token() # Consume ON
                on_table = self._parse_table_name()

            if self._current_token() and self._current_token()[0] == 'SEMICOLON':
                self._next_token()

            all_results = []
            if self.db_engine == 'duckdb':
                # DuckDB logic would go here
                pass
            else: # SQLite
                if on_table:
                    # Query for a single, specific table (now includes PK as ALTER TABLE)
                    sql = """
                        SELECT sql, NULL FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL AND tbl_name = ?
                        UNION ALL
                        SELECT '-- UNIQUE constraint implemented by index: ' || il.name,
                               'CREATE UNIQUE INDEX ' || il.name || ' ON ' || ? || ' (' || group_concat(p.name, ', ') || ');'
                        FROM pragma_index_list(?) AS il JOIN pragma_index_info(il.name) AS p
                        WHERE il.origin = 'u' GROUP BY il.name
                        UNION ALL
                        SELECT 'ALTER TABLE ' || ? || ' ADD CONSTRAINT ' || il.name || ' PRIMARY KEY (' || group_concat(p.name, ', ') || ');', NULL
                        FROM pragma_index_list(?) AS il JOIN pragma_index_info(il.name) AS p
                        WHERE il.origin = 'pk' GROUP BY il.name
                    """
                    params = [on_table, on_table, on_table, on_table, on_table]
                    results = self._execute_sql(sql, is_query=True, params=params)
                    if results: all_results.extend(results)
                else:
                    # Query for ALL tables (now includes PK as ALTER TABLE)
                    sql_explicit = "SELECT sql, NULL FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL"
                    explicit_indexes = self._execute_sql(sql_explicit, is_query=True)
                    if explicit_indexes: all_results.extend(explicit_indexes)
                    
                    all_tables = self._get_table_list()
                    for table_name in all_tables:
                        sql_constraints = """
                            SELECT '-- UNIQUE constraint on table ' || ? || ' implemented by index: ' || il.name,
                                   'CREATE UNIQUE INDEX ' || il.name || ' ON ' || ? || ' (' || group_concat(p.name, ', ') || ');'
                            FROM pragma_index_list(?) AS il JOIN pragma_index_info(il.name) AS p
                            WHERE il.origin = 'u' GROUP BY il.name
                            UNION ALL
                            SELECT 'ALTER TABLE ' || ? || ' ADD CONSTRAINT ' || il.name || ' PRIMARY KEY (' || group_concat(p.name, ', ') || ');', NULL
                            FROM pragma_index_list(?) AS il JOIN pragma_index_info(il.name) AS p
                            WHERE il.origin = 'pk' GROUP BY il.name
                        """
                        constraint_indexes = self._execute_sql(sql_constraints, is_query=True, params=[table_name, table_name, table_name, table_name, table_name])
                        if constraint_indexes: all_results.extend(constraint_indexes)

            if all_results:
                for row in all_results:
                    for col in row:
                        if col:
                            print(col if col.endswith(';') else col + ";")
            else:
                print(f"No indexes found{' on table ' + on_table if on_table else ''}.")

        elif self._current_token() and self._current_token()[0] == 'CREATE':
            self._next_token() 
            if not (self._current_token() and self._current_token()[0] == 'TABLE'):
                self._error("Expected TABLE after SHOW CREATE")
            self._next_token()

            table_names_to_show = []
            if self._current_token() and self._current_token()[0] not in ['SEMICOLON', 'NEWLINE', 'END']:
                table_name = self._parse_table_name()
                table_names_to_show.append(table_name)
            else:
                table_names_to_show = self._get_table_list()
            
            if self._current_token() and self._current_token()[0] == 'SEMICOLON':
                self._next_token()

            for name in table_names_to_show:
                if self.db_engine == 'duckdb':
                    sql = f"SELECT sql FROM duckdb_tables() WHERE table_name = '{name}'"
                else: # SQLite
                    sql = f"SELECT sql FROM sqlite_master WHERE type='table' AND name = '{name}'"
                
                results = self._execute_sql(sql, is_query=True)
                if results and results[0] and results[0][0]:
                    print(results[0][0].rstrip(';') + ";\n")
                else:
                    print(f"-- Table '{name}' not found or has no CREATE statement.\n")
        else:
            self._error("Expected TABLES, INDEXES, or CREATE TABLE after SHOW")
            
    def _parse_describe_statement(self):
        self._expect('DESCRIBE')
        if self._current_token() and self._current_token()[0] == 'TABLE':
            self._next_token()
        
        table_name = self._parse_table_name()
        # Optional: consume semicolon if present
        if self._current_token() and self._current_token()[0] == 'SEMICOLON':
            self._next_token()
        
        try:
            # Execute the engine-specific command for describing table structure
            if self.db_engine == 'duckdb':
                sql = f"DESCRIBE {self._quote_identifier(table_name)};"
            else: # SQLite
                sql = f"PRAGMA table_info({self._quote_identifier(table_name)});"
            
            # Use the standard output handler to display the results as a table
            results = self._execute_sql(sql, is_query=True)
            if results:
                column_names = [desc[0] for desc in self.db_cursor.description]
                self._handle_output(results, column_names)
            else:
                print(f"Table '{table_name}' not found.", file=sys.stderr)
                
        except Exception as e:
            self.variables['ERR'] = 1.0
            self.variables['ERRMSG$'] = str(e)
            if self.sql_fatal_errors:
                self._error(f"Error describing table: {e}")
                
        except Exception as e:
            self.variables['ERR'] = 1.0
            self.variables['ERRMSG$'] = str(e)
            if self.sql_fatal_errors:
                self._error(f"Error describing table: {e}")
                
        
    def _parse_gosub_statement(self):
        self._expect('GOSUB'); label_name = self._expect('ID')[1]
        if label_name not in self.labels: self._error(f"Label '{label_name}' not found.")
        self.gosub_stack.append(self.token_index); self.token_index = self.labels[label_name]
        
    def _parse_return_statement(self):
        self._expect('RETURN')
        if not self.gosub_stack: self._error("RETURN without GOSUB.")
        self.token_index = self.gosub_stack.pop()

class JSONToSQLiteNormalizer:
    SQL_RESERVED_WORDS = {
            'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'TABLE', 'ATTACH', 'COPY',
            'VIEW', 'INDEX', 'ORDER', 'GROUP', 'BY', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'SUMMARIZE', 'PRAGMA',
            'OUTER', 'ON', 'AS', 'IN', 'IS', 'NULL', 'NOT', 'AND', 'OR', 'LIMIT', 'OFFSET'
        }
    def __init__(
        self,
        db_path: str,
        root_table: str = 'main',
        array_threshold: int = 2,
        keep_objects: bool = False,
        keep_arrays: bool = False,
    ):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.array_threshold = array_threshold
        self.keep_objects = keep_objects
        self.keep_arrays = keep_arrays
        self.root_table = root_table or 'main'

    def _quote_identifier(self, identifier: str, quote_style: str = '"') -> str:
            """
            Wraps a SQL identifier in quotes only if it's a reserved
            keyword or contains characters that require quoting.
            Supports different quoting styles ('"' or '[').
            """
            identifier_str = str(identifier)
            
            # Determine the quote characters based on the chosen style
            if quote_style == '[':
                open_quote, close_quote = '[', ']'
            else:
                open_quote, close_quote = '"', '"'

            # Rule 1: If it's a reserved keyword, it must be quoted.
            if identifier_str.upper() in self.SQL_RESERVED_WORDS:
                return f'{open_quote}{identifier_str}{close_quote}'
            
            # Rule 2: If it's a "simple" identifier, it doesn't need quotes.
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier_str):
                return identifier_str
                
            # Rule 3: If it's not simple, it must be quoted.
            # Before quoting, remove any characters that would conflict with the quotes.
            safe_identifier = identifier_str.replace(open_quote, '').replace(close_quote, '')
            return f'{open_quote}{safe_identifier}{close_quote}'
    
    # --- HELPER: This was missing ---
    def _infer_sql_type(self, value):
        if isinstance(value, int): return 'INTEGER'
        if isinstance(value, float): return 'REAL'
        if isinstance(value, bool): return 'INTEGER'
        return 'TEXT'

    def _ensure_table(self, table: str, schema: Dict[str, str], parent_table: Optional[str] = None):
        pk_name = f"pk_{table}"
        try:
            # Check if table already exists
            res = self.cursor.execute(f"PRAGMA table_info('{table}')")
            existing_cols = {row[1] for row in res.fetchall()}
        except (sqlite3.OperationalError, duckdb.Error):
            existing_cols = set()

        if not existing_cols:
            # --- THIS IS THE FIX: Robustly build the list of columns ---
            parts = [f"[{pk_name}] INTEGER PRIMARY KEY AUTOINCREMENT"]
            if parent_table:
                fk_name = f"{parent_table}_fk"
                parts.append(f"[{fk_name}] INTEGER")

            if schema:
                col_defs = [f"[{col}] {dtype}" for col, dtype in schema.items()]
                parts.extend(col_defs)

            ddl = f"CREATE TABLE {self._quote_identifier(table)} ({', '.join(parts)})"
            self.cursor.execute(ddl)
            # --- END FIX ---
        else:
            # Alter table logic remains the same
            for col, dtype in schema.items():
                if col not in existing_cols:
                    self.cursor.execute(f"ALTER TABLE {self._quote_identifier(table)} ADD COLUMN {self._quote_identifier(col)} {dtype}")

    def _insert_row(self, table: str, parent_id: Optional[int], row: Dict[str, Any], parent_table: Optional[str] = None):
        if not row and parent_id is None:
            return None

        cols, vals = (), ()
        if row:
            cols, vals = zip(*row.items())
        
        if parent_id is not None and parent_table:
            fk_name = f"{parent_table}_fk"
            cols = (fk_name,) + cols
            vals = (parent_id,) + vals

        if not cols:
             return None

        placeholders = ", ".join(["?"] * len(vals))
        colnames = ", ".join([f"[{col}]" for col in cols])
        sql = f"INSERT INTO {self._quote_identifier(table)} ({colnames}) VALUES ({placeholders})"
        self.cursor.execute(sql, vals)
        return self.cursor.lastrowid

    def _normalize(self, data: Any, parent_id: Optional[int], table: str, parent_table: Optional[str] = None):
        if isinstance(data, dict):
            row, schema = {}, {}
            if self.keep_objects:
                row[f"{table}_json"] = json.dumps(data)
                schema[f"{table}_json"] = "TEXT"
            else:
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        continue
                    col = f"{table}_{k}"
                    # --- FIX: Use data type inference ---
                    schema[col] = self._infer_sql_type(v)
                    row[col] = v
            
            # --- FIX: Pass parent_table to _ensure_table ---
            self._ensure_table(table, schema, parent_table)
            row_id = self._insert_row(table, parent_id, row, parent_table)

            if not self.keep_objects:
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        self._normalize(v, row_id, f"{table}_{k}", parent_table=table)

        elif isinstance(data, list):
            if self.keep_arrays:
                schema = {f"{table}_json": "TEXT"}
                row = {f"{table}_json": json.dumps(data)}
                # --- FIX: Pass parent_table to helpers ---
                self._ensure_table(table, schema, parent_table)
                self._insert_row(table, parent_id, row, parent_table)
            elif (len(data) < self.array_threshold and all(isinstance(x, (str, int, float, bool, type(None))) for x in data)):
                row = {f"{table}_item{i+1}": v for i, v in enumerate(data)}
                schema = {k: self._infer_sql_type(v) for k, v in row.items()}
                # --- FIX: Pass parent_table to helpers ---
                self._ensure_table(table, schema, parent_table)
                self._insert_row(table, parent_id, row, parent_table)
            else:
                for item in data:
                    self._normalize(item, parent_id, table, parent_table)
        else: # Primitive value
            schema = {f"{table}_value": self._infer_sql_type(data)}
            row = {f"{table}_value": data}
            # --- FIX: Pass parent_table to helpers ---
            self._ensure_table(table, schema, parent_table)
            self._insert_row(table, parent_id, row, parent_table)

    def load_json(self, json_data: Union[str, List, Dict]):
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        root_table = self.root_table
        if isinstance(data, list):
            for item in data:
                self._normalize(item, None, root_table)
        elif isinstance(data, dict):
            self._normalize(data, None, root_table)
        else:
            raise ValueError("Root must be object or array")
        self.conn.commit()
        


TEST_PROGRAM_SOURCE = """
REM --- Test complex IF statement ---
PRINT "DbBasic Interpreter By Data Design Group, Inc. 
PRINT "Written by Dan Bailey"
PRINT
PRINT "Usage: dbbasic -                for stdin
PRINT "       dbasic myprogram.bas     to run script  
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

# Replace your entire main function with this one.

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

    filepath = None 
    base_dir = ''
    if args[0] == '-':
        source_code = sys.stdin.read()
        source_name = "stdin"
        cmd_args = args[1:]
        # For stdin, the base path for includes is the current working directory.
        base_dir = os.getcwd()
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
        # For a file, the base path is the directory containing that file.
        base_dir = os.path.dirname(os.path.abspath(filepath))

    processed_source_code = preprocess_includes(source_code, base_path=base_dir)
    #print("DEBUG:","MAIN",processed_source_code)
    
    # This line will no longer fail because processed_source_code will be a string.
    new_source_code = preprocess_continuations(processed_source_code)
    
    # This check now correctly uses the final processed code.
    if processed_source_code and processed_source_code.strip():
        run_interpreter(new_source_code, cmd_args, source_name, debug=is_debug, dump_tokens=dump_tokens_flag)
    else:
        print("No source code provided.", file=sys.stderr)
        
if __name__ == "__main__":
    main()
