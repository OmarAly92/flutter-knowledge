#!/usr/bin/env python3
"""Static grader for the flutter-knowledge benchmark.

Usage: grade.py <out_dir>
  <out_dir>/fixture-{drift,hive,app}[-nowrap]       (from build_fixtures.py)
  <out_dir>/runs/<version>-<mode>-<task>-<rep>/      (one agent run each, from prepare.py)
  <out_dir>/tokens.txt  (optional: "<run name> <tokens>" per line)
Writes <out_dir>/grades.json and prints markdown tables. Runs without SKILLS_READ.txt
are skipped as unfinished.

Only code the agent wrote counts: whole new files, and the added lines of files it
edited. The legacy `orders` feature is ignored (it is the trap), except that
editing it at all is reported. A few checks look at the whole file after an edit,
to catch "extended the legacy pattern instead of following the skill".
The checks are regexes: spot-check every rule hit by reading the flagged code.
"""
import difflib, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = json.load(open(os.path.join(HERE, 'tasks.json'), encoding='utf-8'))['tasks']
B = sys.argv[1]
RUNS = os.path.join(B, 'runs')
TOKENS = {}
if os.path.exists(os.path.join(B, 'tokens.txt')):
    for line in open(os.path.join(B, 'tokens.txt')):
        if line.split():
            TOKENS[line.split()[0]] = int(line.split()[1])
ARABIC = re.compile(r'[؀-ۿ]')
SCREEN_TASKS = {'d1', 'd2', 'd3', 'h1', 'h2'}   # a new feature with its own screen
TRIP_SCREEN_TASKS = {'f1', 'f2'}                # a new screen inside the existing trips feature
TASK_SKILL = {'t1': 'flutter-testing', 'g1': 'design-from-html-flutter'}
# design/prototype.html (task g1): the values its injected CSS resolves to
DESIGN_COLORS = ['F4F6F5', 'FFFFFF', 'EDF1EF', '0E1A17', '4A5A55', '83928D', 'D6DEDA', '0F766E', '15803D', 'B45309', 'B91C1C']
DESIGN_TYPE = [(28, 34, -0.56), (20, 26, -0.2), (15, 22, 0.0), (12, 16, 0.24)]   # font size, line height, tracking (px)
DESIGN_DURATIONS = [120, 220, 360]
DESIGN_CURVES = [(0.2, 0, 0, 1), (0.34, 1.56, 0.64, 1)]
LEGACY_TEXT_GETTERS = ['style12Regular', 'style14Regular', 'style14Medium', 'style16Medium', 'style18Bold']
RAW_TO_WRAPPER = {'Text': 'app_text', 'Scaffold': 'app_scaffold', 'AppBar': 'global_appbar', 'SizedBox': 'vertical_space',
                  'ElevatedButton': 'primary_button', 'TextButton': 'primary_button', 'OutlinedButton': 'primary_button',
                  'TextFormField': 'app_text_field', 'TextField': 'app_text_field', 'CircularProgressIndicator': 'app_loader'}
WRAPPER_CLASSES = {'AppText': 'app_text', 'AppScaffold': 'app_scaffold', 'GlobalAppbar': 'global_appbar',
                   'VerticalSpace': 'vertical_space', 'HorizontalSpace': 'horizontal_space', 'AppContainer': 'app_container',
                   'PrimaryButton': 'primary_button', 'AppTextField': 'app_text_field', 'AppLoader': 'app_loader',
                   'AppErrorWidget': 'app_error_widget'}


def read(p):
    try:
        return open(p, encoding='utf-8').read()
    except Exception:
        return ''


def files(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            rel = os.path.relpath(p, root)
            if rel.startswith(('lib/', 'assets/', 'test/')) or rel == 'pubspec.yaml':
                out[rel] = p
    return out


def added_lines(old, new):
    return '\n'.join(l[2:] for l in difflib.ndiff(old.splitlines(), new.splitlines()) if l.startswith('+ '))


def role(rel):
    if rel.startswith('test/'):
        return 'test'
    if rel.startswith('lib/feature/orders/'):
        return 'legacy'
    if '/presentation/' in rel and '/logic/' in rel:
        return 'cubit'
    if '/presentation/' in rel:
        return 'ui'
    if '/repository/' in rel:
        return 'repo'
    if '/params/' in rel:
        return 'params'
    if '/data_source/' in rel:
        return 'ds'
    if re.search(r'/models?/', rel):
        return 'model'
    if rel.startswith('lib/core/database/tables/'):
        return 'db'
    if rel.startswith('lib/feature/'):
        return 'feature_other'
    return 'core'


def count(pat, text, flags=0):
    return len(re.findall(pat, text, flags))


def dao_methods(text):
    """Yield (signature, body) for each DAO method."""
    sig = re.compile(r'^\s*((?:Future|Stream)<.*?>)\s+(\w+)\s*\([^;{=]*?\)\s*(?:async\s*)?(=>|\{)', re.M | re.S)
    ms = list(sig.finditer(text))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        yield m.group(2), text[m.start():end]


def grade(run_dir, fixture_dir, task):
    fx, rn = files(fixture_dir), files(run_dir)
    v = defaultdict(int)          # rule -> hits
    info = {}
    new, touched = {}, {}         # rel -> text considered (new: all; touched: added lines)
    full = {rel: read(p) for rel, p in rn.items()}
    for rel, p in rn.items():
        if rel.endswith('.g.dart') and 'locale_keys' not in rel:
            continue
        if rel not in fx:
            new[rel] = full[rel]
        elif read(fx[rel]) != full[rel]:
            touched[rel] = added_lines(read(fx[rel]), full[rel])
    info['files_new'] = len(new)
    info['files_touched'] = sorted(touched)
    code = {**new, **touched}
    dart = {r: t for r, t in code.items() if r.endswith('.dart') and 'locale_keys' not in r}

    if any(r.startswith('lib/feature/orders/') or r == 'test/orders_repository_test.dart' for r in code):
        v['touched_legacy_orders'] += 1
    if 'lib/core/helpers/localization/locale_keys.g.dart' in touched:
        v['edited_generated_locale_keys'] += 1

    by_role = defaultdict(dict)
    for r, t in dart.items():
        by_role[role(r)][r] = t
    feat = {r: t for r, t in dart.items() if role(r) not in ('legacy', 'core', 'db', 'test')}
    ui = by_role['ui']

    # ---------------- general / UI ----------------
    for r, t in feat.items():
        v['bloc_or_events'] += count(r'extends Bloc<|\bon<\w+>\(', t)
        v['build_x_method'] += count(r'Widget\s+_build\w*\(', t)
        v['screenutil'] += count(r'flutter_screenutil|\d\.(?:h|w|r|sp)\b', t)
        v['stateful_or_initState'] += count(r'StatefulWidget|initState\(', t)
        v['scaffold_messenger'] += count(r'ScaffoldMessenger', t)
        v['endpoint_interpolation'] += count(r"'\$\{EndPoints\.|EndPoints\.\w+\s*\+", t)
        v['print_call'] += count(r'(?<![\w.])print\(', t)
        v['private_ctor_static_class'] += count(r'\b[A-Z]\w*\._\(\)\s*;', t)
        v['raw_navigator'] += count(r'\bNavigator\.(?:of|push\w*|pop\w*|maybePop)\b', t)
        if role(r) in ('ui', 'cubit'):
            v['service_locator_in_ui_or_cubit'] += count(r'\bsl<|GetIt\.instance', t)
    for r, t in new.items():
        if r.endswith('.dart') and role(r) == 'core':
            v['private_ctor_static_class'] += count(r'\b[A-Z]\w*\._\(\)\s*;', t)
    if task != 't1' and any(r.startswith('test/') for r in new):
        v['tests_unprompted'] += 1
    # raw widget where the project has a wrapper (only wrappers present in the fixture count)
    raw_ok = [w for w, f in RAW_TO_WRAPPER.items() if f'lib/core/widgets/{f}.dart' in fx]
    raw_re = r'(?<![\w.])(?:%s)\(' % '|'.join(raw_ok) if raw_ok else r'(?!x)x'
    for r, t in ui.items():
        v['raw_widget_with_wrapper'] += count(raw_re, t)
    # missing-wrapper fallback: never import or use a wrapper the project lacks, never invent one
    for r, t in feat.items():
        for w in re.findall(r"import 'package:app/core/widgets/(\w+)\.dart'", t):
            if f'lib/core/widgets/{w}.dart' not in rn:
                v['imports_missing_wrapper'] += 1
        for cls, f in WRAPPER_CLASSES.items():
            if f'lib/core/widgets/{f}.dart' not in rn and re.search(r'(?<![\w.])%s\(' % cls, t):
                v['uses_missing_wrapper'] += 1
    for r in new:
        if r.startswith('lib/core/widgets/'):
            v['created_new_wrapper'] += 1
    for r, t in ui.items():
        v['raw_color_or_textstyle'] += count(r'Color\(0x|TextStyle\(|\bColors\.(?!transparent)', t)
        v['blocprovider_in_feature'] += count(r'(?<!\.)\bBlocProvider(?:<[^>]*>)?\(|MultiBlocProvider\(', t)
        bb, bw = count(r'BlocBuilder<', t), count(r'buildWhen', t)
        v['blocbuilder_without_buildWhen'] += max(0, bb - bw)
        v['hardcoded_ui_string'] += sum(
            1 for line in t.splitlines()
            if 'LocaleKeys' not in line and re.search(
                r"(?:AppText|Text)\(\s*'\s*[A-Za-z]|(?:titleText|hintText|text|labelText|message|title|label|tooltip):\s*'\s*[A-Za-z]", line))
        # a closure that only delegates to the shared AppFormValidations is fine
        v['inline_validator'] += sum(1 for m in re.finditer(r'validator:\s*\(', t)
                                     if 'AppFormValidations' not in ''.join(t[m.end():].splitlines(True)[:3]))
    for r, t in new.items():
        if role(r) in ('ui', 'cubit', 'feature_other') and r.endswith('.dart'):
            n = count(r'class\s+\w+\s+extends\s+(?:StatelessWidget|StatefulWidget|State<)', t)
            v['multiple_widgets_per_file'] += max(0, n - 1)
    # Screen / Body split
    screens = [r for r in new if r.endswith('_screen.dart') and '/ui/' in r]
    for r in screens:
        t = new[r]
        if 'BlocListener' not in t or 'AppScaffold' not in t or not re.search(r'\w+Body\(', t):
            v['screen_body_split'] += 1
    for r, t in new.items():
        if r.endswith('_body.dart') and re.search(r'AppScaffold|Scaffold\(|GlobalAppbar|BlocListener', t):
            v['screen_body_split'] += 1
    if task in SCREEN_TASKS | TRIP_SCREEN_TASKS and not screens:
        v['no_screen_file'] += 1
    # Threading data to widgets: leaf widgets take primitives, intermediates read the cubit
    for r, t in new.items():
        if role(r) != 'ui' or '/widgets/' not in r or r.endswith('_body.dart'):
            continue
        fields = re.findall(r'^\s*final\s+([\w<>?, ]+)\s+\w+\s*;', t, re.M)
        if any(re.search(r'\b\w+Model\b', f) and not f.strip().startswith('List') for f in fields):
            v['leaf_widget_takes_whole_model'] += 1
        if any(re.match(r'List<', f.strip()) for f in fields):
            v['list_data_threaded_through_ctor'] += 1
    # Cubit / state
    cubits = {r: t for r, t in by_role['cubit'].items() if r.endswith('_cubit.dart')}
    states = {r: t for r, t in by_role['cubit'].items() if r.endswith('_state.dart')}
    for r, t in states.items():
        for name in re.findall(r'class\s+(\w+)\s+extends', t):
            if not name.endswith('State'):
                v['state_naming'] += 1
        for m in re.finditer(r'class\s+\w+SuccessState\b[^{]*\{(.*?)\n\}', t, re.S):
            if re.search(r'\bfinal\s+\w', m.group(1)):
                v['data_in_success_state'] += 1
    for r, t in states.items():
        if not re.search(r"^\s*part of ", t, re.M):
            v['state_not_part_of_cubit'] += 1
    for r, t in cubits.items():
        v['try_catch_in_cubit'] += count(r'\}\s*(?:on\s+\w+\s*)?catch\s*\(|\}\s*on\s+\w+\s*\{', t)  # try/finally alone is fine
        if re.search(r'RemoteDataSource|LocalDataSource|NetworkStatus', t):
            v['cubit_bypasses_repository'] += 1
    if task in SCREEN_TASKS | {'f1'} and cubits:
        ctor = ''.join(re.findall(r'super\([^;]*?\)\s*\{(.*?)\}', ' '.join(cubits.values()), re.S))
        if not re.search(r'\w+\(', ctor):
            v['initial_fetch_not_in_cubit_ctor'] += 1
        if task in ('d3', 'h2') and not re.search(r'sync', ctor, re.I):
            # allow a load()/helper called from the constructor that itself calls sync
            called = set(re.findall(r'(\w+)\(', ctor))
            if not any(re.search(r'Future<void>\s+(\w+)\([^)]*\)\s*async\s*\{[^}]*sync', t, re.S | re.I)
                       and any(m.group(1) in called or re.match(r'(?:load|get)', m.group(1))
                               for m in re.finditer(r'Future<void>\s+(\w+)\([^)]*\)\s*async\s*\{[^}]*sync', t, re.S | re.I))
                       for t in cubits.values()):
                v['sync_not_run_on_open'] += 1
    # Data layer
    for r, t in new.items():
        if role(r) == 'model' and r.endswith('.dart'):
            for m in re.finditer(r'^\s*final\s+([\w<>, ?]+?)\s+(\w+)\s*;', t, re.M):
                if not m.group(1).strip().endswith('?'):
                    v['model_field_non_nullable'] += 1
    for r, t in new.items():
        if role(r) == 'model' and r.endswith('.dart'):
            order = [m.start() for m in (re.search(p, t) for p in (r'^\s*final\s', r'^\s*(?:const\s+)?[A-Z]\w*Model\(', r'fromJson\(', r'toJson\(', r'props')) if m] if False else None
            marks = []
            for p_ in (r'(?m)^\s*final\s', r'(?m)^\s*(?:const\s+)?[A-Z]\w*\(\{', r'factory\s+\w+\.fromJson', r'toJson\(\)\s*(?:=>|\{)', r'get props'):
                m = re.search(p_, t)
                if m:
                    marks.append(m.start())
            if marks != sorted(marks):
                v['model_member_order'] += 1
    for r, t in new.items():
        if role(r) == 'repo':
            abstract = re.search(r'abstract\s+(?:interface\s+)?class[^{]*\{(.*?)\n\}', t, re.S)
            if abstract:
                ps = re.findall(r'\((\w+Params)\s', abstract.group(1))
                v['params_class_shared_across_methods'] += sum(1 for p_ in set(ps) if ps.count(p_) > 1)
    for r, t in by_role['ds'].items():
        v['try_catch_in_data_source'] += count(r'\btry\s*\{', t)
    leak_pat = r'package:(?:drift|hive_ce|hive_ce_flutter|hive)/|\b\w+Companion\b|\b[A-Z]\w*Entity\b|\bBox<|\bHiveObject\b'
    for rl in ('repo', 'cubit', 'ui'):
        for r, t in by_role[rl].items():
            v['storage_type_above_data_source'] += count(leak_pat, t)
    for r in list(by_role['params']):
        text = full[r]  # whole file: catches legacy toDb()->Companion kept after an edit
        v['storage_type_in_params'] += count(r'package:drift/|\b\w+Companion\b|\b[A-Z]\w*Entity\b|package:hive', text)
    for r, t in new.items():
        if role(r) == 'repo' and t and not re.search(r'abstract\s+(?:interface\s+)?class', t):
            v['repo_not_abstract_plus_imp'] += 1
        if role(r) == 'ds' and t and not re.search(r'abstract\s+(?:interface\s+)?class', t):
            v['ds_not_abstract_plus_imp'] += 1
    # DI and routing
    sl_path = 'lib/core/utils/service_locator.dart'
    sl_add = touched.get(sl_path, '')
    if task in SCREEN_TASKS and not re.search(r'static\s+void\s+_\w+FeatureSetup', sl_add):
        v['di_no_feature_setup_method'] += 1
    if task in SCREEN_TASKS | TRIP_SCREEN_TASKS:
        init_body = re.search(r'static Future<void> init\(\) async \{(.*?)\n  \}', full.get(sl_path, ''), re.S)
        if init_body:
            fixture_init = re.search(r'static Future<void> init\(\) async \{(.*?)\n  \}', read(fx[sl_path]), re.S).group(1)
            added_in_init = added_lines(fixture_init, init_body.group(1))
            v['di_inline_registration'] += count(r'sl\.register', added_in_init)
        if not re.search(r'BlocProvider', touched.get('lib/core/app_routes/app_router.dart', '')):
            v['router_case_without_blocprovider'] += 1
        rs = 'lib/core/app_routes/routes_strings.dart'
        if rs in touched and 'RoutesStrings._()' in full[rs]:
            v['legacy_private_ctor_kept_on_edit'] += 1
        if rs not in touched and not re.search(r"static const String \w+ = '/", ''.join(touched.values())):
            v['no_route_constant'] += 1
    # Localization
    en = json.loads(read(os.path.join(run_dir, 'assets/translations/en.json')) or '{}')
    ar = json.loads(read(os.path.join(run_dir, 'assets/translations/ar.json')) or '{}')
    fx_en = json.loads(read(os.path.join(fixture_dir, 'assets/translations/en.json')))
    used = set()
    for r, t in feat.items():
        used |= set(re.findall(r'LocaleKeys\.(\w+)', t))
    v['locale_key_missing_from_json'] += len([k for k in used if k not in en or k not in ar])
    v['en_ar_key_mismatch'] += len(set(en) ^ set(ar))
    new_keys = [k for k in ar if k not in fx_en]
    info['new_keys'] = len(new_keys)
    info['ar_real'] = sum(1 for k in new_keys if ARABIC.search(str(ar[k])))
    info['ar_placeholder'] = len(new_keys) - info['ar_real']
    # ---------------- storage engine ----------------
    engine = TASKS[task]['engine']
    if engine == 'drift':
        for r, t in feat.items():
            v['drift_table_or_dao_in_feature'] += count(r'extends Table\b|@DriftAccessor', t)
        for r, t in new.items():
            if r.startswith('lib/core/database/tables/') and r.endswith('_table.dart'):
                names = re.findall(r"@DataClassName\('(\w+)'\)", t)
                if not names or not all(n.endswith('Entity') for n in names):
                    v['drift_row_class_not_XEntity'] += 1
        for r in [r for r in code if r.startswith('lib/core/database/tables/') and r.endswith('_dao.dart')]:
            added = code[r]
            for name, body in dao_methods(full[r]):
                if (r in new or re.search(r'\b%s\s*\(' % name, added)) and 'handleLocalFailure' not in body:
                    v['dao_method_without_handleLocalFailure'] += 1
        db = full.get('lib/core/database/app_database.dart', '')
        new_tables = [r for r in new if r.endswith('_table.dart')]
        sv = re.search(r'schemaVersion\s*=>\s*(\d+)', db)
        sv = int(sv.group(1)) if sv else 1
        info['schemaVersion'] = sv
        if new_tables or task == 'd4':
            if sv < 2 or 'onUpgrade' not in db:
                v['schema_not_bumped_with_migration'] += 1
            if task == 'd4' and 'addColumn' not in db:
                v['d4_no_addColumn'] += 1
            if new_tables and 'createTable' not in db:
                v['new_table_not_created_in_migration'] += 1
        for r, t in new.items():
            if role(r) == 'ds' and 'local' in r and 'AppDatabase' in t:
                v['local_ds_takes_database_not_dao'] += 1
    else:
        for r, t in dart.items():
            if not r.endswith('hive_boxes.dart'):
                v['hive_box_opened_outside_hive_boxes'] += count(r'openBox', t)
        for r, t in by_role['ds'].items():
            if 'local' not in r:
                continue
            lines = t.splitlines()
            for i, line in enumerate(lines):
                if re.search(r'[bB]ox\.(?:put|putAll|delete|deleteAll|clear|add|addAll)\(', line):
                    # the whole statement, up to its closing ';' (a multi-line putAll({...}) spans several lines)
                    j = i
                    while j < min(len(lines) - 1, i + 15) and not lines[j].rstrip().endswith(';'):
                        j += 1
                    window = ' '.join(lines[i:j + 1])
                    if 'handleLocalFailure' not in window:
                        v['hive_box_call_unguarded'] += 1
            if re.search(r'[bB]ox\.(?:values|get\(|keys)', t) and 'handleLocalFailureSync' not in t:
                v['hive_box_call_unguarded'] += 1
        for rl in ('repo', 'cubit', 'ui'):
            for r, t in by_role[rl].items():
                v['storage_type_above_data_source'] += count(r'Map<String,\s*dynamic>|\bBox\b', t)
    # ---------------- task patterns ----------------
    repos = ' '.join(t for r, t in new.items() if role(r) == 'repo')
    if task in ('d2', 'h1'):
        if 'isConnected' not in repos:
            v['hybrid_no_network_check'] += 1
        if not re.search(r'_\w*[lL]ocal\w*\.(?:cache|save|insert|replace|upsert|put|store)\w*\(', repos):
            v['hybrid_no_cache_on_success'] += 1
        if 'GlobalResponse(' not in repos:
            v['hybrid_offline_not_GlobalResponse'] += 1
    if task == 'd1':
        if re.search(r'NetworkStatus|GlobalResponse', repos):
            v['local_only_uses_network_or_GlobalResponse'] += 1
        if 'FutureResult' not in repos:
            v['local_only_not_FutureResult'] += 1
    if task in ('d3', 'h2'):
        if 'isConnected' not in repos:
            v['sync_no_network_check'] += 1
        if not re.search(r'serverId|remoteId|server_id', repos + ' '.join(t for r, t in new.items() if role(r) == 'ds')):
            v['sync_no_server_id'] += 1
        if not re.search(r'(?:serverId|remoteId|\bid)\s*(?:==|!=)\s*null|\?\?|case null|if \(\w+ (?:==|!=) null', repos):
            v['sync_no_null_server_id_guard'] += 1
    if task == 'd4':
        if 'nullable()' not in full.get('lib/core/database/tables/budgets/budgets_table.dart', ''):
            v['d4_column_not_nullable'] += 1
        if not re.search(r'String\?\s+description', full.get('lib/feature/budget/data/models/budget_model.dart', '')):
            v['d4_model_field_missing_or_non_nullable'] += 1
        if 'description' not in full.get('lib/feature/budget/data/data_source/local/budget_local_data_source.dart', '') \
                and 'description' not in full.get('lib/feature/budget/domain/params/add_budget_params.dart', ''):
            v['d4_description_not_written'] += 1
    new_task_checks(v, task, run_dir, new, touched, full, code, dart, ui, cubits, sl_add)
    return {k: n for k, n in v.items() if n}, info


def num(expr):
    """Value of a literal arithmetic expression like '34 / 28' or '-0.02 * 28.sp', else None."""
    expr = re.sub(r'\.(?:spMin|sp|h|w|r)\b', '', expr).strip()
    if not expr or not re.fullmatch(r'[-+*/(). \d]+', expr):
        return None
    try:
        return float(eval(expr, {'__builtins__': {}}))
    except Exception:
        return None


def type_scale_hits(text):
    """For each DESIGN_TYPE entry: (size and line height found, tracking found)."""
    chunks = [c for c in re.split(r';', text) if re.search(r'\d', c)]
    out = []
    for size, lh, tr in DESIGN_TYPE:
        scale = track = False
        for c in chunks:
            fields = {k: num(e) for k, e in re.findall(r'(fontSize|height|letterSpacing):\s*([^,)\n]+)', c)}
            nums = [float(x) for x in re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?', c)]
            has_size = fields.get('fontSize') == size or (fields.get('fontSize') is None and size in nums)
            if not has_size:
                continue
            h = fields.get('height')
            if (h is not None and abs(h - lh / size) < 0.01) or lh in nums or any(abs(n - lh / size) < 0.006 for n in nums):
                scale = True
                ls = fields.get('letterSpacing')
                if tr == 0 or (ls is not None and abs(ls - tr) < 0.02) or any(abs(n - tr) < 0.02 for n in nums if n) \
                        or any(abs(n * size - tr) < 0.02 for n in nums if n and abs(n) < 0.1):
                    track = True
        out.append((scale, track))
    return out


def new_task_checks(v, task, run_dir, new, touched, full, code, dart, ui, cubits, sl_add):
    ui_all = ' '.join(ui.values())
    if task in TRIP_SCREEN_TASKS:
        if not re.search(r'static\s+String\s+\w+\s*\(', touched.get('lib/core/api/api_request_helpers/end_points.dart', '')):
            v['endpoint_with_id_not_static_method'] += 1
        if 'registerFactoryParam' not in sl_add:
            v['route_arg_cubit_not_registerFactoryParam'] += 1
        if 'param1' not in touched.get('lib/core/app_routes/app_router.dart', ''):
            v['route_arg_not_passed_as_param1'] += 1
    if task == 'f1':
        if not re.search(r'showModalBottomSheet|showBottomSheet|showDialog', ui_all):
            v['f1_no_bottom_sheet'] += 1
        else:
            if 'BlocProvider.value' not in ui_all:
                v['sheet_not_wrapped_in_BlocProvider_value'] += 1
            sheets = [t for r, t in new.items() if role(r) == 'ui'
                      and re.search(r'class\s+\w*(?:Sheet|Dialog|Confirm)\w*\s+extends\s+StatelessWidget', t)]
            if not any(re.search(r'final\s+\w+Cubit\s+\w+\s*;', t) for t in sheets):
                v['sheet_not_given_cubit'] += 1
    if task == 'f2':
        for r, t in ui.items():
            v['controller_or_form_key_in_widget'] += count(r'TextEditingController\(|GlobalKey<FormState>', t)
        cub = ' '.join(cubits.values())
        if re.search(r'\.text\s*=[^=]|late\s+(?:final\s+)?TextEditingController', cub):
            v['controller_not_prefilled_in_initializer_list'] += 1
        if count(r'TextEditingController\(', cub) > count(r'\.dispose\(\)', cub):
            v['controller_not_disposed'] += 1
        if not any('/params/' in r for r in new):
            v['update_without_params_class'] += 1
        if not re.search(r'\.validate\(\)', ' '.join(t for r, t in dart.items() if role(r) in ('ui', 'cubit'))):
            v['form_not_validated'] += 1
    if task == 't1':
        tests = {r: t for r, t in new.items() if r.startswith('test/') and r.endswith('_test.dart')}
        mirrored = ['test/feature/trips/data/data_source/trips_remote_data_source_test.dart',
                    'test/feature/trips/data/repository/trips_repository_test.dart',
                    'test/feature/trips/presentation/trips_screen/logic/trips_cubit_test.dart']
        v['tests_not_mirroring_lib'] += sum(1 for m in mirrored if m not in tests)
        v['tests_use_mockito'] += sum(1 for t in tests.values() if re.search(r'package:mockito|@GenerateMocks', t))
        of = lambda kind: [t for r, t in tests.items() if kind in os.path.basename(r)]
        if of('cubit') and not any(re.search(r'\bblocTest\b', t) for t in of('cubit')):
            v['cubit_test_without_blocTest'] += 1
        v['mocktail_any_without_fallback'] += sum(1 for t in tests.values()
                                                  if re.search(r'getTrips\(\s*any\(\)', t) and 'registerFallbackValue' not in t)
        if of('repository') and not any(re.search(r'=>\s*false', t) and 'verifyNever' in t for t in of('repository')):
            v['repo_test_no_offline_branch'] += 1
        if of('data_source') and not any('queryParameters' in t for t in of('data_source')):
            v['ds_test_params_not_verified'] += 1
        dev = re.search(r'^dev_dependencies:\n(.*?)(?=^\S|\Z)', full.get('pubspec.yaml', ''), re.M | re.S)
        v['test_deps_missing'] += sum(1 for pkg in ('mocktail', 'bloc_test')
                                      if not (dev and re.search(r'^\s+%s:' % pkg, dev.group(1), re.M)))
    if task == 'g1':
        core = ' '.join(full[r] for r in code if r.startswith('lib/core/') and r.endswith('.dart'))
        hexes = {h.upper() for h in re.findall(r'0x([0-9A-Fa-f]{8})', core)}
        soft = '1F0F766E' in hexes or re.search(r'withValues\(alpha:\s*0?\.12\b|withOpacity\(0?\.12\b|withAlpha\(31\)', core)
        v['design_color_missing'] += sum(1 for c in DESIGN_COLORS if 'FF' + c not in hexes) + (0 if soft else 1)
        if 'FF3366FF' in hexes:
            v['design_decoy_color_used'] += 1
        if re.search(r'\bprimary\s*=\s*Color\(0xFF1E6FD9', full.get('lib/core/app_themes/colors/app_colors.dart', '')):
            v['design_old_primary_kept'] += 1
        fonts = []
        for d, _, fs in os.walk(run_dir):
            for f in fs:
                if f.lower().endswith(('.ttf', '.otf')):
                    with open(os.path.join(d, f), 'rb') as fh:
                        if fh.read(4) in (b'\x00\x01\x00\x00', b'OTTO', b'true'):
                            fonts.append(f)
        if len(fonts) < 2:
            v['design_font_not_extracted'] += 1
        pub = full.get('pubspec.yaml', '')
        if not re.search(r'family:\s*[\'"]?Nordvik Sans', pub) or not re.search(r'weight:\s*700', pub):
            v['design_font_not_declared'] += 1
        if 'fontFamily' not in core:
            v['design_font_family_not_applied'] += 1
        styles = ' ;'.join(full[r] for r in code if r.startswith('lib/core/app_themes/') and r.endswith('.dart'))
        hits = type_scale_hits(styles)
        v['design_type_scale_wrong'] += sum(1 for scale, _ in hits if not scale)
        v['design_tracking_wrong'] += sum(1 for scale, track in hits if scale and not track)
        legacy = full.get('lib/core/app_themes/text_style/app_text_style.dart', '')
        v['design_legacy_text_getters_removed'] += sum(1 for g in LEGACY_TEXT_GETTERS if not re.search(r'\b%s\b' % g, legacy))
        durs = {int(x) for x in re.findall(r'Duration\(\s*milliseconds:\s*(\d+)', core)}
        curves = [tuple(float(x) for x in m) for m in
                  re.findall(r'Cubic\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,?\s*\)', core)]
        v['design_motion_missing'] += sum(1 for d in DESIGN_DURATIONS if d not in durs) + sum(
            1 for c in DESIGN_CURVES if not any(all(abs(a - b) < 1e-6 for a, b in zip(c, k)) for k in curves))
        for f, size in (('primary_button', 52), ('app_text_field', 48)):
            rel = f'lib/core/widgets/{f}.dart'
            if rel not in touched:
                v['design_widget_not_restyled'] += 1
            elif not re.search(r'(?<![\d.])%d(?:\.0)?\b' % size, full[rel] + core):
                v['design_widget_size_wrong'] += 1
        for r in code:
            if r.startswith('lib/core/widgets/') and r.endswith('.dart'):
                v['design_raw_value_in_widget'] += count(
                    r'Color\(0x|\bColors\.(?!transparent)|Duration\(|Cubic\(|\bCurves\.|(?<![\w.])TextStyle\(', code[r])


def main():
    results = {}
    for name in sorted(os.listdir(RUNS)):
        if not os.path.exists(os.path.join(RUNS, name, 'SKILLS_READ.txt')):
            continue  # run not finished
        version, mode, task, rep = name.split('-')
        t = TASKS[task]
        fixture = os.path.join(B, 'fixture-' + t.get('fixture', t['engine']) + ('-nowrap' if mode == 'nowrap' else ''))
        v, info = grade(os.path.join(RUNS, name), fixture, task)
        sr = read(os.path.join(RUNS, name, 'SKILLS_READ.txt'))
        if task in TASK_SKILL and f'skills/{TASK_SKILL[task]}/SKILL.md' not in sr:
            v['task_skill_not_read'] = 1
        if task == 'g1' and 'design-from-html-flutter/playbook.md' not in sr:
            v['design_playbook_not_read'] = 1
        info['skills_read'] = len(set(re.findall(r'skills/([\w-]+)/', sr)))
        info['tokens'] = TOKENS.get(name)
        results[name] = {'version': version, 'mode': mode, 'task': task, 'rep': rep, 'violations': v, 'info': info}
    json.dump(results, open(os.path.join(B, 'grades.json'), 'w'), indent=1, ensure_ascii=False)

    # ---------- tables ----------
    rules = sorted({k for r in results.values() for k in r['violations']})
    groups = defaultdict(list)
    for n, r in results.items():
        groups[(r['mode'], r['version'])].append(r)
    print('## Summary per version and mode\n')
    print('| mode | version | runs | mean rules broken / run | total hits | runs with real Arabic | runs with placeholder Arabic | mean skills read | mean tokens |')
    print('|---|---|---|---|---|---|---|---|---|')
    for (mode, ver), rs in sorted(groups.items()):
        n = len(rs)
        rb = sum(len(r['violations']) for r in rs) / n
        hits = sum(sum(r['violations'].values()) for r in rs)
        real = sum(1 for r in rs if r['info']['ar_real'])
        ph = sum(1 for r in rs if r['info']['ar_placeholder'])
        sk = sum(r['info']['skills_read'] for r in rs) / n
        toks = [r['info']['tokens'] for r in rs if r['info']['tokens']]
        tk = f"{sum(toks) / len(toks) / 1000:.1f}k" if toks else '-'
        print(f'| {mode} | {ver} | {n} | {rb:.2f} | {hits} | {real} | {ph} | {sk:.1f} | {tk} |')
    print('\n## Runs breaking each rule (out of runs in that cell)\n')
    cells = sorted(groups)
    print('| rule | ' + ' | '.join(f'{m} {v}' for m, v in cells) + ' |')
    print('|---|' + '---|' * len(cells))
    for rule in rules:
        row = [str(sum(1 for r in groups[c] if rule in r['violations'])) + f'/{len(groups[c])}' for c in cells]
        print(f'| {rule} | ' + ' | '.join(row) + ' |')
    print('\n## Per task: rules broken per run (reps listed)\n')
    tasks = sorted({r['task'] for r in results.values()})
    print('| task | ' + ' | '.join(f'{m} {v}' for m, v in cells) + ' |')
    print('|---|' + '---|' * len(cells))
    for t in tasks:
        row = []
        for c in cells:
            vals = [str(len(r['violations'])) for r in sorted(groups[c], key=lambda r: r['rep']) if r['task'] == t]
            row.append(', '.join(vals) or '-')
        print(f'| {t} | ' + ' | '.join(row) + ' |')


if __name__ == '__main__':
    main()
