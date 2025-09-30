import http.server
import os
import sys
import io
import cgi
import threading
import re
from urllib.parse import urlparse, parse_qs

# Import the necessary components from your DbBasic interpreter file
from dbbasic import Interpreter, Lexer, preprocess_continuations, preprocess_includes


def preprocess_htb_includes(content, base_path='.', included_files=None):
    """
    Recursively finds all <% INCLUDE "filename" %> statements in .htb files
    and replaces them with the content of the specified file.
    """
    if included_files is None:
        included_files = set()

    # Regex to find <% INCLUDE "file.htb" %>
    include_pattern = re.compile(r'<%\s*INCLUDE\s+"([^"]+)"\s*%>', re.IGNORECASE)

    def replacer(match):
        include_filename = match.group(1)
        include_path = os.path.join(base_path, include_filename)
        absolute_path = os.path.abspath(include_path)
        if absolute_path in included_files:
            return f""

        included_files.add(absolute_path)
        try:
            with open(include_path, 'r', encoding='utf-8') as f:
                included_content = f.read()
            # Recursively process includes within the included file
            new_base_path = os.path.dirname(include_path)
            return preprocess_htb_includes(included_content, new_base_path, included_files)
        except FileNotFoundError:
            return f""
        except Exception as e:
            return f""

    return include_pattern.sub(replacer, content)
    
# --- Configuration ---
HOST_NAME = 'localhost'
PORT_NUMBER = 8000
SCRIPT_DIR = '.' # Directory where your .bas and .htb web scripts are located

class DbBasicHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    Custom request handler that executes DbBasic scripts and processes .htb files.
    """
    def do_GET(self):
        """Handles GET requests."""
        self.run_script()

    def do_POST(self):
        """Handles POST requests."""
        form_data = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     })
        self.run_script(form_data=form_data)


    def process_htb_file(self, content, form_data=None):
        """
        Process .htb files by converting them to DbBasic code and executing.
        """
        self.setup_request_data(form_data)

        dbbasic_code = self.convert_template_to_dbbasic(content)

        try:
            old_stdout = sys.stdout
            sys.stdout = captured = io.StringIO()

            db_interpreter.execute(dbbasic_code)

            sys.stdout = old_stdout
            return captured.getvalue()

        except Exception as e:
            return f"ERROR: {str(e)}\n\nGenerated code:\n{dbbasic_code}"

    def convert_template_to_dbbasic(self, content: str) -> str:
        if not content.endswith("\n"):
            content += "\n"

        out = []
        i = 0
        
        def escape_for_print(text):
            """Escape text for use in PRINT statements."""
            # First try backticks if no backticks in the text
            if '`' not in text:
                return f'`{text}`'
            # Otherwise escape double quotes
            escaped = text.replace('"', '""')
            return f'"{escaped}"'
        
        while i < len(content):
            # Look for <%
            if content[i:i+2] == '<%':
                if content[i+2:i+3] == '=':
                    # <%=expression%> - inline print expression
                    i += 3  # Skip <%=
                    expr_start = i
                    while i < len(content) and content[i:i+2] != '%>':
                        i += 1
                    expr = content[expr_start:i].strip()
                    out.append(f'PRINT {expr};\n')
                    i += 2  # Skip %>
                    
                    # Check for text after %> on the same line
                    text_start = i
                    while i < len(content) and content[i] != '\n' and content[i:i+2] != '<%':
                        i += 1
                        
                    if i > text_start:
                        text = content[text_start:i]
                        out.append(f'PRINT {escape_for_print(text)}\n')
                        
                    # Skip the newline if present
                    if i < len(content) and content[i] == '\n':
                        i += 1
                        
                else:
                    # <%code%> - code block (can be multiline)
                    i += 2  # Skip <%
                    code_start = i
                    while i < len(content) and content[i:i+2] != '%>':
                        i += 1
                    code = content[code_start:i].strip()
                    
                    # Output the code as-is, preserving the original formatting
                    if code:
                        # Don't split by lines, just output the code block as-is
                        # but ensure it ends with a newline
                        if not code.endswith('\n'):
                            code += '\n'
                        out.append(code)
                            
                    i += 2  # Skip %>
                    
                    # Skip rest of line if it only contains whitespace
                    while i < len(content) and content[i] in ' \t':
                        i += 1
                    if i < len(content) and content[i] == '\n':
                        i += 1
                        
            else:
                # Regular HTML/text - process line by line
                line_start = i
                
                # Check if this line contains any <%
                line_end = i
                has_code = False
                while line_end < len(content) and content[line_end] != '\n':
                    if content[line_end:line_end+2] == '<%':
                        has_code = True
                        break
                    line_end += 1
                
                if has_code:
                    # This line has embedded code - handle text before it
                    text = content[line_start:line_end]
                    if text:
                        out.append(f'PRINT {escape_for_print(text)};\n')
                    i = line_end
                else:
                    # Simple line without code
                    text = content[line_start:line_end]
                    out.append(f'ECHO {text}\n')
                    i = line_end
                    if i < len(content) and content[i] == '\n':
                        i += 1
        
        result = ''.join(out)
        # Clean up any double newlines at the end
        while result.endswith('\n\n'):
            result = result[:-1]
        if not result.endswith('\n'):
            result += '\n'
        return result



    def setup_request_data(self, form_data=None):
        """Setup REQUEST hash with request data."""
        parsed_path = urlparse(self.path)
        
        request_hash = {}
        request_hash['METHOD'] = self.command
        request_hash['PATH'] = parsed_path.path
        request_hash['QUERY_STRING'] = parsed_path.query

        # Parse query string parameters
        query_params = parse_qs(parsed_path.query)
        request_hash['QUERY'] = {k: v[0] for k, v in query_params.items()}

        # Parse POST form data
        form_params = {}
        if form_data:
            for key in form_data.keys():
                form_params[key] = form_data[key].value
        request_hash['FORM'] = form_params
        
        # Assign to interpreter
        db_interpreter.variables['REQUEST'] = request_hash

    def run_script(self, form_data=None):
        """
        Execute DbBasic scripts (.bas) or process template files (.htb).
        """
        # Get the path to the requested script
        parsed_path = urlparse(self.path)
        script_path = os.path.join(SCRIPT_DIR, parsed_path.path.lstrip('/'))

        # Handle directory requests - look for index files
        if os.path.isdir(script_path):
            # Try index.htb first, then index.bas
            for index_file in ['index.htb', 'index.bas']:
                index_path = os.path.join(script_path, index_file)
                if os.path.exists(index_path):
                    script_path = index_path
                    break
            else:
                self.send_error(404, "No index file found.")
                return

        # Check if file exists and has supported extension
        if not os.path.exists(script_path):
            self.send_error(404, "File not found.")
            return
        
        if not (script_path.endswith('.bas') or script_path.endswith('.htb')):
            self.send_error(404, "Unsupported file type.")
            return

        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            if script_path.endswith('.htb'):
                source_code = preprocess_htb_includes(source_code, base_path=os.path.dirname(script_path))
                dbbasic_code = self.convert_template_to_dbbasic(source_code)
                self.setup_request_data(form_data)
                
                # --- MODIFICATION STARTS HERE ---

                # Call the interpreter and get the result
                result = db_interpreter.execute(dbbasic_code)
                
                # Check if the result is a redirect signal
                if isinstance(result, tuple) and result[0] == 'redirect':
                    _, destination_url = result
                    self.send_response(303) # 303 See Other is correct for this
                    self.send_header('Location', destination_url)
                    self.end_headers()
                    return # Stop further processing

                # If not a redirect, it's HTML content
                body = result
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(body.encode('utf-8'))

                # --- MODIFICATION ENDS HERE ---

            else: # .bas file logic (remains mostly the same but simplified)
                self.setup_request_data(form_data)

                # --- MODIFICATION STARTS HERE ---

                result = db_interpreter.execute(source_code)
                
                if isinstance(result, tuple) and result[0] == 'redirect':
                    _, destination_url = result
                    self.send_response(303)
                    self.send_header('Location', destination_url)
                    self.end_headers()
                    return

                # --- The rest of the .bas logic for parsing headers from output ---
                # This part is complex, the HTB approach is cleaner.
                # If you only use HTB files for web, you can simplify this.
                response_text = result
                if '\n\n' in response_text:
                    headers_str, body = response_text.split('\n\n', 1)
                elif '\r\n\r\n' in response_text:
                    headers_str, body = response_text.split('\r\n\r\n', 1)
                else:
                    headers_str = "Content-Type: text/plain; charset=utf-8"
                    body = response_text
                
                self.send_response(200)
                for line in headers_str.strip().splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        self.send_header(key.strip(), value.strip())
                self.end_headers()
                self.wfile.write(body.encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Script execution error: {str(e)}")

if __name__ == '__main__':
    import webbrowser
    # Create persistent interpreter instance
    print("Initializing persistent DbBasic interpreter...")
    db_interpreter = Interpreter(Lexer(""))
    
    # Use single-threaded HTTPServer
    server_address = (HOST_NAME, PORT_NUMBER)
    httpd = http.server.HTTPServer(server_address, DbBasicHTTPRequestHandler)
    
    print(f"DbBasic Web Server started on http://{HOST_NAME}:{PORT_NUMBER}")
    print("Supported files: .bas (DbBasic scripts) and .htb (HTML with embedded DbBasic)")
    print("Place your scripts in the same directory and access them in your browser.")
    print("Press Ctrl+C to stop the server.")
    
    # Auto-open browser after a short delay to ensure server is ready
    def open_browser():
        import time
        time.sleep(1)  # Give server time to start
        webbrowser.open(f'http://{HOST_NAME}:{PORT_NUMBER}')
    
    # Start browser in background thread (this is fine, it's just opening a browser)
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # Run server in main thread (blocking call)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCtrl+C received, shutting down server...")
    
    httpd.shutdown()
    httpd.server_close()
    print("Server stopped.")
