import cli2
import os
import multiprocessing
import sqlite3
import time
from tree_sitter_language_pack import get_language, get_parser
from typing import Dict, Optional, Tuple, List
from tqdm import tqdm
from queue import Empty
import fnmatch

DB_FILE = 'repo_symbols.db'
EXCLUDE_DIRS = ['.git', 'node_modules', '.tox', '__pycache__', '*.egg-info']

def init_db():
    """Initialize the SQLite database with WAL mode."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            mtime REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            type TEXT,
            name TEXT,
            line_number INTEGER,
            FOREIGN KEY (file_id) REFERENCES files(id)
        )
    ''')
    conn.commit()
    conn.close()

def scan_file(args: Tuple[str, dict, multiprocessing.Queue, Dict[str, Tuple[Optional[float], bool]]]) -> Tuple[str, Optional[List[dict]], float]:
    """Scan a file if needed and send to queue."""
    file_path, language_extensions, queue, file_cache = args
    current_mtime = os.path.getmtime(file_path)

    # Check if file exists in DB and has symbols
    stored_mtime, has_symbols = file_cache.get(file_path, (None, False))
    if stored_mtime == current_mtime and has_symbols:
        cli2.log.debug('cached', path=file_path)
        return file_path, None, current_mtime

    ext = os.path.splitext(file_path)[1]
    if ext in [ext for exts in language_extensions.values() for ext in exts]:
        try:
            lang = next(lang for lang, exts in language_extensions.items() if ext in exts)
            language = get_language(lang)
            parser = get_parser(lang)

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = parser.parse(content.encode('utf-8'))
            symbols = extract_symbols(tree, lang, content)
            queue.put((file_path, symbols, current_mtime))
            cli2.log.debug('scanned', path=file_path)
            return file_path, symbols, current_mtime
        except Exception as e:
            cli2.log.warn(str(e), path=file_path)
            queue.put((file_path, None, current_mtime))
    else:
        cli2.log.debug('skipped', path=file_path)
    return file_path, None, current_mtime

def extract_symbols(tree, language: str, file_content: str) -> List[dict]:
    """Extract symbols from the AST."""
    queries = {
        'python': '''
            (function_definition name: (identifier) @func)
            (class_definition name: (identifier) @class)
        ''',
        'javascript': '''
            (function_declaration name: (identifier) @func)
            (class_declaration name: (identifier) @class)
        ''',
        'java': '''
            (method_declaration name: (identifier) @func)
            (class_declaration name: (identifier) @class)
        ''',
        'cpp': '''
            (function_definition declarator: (function_declarator declarator: (identifier) @func))
            (class_specifier name: (identifier) @class)
        ''',
        'ruby': '''
            (method name: (identifier) @func)
            (class name: (identifier) @class)
        ''',
    }
    query = queries.get(language, '')
    if not query:
        return []

    lang = get_language(language)
    q = lang.query(query)
    captures = q.captures(tree.root_node)

    symbols = []
    for tag, nodes in captures.items():
        for node in nodes:
            name = file_content[node.start_byte:node.end_byte]
            symbols.append({'name': name, 'type': tag, 'line_number': node.start_point[0] + 1})

    return symbols

def db_writer(queue: multiprocessing.Queue, total_files: int):
    """Write queue items to the database until all expected items are processed."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    processed = 0

    while processed < total_files:
        try:
            item = queue.get(timeout=1)
            if item is None:
                break
            absolute_path, symbols, mtime = item
            file_path = os.path.relpath(absolute_path, os.getcwd())
            cursor.execute('''
                INSERT INTO files (path, mtime) VALUES (?, ?)
                ON CONFLICT(path) DO UPDATE SET mtime = excluded.mtime
            ''', (file_path, mtime))
            cursor.execute('SELECT id FROM files WHERE path = ?', (file_path,))
            file_id = cursor.fetchone()[0]

            cursor.execute('DELETE FROM symbols WHERE file_id = ?', (file_id,))
            if symbols:
                for symbol in symbols:
                    cursor.execute('''
                        INSERT INTO symbols (file_id, type, name, line_number)
                        VALUES (?, ?, ?, ?)
                    ''', (file_id, symbol['type'], symbol['name'], symbol['line_number']))
            processed += 1
            conn.commit()
            cli2.log.info('updated', path=file_path)
        except Empty:
            continue

    conn.close()
    cli2.log.info(f"DB writer finished, processed {processed} files")

def scan_repo(repo_path: str = os.getcwd()) -> Dict[str, List[dict]]:
    """Scan the repository with concurrent database writes."""
    symbol_data = {}
    manager = multiprocessing.Manager()
    queue = manager.Queue()

    language_extensions = {
        'python': ['.py'],
        'javascript': ['.js', '.jsx'],
        'java': ['.java'],
        'cpp': ['.cpp', '.h', '.hpp', '.cxx'],
        'ruby': ['.rb'],
    }

    file_paths = []
    for root, dirs, files in os.walk(repo_path, topdown=True):
        dirs[:] = [d for d in dirs if not d.startswith('.') and not any(fnmatch.fnmatch(d, pattern) for pattern in EXCLUDE_DIRS)]
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)

    total_files = len(file_paths)
    if total_files == 0:
        print("No files found to scan.")
        return {}

    # Fetch all file metadata in one query
    if os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.path, f.mtime, COUNT(s.id) > 0 as has_symbols
            FROM files f
            LEFT JOIN symbols s ON f.id = s.file_id
            GROUP BY f.id, f.path
        ''')
        file_cache = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}  # {path: (mtime, has_symbols)}
        conn.close()
    else:
        init_db()
        file_cache = dict()

    cpu_count = os.cpu_count() or 1
    print(f"Scanning {total_files} files using {cpu_count} processes in {repo_path}...")

    with multiprocessing.Pool(processes=cpu_count) as pool:
        writer_process = multiprocessing.Process(target=db_writer, args=(queue, total_files))
        writer_process.start()

        with tqdm(total=total_files, desc="Scanning files", unit="file") as pbar:
            results = pool.imap_unordered(scan_file, [(fp, language_extensions, queue, file_cache) for fp in file_paths])
            for file_path, symbols, _ in results:
                if symbols:
                    symbol_data[file_path] = symbols
                pbar.update(1)

        queue.put(None)
        writer_process.join()

    return symbol_data

def optimize_repo_map(token_budget: int = 10000, fileglob: str = '*') -> str:
    """Optimize the repo map by querying the database with a fileglob filter."""
    optimized_map = []
    current_tokens = 0

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT f.path, COUNT(s.id) as symbol_count
        FROM files f
        LEFT JOIN symbols s ON f.id = s.file_id
        GROUP BY f.id, f.path
        ORDER BY symbol_count DESC
    ''')
    files = [(path, count) for path, count in cursor.fetchall() if fnmatch.fnmatch(path, fileglob)]

    for file_path, _ in files:
        cursor.execute('''
            SELECT type, name, line_number
            FROM symbols
            WHERE file_id = (SELECT id FROM files WHERE path = ?)
        ''', (file_path,))
        symbols = [{'type': row[0], 'name': row[1], 'line_number': row[2]} for row in cursor.fetchall()]

        file_entry = f"File: {file_path}\n"
        symbol_entries = [f"{symbol['type']}: {symbol['name']} (line {symbol['line_number']})" for symbol in symbols]
        entry = file_entry + '\n'.join(symbol_entries) + '\n'
        token_count = len(entry) // 4

        if current_tokens + token_count <= token_budget:
            optimized_map.append(entry)
            current_tokens += token_count
        else:
            break

    conn.close()
    return ''.join(optimized_map)

def main():
    repo_path = os.getcwd()

    print("Scanning repository...")
    symbol_data = scan_repo(repo_path)

    print("Optimizing for LLM...")
    repo_map = optimize_repo_map(fileglob='*.py')

    print("\nRepository Map:")
    print(repo_map)

    with open('repo_map.txt', 'a', encoding='utf-8') as f:
        f.write(repo_map + '\n')

if __name__ == "__main__":
    main()
