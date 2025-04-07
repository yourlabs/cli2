import cli2
import os
import multiprocessing
from tree_sitter_language_pack import get_language, get_parser
from peewee import fn
from typing import Dict, Optional, Tuple, List
from tqdm import tqdm
from queue import Empty
import fnmatch
import subprocess
from .orm import db, Language, File, Symbol, Reference

EXCLUDE_DIRS = ['.git', 'node_modules', '.tox', '__pycache__', '*.egg-info']

def filter_paths(paths):
    from pathlib import Path
    gitignore = Path(os.getcwd()) / '.gitignore'
    if gitignore.exists():
        result = subprocess.run(
            ['git', 'check-ignore'] + [str(path) for path in paths],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        ignore = result.stdout.splitlines()
        return [path for path in paths if str(path) not in ignore]
    return paths

def scan_file(args: Tuple[str, dict, multiprocessing.Queue, Dict[str, Tuple[Optional[float], bool]]]) -> Tuple[str, Optional[List[dict]], float]:
    file_path, language_extensions, queue, file_cache = args
    current_mtime = os.path.getmtime(file_path)

    stored_mtime, has_symbols = file_cache.get(file_path, (None, False))
    # Only scan if file is new or modified
    if stored_mtime is not None and current_mtime <= stored_mtime and has_symbols:
        cli2.log.debug('cached', path=file_path)
        return file_path, None, current_mtime

    ext = os.path.splitext(file_path)[1]
    if ext in [ext for exts in language_extensions.values()]:
        try:
            lang = next(lang for lang, exts in language_extensions.items() if ext in exts)
            parser = get_parser(lang)

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            token_count = len(content.split())
            tree = parser.parse(content.encode('utf-8'))
            symbols, ref_counts = extract_symbols(tree, lang, content)
            queue.put((file_path, symbols, ref_counts, current_mtime, lang, token_count))
            cli2.log.debug('scanned', path=file_path)
            return file_path, symbols, current_mtime
        except Exception as e:
            cli2.log.warn(str(e), path=file_path)
            queue.put((file_path, None, {}, current_mtime, None, 0))
    else:
        cli2.log.debug('skipped', path=file_path)
    return file_path, None, current_mtime

def extract_symbols(tree, language: str, file_content: str) -> Tuple[List[dict], Dict[str, int]]:
    # [Unchanged extract_symbols function]
    def_queries = {
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
            (function_definition declarator: (identifier) @func)
            (class_specifier name: (identifier) @class)
        ''',
        'ruby': '''
            (method name: (identifier) @func)
            (class name: (constant) @class)
        ''',
    }
    ref_queries = {
        'python': '''
            (call function: (identifier) @call)
            (attribute object: (identifier) @obj)
        ''',
        'javascript': '''
            (call_expression function: (identifier) @call)
            (member_expression object: (identifier) @obj)
        ''',
        'java': '''
            (method_invocation name: (identifier) @call)
            (field_access field: (identifier) @obj)
        ''',
        'cpp': '''
            (call_expression function: (identifier) @call)
            (field_expression field: (identifier) @obj)
        ''',
        'ruby': '''
            (call method: (identifier) @call)
            (method_call receiver: (identifier) @obj)
        ''',
    }

    query_def = def_queries.get(language, '')
    query_ref = ref_queries.get(language, '')
    if not query_def or not query_ref:
        return [], {}

    lang = get_language(language)
    q_def = lang.query(query_def)
    def_captures = q_def.captures(tree.root_node)
    definitions = []
    def_names = set()
    for tag, nodes in def_captures.items():
        for node in nodes:
            name = file_content[node.start_byte:node.end_byte]
            definitions.append({'name': name, 'type': tag, 'line_number': node.start_point[0] + 1})
            def_names.add(name)

    q_ref = lang.query(query_ref)
    ref_captures = q_ref.captures(tree.root_node)
    ref_counts = {}
    for tag, nodes in ref_captures.items():
        for node in nodes:
            name = file_content[node.start_byte:node.end_byte]
            if name not in def_names:
                ref_counts[name] = ref_counts.get(name, 0) + 1

    return definitions, ref_counts

def db_writer(queue: multiprocessing.Queue, total_files: int):
    """Write symbols and initial references to the database."""
    with db:
        processed = 0
        while processed < total_files:
            try:
                item = queue.get(timeout=1)
                if item is None:
                    break
                absolute_path, symbols, ref_counts, mtime, lang_name, token_count = item
                file_path = os.path.relpath(absolute_path, os.getcwd())

                with db.atomic():
                    language = Language.get_or_none(Language.name == lang_name) if lang_name else None
                    file, created = File.get_or_create(
                        path=file_path,
                        defaults={'mtime': mtime, 'language': language, 'token_count': token_count}
                    )
                    if not created and file.mtime < mtime:  # Only update if mtime increased
                        file.mtime = mtime
                        file.language = language
                        file.token_count = token_count
                        file.save()

                        Symbol.delete().where(Symbol.file == file).execute()
                        symbol_ids = {}
                        if symbols:
                            for s in symbols:
                                symbol = Symbol.create(file=file, type=s['type'], name=s['name'], line_number=s['line_number'])
                                symbol_ids[s['name']] = symbol.id

                        Reference.delete().where(Reference.file == file).execute()
                        if ref_counts and symbol_ids:
                            ref_data = [
                                {'symbol': symbol_ids[name], 'file': file, 'count': count}
                                for name, count in ref_counts.items() if name in symbol_ids
                            ]
                            if ref_data:
                                Reference.insert_many(ref_data).execute()

                processed += 1
                cli2.log.info('updated', path=file_path)
            except Empty:
                continue
    cli2.log.info(f"DB writer finished, processed {processed} files")

def process_references(args: Tuple[File, Dict[str, int], Dict[str, int], multiprocessing.Queue, set]):
    """Process cross-file references for a single file if it was updated."""
    file, ref_counts_all, all_symbols, progress_queue, updated_files = args
    db.connect(reuse_if_open=True)
    db.create_tables([Language, File, Symbol, Reference], safe=True)

    # Only process references if the file was updated
    if file.path in updated_files:
        refs = ref_counts_all
        ref_data = []
        for name, count in refs.items():
            if name in all_symbols and name not in [s.name for s in file.symbols]:
                ref_data.append({
                    'symbol': all_symbols[name],
                    'file': file,
                    'count': count
                })

        if ref_data:
            with db.atomic():
                Reference.delete().where(Reference.file == file).execute()  # Clear old refs for updated file
                Reference.insert_many(ref_data).on_conflict(
                    conflict_target=[Reference.symbol, Reference.file],
                    update={Reference.count: count}
                ).execute()

    db.close()
    progress_queue.put(1)
    return file.path

def repo(repo_path: str = os.getcwd()) -> Dict[str, List[dict]]:
    """Scan the repository and handle cross-file references incrementally."""
    symbol_data = {}
    manager = multiprocessing.Manager()
    queue = manager.Queue()
    ref_counts_all = manager.dict()
    updated_files = manager.dict()  # Track files that were rescanned

    language_extensions = {
        'python': ['.py'],
        'javascript': ['.js', '.jsx'],
        'java': ['.java'],
        'cpp': ['.cpp', '.h', '.hpp', '.cxx'],
        'ruby': ['.rb'],
    }

    db.create_tables([Language, File, Symbol, Reference], safe=True)

    file_paths = []
    for root, dirs, files in os.walk(repo_path, topdown=True):
        dirs[:] = [d for d in dirs if not d.startswith('.') and not any(fnmatch.fnmatch(d, pattern) for pattern in EXCLUDE_DIRS)]
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)

    file_paths = filter_paths(file_paths)
    total_files = len(file_paths)
    if total_files == 0:
        print("No files found to scan.")
        return {}

    file_cache = {
        f.path: (f.mtime, len(f.symbols) > 0)
        for f in File.select(File.path, File.mtime, fn.COUNT(Symbol.id).alias('symbol_count'))
            .left_outer_join(Symbol, on=(File.id == Symbol.file_id))
            .group_by(File)
    }
    db.close()

    cpu_count = os.cpu_count() or 1
    print(f"Scanning {total_files} files using {cpu_count} processes in {repo_path}...")

    with multiprocessing.Pool(processes=cpu_count) as pool:
        writer_process = multiprocessing.Process(target=db_writer, args=(queue, total_files))
        writer_process.start()

        results = pool.imap_unordered(scan_file, [(fp, language_extensions, queue, file_cache) for fp in file_paths])
        for file_path, symbols, _ in tqdm(results, total=total_files, desc="Scanning files", unit="file"):
            if symbols:  # File was rescanned
                symbol_data[file_path] = symbols
                updated_files[file_path] = True
            try:
                while True:
                    item = queue.get_nowait()
                    _, _, ref_counts, _, _, _ = item
                    for name, count in ref_counts.items():
                        ref_counts_all[name] = ref_counts_all.get(name, 0) + count
            except Empty:
                pass

        pool.close()
        pool.join()
        queue.put(None)
        writer_process.join()

    # Process cross-file references with multiprocessing
    db.connect()
    all_symbols = manager.dict({s.name: s.id for s in Symbol.select(Symbol.name, Symbol.id)})
    all_files = [*File.select()]
    total_files_in_db = len(all_files)
    db.close()
    print(f"Files in DB after scan: {total_files_in_db}")

    if total_files_in_db > 0 and updated_files:
        print("Processing cross-file references for updated files...")
        progress_queue = manager.Queue()
        with multiprocessing.Pool(processes=cpu_count) as pool:
            files_to_process = [(f, ref_counts_all, all_symbols, progress_queue, updated_files) for f in all_files]
            results = pool.imap_unordered(process_references, files_to_process)

            with tqdm(total=total_files_in_db, desc="Updating references", unit="file") as pbar:
                processed = 0
                for _ in results:
                    try:
                        while True:
                            progress_queue.get_nowait()
                            processed += 1
                            pbar.update(1)
                    except Empty:
                        if processed >= total_files_in_db:
                            break
                        continue

    return symbol_data
