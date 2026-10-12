"""Check or fix tracked repository text. No network access or external packages."""
import argparse
import fnmatch
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

DOCS = {'.md', '.markdown', '.rst', '.txt', '.html', '.htm', '.svg'}
BINARY = {'.png','.jpg','.jpeg','.gif','.webp','.ico','.pdf','.zip','.gz','.7z',
          '.mp4','.mp3','.wav','.woff','.woff2','.ttf','.exe','.dll','.bin',
          '.docx','.xlsx','.pptx','.db','.pyc','.safetensors','.gguf','.parquet'}


def patterns(encoded=False):
    result = [re.compile(chr(8212))]
    if encoded:
        code = format(8212, '04x')
        result += [re.compile(r'\\+(?:u'+code+r'|u\{'+code+r'\}|U0000'+code+r'|N\{EM DASH\})', re.I),
                   re.compile(r'&(?:amp;)*(?:mdash;|\#0*'+str(8212)+r'(?![0-9]);?|\#x0*'+code+r'(?![0-9a-f]);?)', re.I),
                   re.compile('%'+'E2%80%94', re.I),
                   re.compile(r'\\+x[eE]2\\+x80\\+x94'),
                   re.compile(chr(226)+chr(8364)+chr(8221)),
                   re.compile(r'\\+(?:textemdash|emdash)\b')]
    return result


def replace(text, replacement='-', encoded=False):
    count = 0
    for pattern in patterns(encoded):
        # A callable keeps replacement backslashes literal.
        text, found = pattern.subn(lambda _: replacement, text)
        count += found
    return text, count


def decode(data):
    if data.startswith(b'\xff\xfe'):
        return data[2:].decode('utf-16-le'), 'utf-16-le', b'\xff\xfe'
    if data.startswith(b'\xfe\xff'):
        return data[2:].decode('utf-16-be'), 'utf-16-be', b'\xfe\xff'
    if b'\0' in data:
        raise ValueError('binary content')
    return data.decode('utf-8'), 'utf-8', b''


def tracked(root):
    run = subprocess.run(['git', '-C', str(root), 'ls-files', '--stage', '-z'],
                         capture_output=True, check=True)
    for row in run.stdout.split(b'\0'):
        if not row:
            continue
        info, filename = row.split(b'\t', 1)
        mode, _, stage = info.split()
        if stage != b'0':
            raise ValueError('Resolve merge conflicts before scanning')
        if mode in (b'100644', b'100755'):
            yield os.fsdecode(filename)


def confined(root, path):
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return False
    current = path
    while current != root:
        if current.is_symlink():
            return False
        current = current.parent
    return True


def scan(root, fix=False, all_text=False, encoded=False, replacement='-', excludes=(), max_bytes=2*1024*1024):
    root = Path(root).resolve()
    if not root.is_dir() or not 1 <= max_bytes <= 100*1024*1024:
        raise ValueError('Choose an existing Git directory and a limit between 1 byte and 100 MiB')
    report = {'scanned': 0, 'changed_files': 0, 'replacements': 0, 'files': [], 'skipped': [], 'errors': []}
    for name in tracked(root):
        path = root / name
        reason = None
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in excludes): reason = 'excluded'
        elif path.suffix.lower() in BINARY: reason = 'binary format'
        elif not all_text and path.suffix.lower() not in DOCS: reason = 'outside documentation scope'
        elif not confined(root, path): reason = 'symlink or outside repository'
        elif not path.is_file(): reason = 'missing working-tree file'
        elif path.stat().st_size > max_bytes: reason = 'size limit'
        if reason:
            report['skipped'].append({'path': name, 'reason': reason})
            continue
        try:
            original = path.read_bytes()
            if len(original) > max_bytes:
                raise ValueError('file grew beyond size limit')
            text, encoding, prefix = decode(original)
            revised, count = replace(text, replacement, encoded)
            report['scanned'] += 1
            if not count:
                continue
            updated = prefix + revised.encode(encoding)
            if path.suffix.lower() in ('.json', '.ipynb'):
                # Validate new JSON only if the original was valid JSON.
                try: json.loads(text)
                except ValueError: pass
                else: json.loads(revised)
            if fix:
                if not confined(root, path) or path.read_bytes() != original:
                    raise ValueError('file changed during scan')
                permission = path.stat().st_mode
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                        temporary = Path(handle.name)
                        handle.write(updated)
                    os.chmod(temporary, permission)
                    os.replace(temporary, path)
                finally:
                    if temporary is not None and temporary.exists(): temporary.unlink()
            report['changed_files'] += 1
            report['replacements'] += count
            report['files'].append({'path': name, 'replacements': count, 'written': fix})
        except (UnicodeError, ValueError) as error:
            if isinstance(error, UnicodeError) or str(error) == 'binary content':
                report['skipped'].append({'path': name, 'reason': 'unsupported encoding or binary content'})
            else:
                report['errors'].append({'path': name, 'error': str(error)})
        except OSError as error:
            report['errors'].append({'path': name, 'error': type(error).__name__})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['check','fix','report'], default='check')
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--all-text', action='store_true')
    parser.add_argument('--encoded', action='store_true')
    parser.add_argument('--replacement', default='-')
    parser.add_argument('--exclude', action='append', default=[])
    parser.add_argument('--max-bytes', type=int, default=2*1024*1024)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    try:
        result = scan(args.root, args.mode == 'fix', args.all_text, args.encoded,
                      args.replacement, args.exclude, args.max_bytes)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print('Cannot scan repository: '+type(error).__name__)
        return 2
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
    for item in result['files']:
        print(json.dumps(item, ensure_ascii=True))
    print(f"Scanned {result['scanned']} files; {result['replacements']} replacements in {result['changed_files']} files; {len(result['errors'])} errors.")
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as handle:
            handle.write(f"changed-files={result['changed_files']}\nreplacements={result['replacements']}\n")
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as handle:
            handle.write(f"### Em dash scan\n\nMode: {args.mode}. Scanned {result['scanned']} files, found {result['replacements']} replacements in {result['changed_files']} files. Skipped {len(result['skipped'])} files; errors: {len(result['errors'])}.\n")
    return 2 if result['errors'] else 1 if args.mode == 'check' and result['replacements'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
