class Line:
    def __init__(self, data):
        self.data = data.strip()
        self.i = 0

    def _in(self, values):
        return self.i < len(self.data) and self.data[self.i] in values

    def _not_in(self, values):
        return self.i < len(self.data) and self.data[self.i] not in values

    def _next(self):
        ch = self.data[self.i]
        self.i += 1
        return ch 

    def next(self, separators, quotes = ''):
        result = []
        if self._in(quotes):
            quote = self.data[self.i]
            while self._in(quote):
                self._next()
                while self._not_in(quote):
                    result.append(self._next())
                assert self._next() == quote, f'Unbalanced quotes {self.data}'
        else:
            while self._not_in(separators):
                result.append(self._next())

        while self._in(separators):
            self._next()

        return ''.join(result)


def download(url):
    from requests import Session
    from requests_file import FileAdapter
    with Session() as session:
        session.mount('file://', FileAdapter())

        result = session.get(url)
        if result.status_code != 200:
            raise Exception(f'Status code {result.status_code}')
        return result.content


def save(filename, data):
    with open(filename, 'wb') as f:
        f.write(data)


def extract_filename(url):
    from urllib.parse import urlparse
    path = urlparse(url, allow_fragments=False).path
    index = path.rfind('/')
    return path if index < 0 else path[index + 1:]


def load_yaml(filename):
    import yaml

    with open(filename, 'r', encoding='utf8') as f:
        result = yaml.safe_load(f)
        result['__path'] = filename
        return result

def get_yaml(node, key, default = None):
    if key in node:
        result = node[key]
        if result is dict:
            result['__path'] = f'{node["__path"]}/{key}'
        return result
    elif default is not None:
        return default
    else:
        raise Exception(f'Key "{key}" not found in {node["__path"]}')

def parse_meta(data, encoding):
    META_SEPARATOR = 26
    index = data.find(META_SEPARATOR)
    meta = (data if index < 0 else data[index + 1:]).decode(encoding)

    from types import SimpleNamespace

    problems = []
    sessions = []
    runs = []
    contest = ''

    for line in [Line(s) for s in meta.splitlines()]:
        if line.data == '':
            continue 
        action = line.next(' ')
        if action == '@contest':
            # @contest "LIX St. Petersburg State University Championship, Sunday, May 12, 2024"
            contest = line.next(',', quotes='"')
        elif action == '@p':
            # @p L,Конфеты,20,0
            letter = line.next(',')
            name = line.next(',', quotes='"')
            problems.append(SimpleNamespace(letter=letter, name= name))
        elif action == '@t':
            # @t 01,0,1,"YKKONEN (Титов, Габитов, Аграновский)"
            party_id = line.next(',')
            flags = line.next(','), line.next(',')
            name = line.next(',', quotes='"')
            sessions.append(SimpleNamespace(id=party_id, name=name))
        elif action == '@s':
            # @s 39,C,1,422,WA,5
            party_id = line.next(',')
            letter = line.next(',')
            attempt = line.next(',')
            time = line.next(',')
            outcome = line.next(',')
            test = line.next(',')
            runs.append(SimpleNamespace(
                party_id=party_id,
                letter=letter,
                attempt=attempt,
                time=time,
                outcome=outcome,
                test=test,
            ))
        else:
            assert action in [
                '@startat', '@contlen', 
                '@now', '@state', '@freeze', 
                '@problems', '@teams', '@submissions', 
                '@comment'
            ], f'Unknown action {action}: {line.data}'
    return SimpleNamespace(contest=contest, problems=problems, sessions=sessions, runs=runs)


def write_xml_list(filename, root, root_attrs, tag, items):
    import xml.etree.ElementTree as ET

    xml = ET.TreeBuilder()
    xml.start(root, root_attrs)
    for item in items:
        xml.start(tag, item)
        xml.end(tag)

    document = ET.ElementTree(xml.end(root))
    if hasattr(ET, 'indent'):
        ET.indent(document, space="    ", level=0)
    document.write(filename, encoding="UTF-8", xml_declaration=True)


def write_challenge(name, problems, config):
    write_xml_list(
        config.challenge_xml,
        'challenge', 
        {
            'id': config.challenge_id,
            'name': name,
            'scoring-model': config.scoring_model,
            'xmlai-process':  'http://neerc.ifmo.ru/develop/pcms2/xmlai/default-rules.xml'
        },
        'problem-ref',
        [{
            'alias': problem.letter,
            'problem-id': config.problems_prefix + config.problems[problem.letter],
            'name': problem.name
        } for problem in problems]
    )


def write_sessions(sessions, config):
    write_xml_list(
        config.sessions_xml,
        'sessions', 
        {
            'id': config.sessions_prefix[:-1],
            'party-id': config.sessions_prefix[:-1],
            'challenge-id': config.challenge_id,
            'clock-id': config.clock_id,
            'xmlai-process':  'http://neerc.ifmo.ru/develop/pcms2/xmlai/default-rules.xml'
            },
        'session',
        [{'id': session.id} for session in sessions]
    )


def write_contest(name, sessions, config):
    write_xml_list(
        config.contest_xml,
        'contest', 
        {
            'id': config.challenge_id,
            'challenge-id': config.challenge_id,
            'clock-id': config.clock_id,
            'name': name,
            'xmlai-process':  'http://neerc.ifmo.ru/develop/pcms2/xmlai/default-rules.xml',
        },
        'session-ref',
        [{'id': session.id} for session in sessions]
    )


def write_parties(sessions, config):
    write_xml_list(
        config.parties_xml,
        'parties', 
        {
            'id': config.parties_prefix[:-1],
            'xmlai-process':  'http://neerc.ifmo.ru/develop/pcms2/xmlai/default-rules.xml'
        },
        'party',
        [{'id': session.id, 'name': session.name} for session in sessions]
    )


def write_runs(runs, config):
    write_xml_list(config.runs_xml, 'runs', {}, 'run', [
        {
            'id': f'{session_id}.{no + 1}',
            'session-id': session_id,
            'problem-id': config.problems_prefix + config.problems[run.letter],
            'time': run.time + 's',
            'accepted': 'yes' if run.outcome == 'OK' else 'no',
            'outcome': 'UD' if run.outcome == 'FZ' else run.outcome,
        }
        for no, run in enumerate(runs)
        for session_id in [config.sessions_prefix + run.party_id]
    ])


def path_to_url(path):
    from pathlib import Path
    return 'file:///' + str(Path(path).absolute().as_posix())


def parse_config(yaml):
    from types import SimpleNamespace
   
    config = SimpleNamespace()
    url                     = get_yaml(yaml, 'url')
    config.url = path_to_url(url) if '//' not in url else url

    config.filename         = get_yaml(yaml, 'filename', extract_filename(config.url))
    config.meta_encoding    = get_yaml(yaml, 'meta-encoding', 'utf8')
    config.challenge_id     = get_yaml(yaml, 'challenge-id')
    config.scoring_model    = get_yaml(yaml, 'scoring-model', '%icpc')
    config.problems_prefix  = get_yaml(yaml, 'problems-prefix', config.challenge_id + '.')
    config.problems         = get_yaml(yaml, 'problems')
    config.sessions_prefix  = get_yaml(yaml, 'sessions-prefix', config.challenge_id + '.')
    config.parties_prefix   = get_yaml(yaml, 'parties-prefix', config.challenge_id + '.')
    config.clock_id         = get_yaml(yaml, 'clock-id', config.challenge_id)

    config.xmls_prefix      = get_yaml(yaml, 'xmls-prefix', '')
    config.challenge_xml    = get_yaml(yaml, 'runs-xmls', config.xmls_prefix + 'challenge.xml')
    config.contest_xml      = get_yaml(yaml, 'runs-xmls', config.xmls_prefix + 'contest.xml')
    config.sessions_xml     = get_yaml(yaml, 'runs-xmls', config.xmls_prefix + 'sessions.xml')
    config.parties_xml      = get_yaml(yaml, 'runs-xmls', config.xmls_prefix + 'parties.xml')
    config.runs_xml         = get_yaml(yaml, 'runs-xmls', config.xmls_prefix + 'runs.xml')

    return config


def main(config_filename):
    config = parse_config(load_yaml(config_filename))

    data = download(config.url)
    save(config.filename, data)
    meta = parse_meta(data, config.meta_encoding)

    for problem in meta.problems:
        assert problem.letter in config.problems, f'Unknown problem "{problem.letter}"'

    write_challenge(meta.contest, meta.problems, config)
    write_contest(meta.contest, meta.sessions, config)
    write_sessions(meta.sessions, config)
    write_parties(meta.sessions, config)
    write_runs(meta.runs, config)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage testsys2pcms.py [config.yaml]')
        exit(1)
    else:
        main(sys.argv[1])
        exit(0)
