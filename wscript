#!/usr/bin/env python

import os
import sys

from waflib import Context, Logs, Options, Scripting, Utils
from waflib.extras import autowaf as autowaf

# Mandatory waf variables
APPNAME = 'lv2'     # Package name for waf dist
VERSION = '1.16.2'  # Package version for waf dist
top     = '.'       # Source directory
out     = 'build'   # Build directory

# Map of specification base name to old URI-style include path
spec_map = {
    'atom'            : 'lv2/lv2plug.in/ns/ext/atom',
    'buf-size'        : 'lv2/lv2plug.in/ns/ext/buf-size',
    'core'            : 'lv2/lv2plug.in/ns/lv2core',
    'data-access'     : 'lv2/lv2plug.in/ns/ext/data-access',
    'dynmanifest'     : 'lv2/lv2plug.in/ns/ext/dynmanifest',
    'event'           : 'lv2/lv2plug.in/ns/ext/event',
    'instance-access' : 'lv2/lv2plug.in/ns/ext/instance-access',
    'log'             : 'lv2/lv2plug.in/ns/ext/log',
    'midi'            : 'lv2/lv2plug.in/ns/ext/midi',
    'morph'           : 'lv2/lv2plug.in/ns/ext/morph',
    'options'         : 'lv2/lv2plug.in/ns/ext/options',
    'parameters'      : 'lv2/lv2plug.in/ns/ext/parameters',
    'patch'           : 'lv2/lv2plug.in/ns/ext/patch',
    'port-groups'     : 'lv2/lv2plug.in/ns/ext/port-groups',
    'port-props'      : 'lv2/lv2plug.in/ns/ext/port-props',
    'presets'         : 'lv2/lv2plug.in/ns/ext/presets',
    'resize-port'     : 'lv2/lv2plug.in/ns/ext/resize-port',
    'state'           : 'lv2/lv2plug.in/ns/ext/state',
    'time'            : 'lv2/lv2plug.in/ns/ext/time',
    'ui'              : 'lv2/lv2plug.in/ns/extensions/ui',
    'units'           : 'lv2/lv2plug.in/ns/extensions/units',
    'uri-map'         : 'lv2/lv2plug.in/ns/ext/uri-map',
    'urid'            : 'lv2/lv2plug.in/ns/ext/urid',
    'worker'          : 'lv2/lv2plug.in/ns/ext/worker'}

def options(ctx):
    ctx.load('compiler_c')
    ctx.load('lv2')
    ctx.add_flags(
        ctx.configuration_options(),
        {'no-coverage':    'Do not use gcov for code coverage',
         'online-docs':    'Build documentation for web hosting',
         'no-check-links': 'Do not check documentation for broken links',
         'no-plugins':     'Do not build example plugins',
         'copy-headers':   'Copy headers instead of linking to bundle'})

def configure(conf):
    try:
        conf.load('compiler_c', cache=True)
    except:
        Options.options.build_tests = False
        Options.options.no_plugins = True

    if Options.options.online_docs:
        Options.options.docs = True

    conf.load('lv2', cache=True)
    conf.load('autowaf', cache=True)
    autowaf.set_c_lang(conf, 'c99')

    if Options.options.ultra_strict and not conf.env.MSVC_COMPILER:
        conf.env.append_value('CFLAGS', ['-Wconversion'])

    if conf.env.DEST_OS == 'win32' or not hasattr(os.path, 'relpath'):
        Logs.warn('System does not support linking headers, copying')
        Options.options.copy_headers = True

    conf.env.BUILD_TESTS   = Options.options.build_tests
    conf.env.BUILD_PLUGINS = not Options.options.no_plugins
    conf.env.COPY_HEADERS  = Options.options.copy_headers
    conf.env.ONLINE_DOCS   = Options.options.online_docs

    if conf.env.DOCS or conf.env.ONLINE_DOCS:
        try:
            conf.find_program('asciidoc')
            conf.env.BUILD_BOOK = True
        except:
            Logs.warn('Asciidoc not found, book will not be built')

        if not Options.options.no_check_links:
            if not conf.find_program('linkchecker',
                                     var='LINKCHECKER', mandatory=False):
                Logs.warn('Documentation will not be checked for broken links')

    # Check for gcov library (for test coverage)
    if (conf.env.BUILD_TESTS
        and not Options.options.no_coverage
        and not conf.is_defined('HAVE_GCOV')):
        conf.check_cc(lib='gcov', define_name='HAVE_GCOV', mandatory=False)

    autowaf.set_lib_env(conf, 'lv2', VERSION, has_objects=False)
    autowaf.set_local_lib(conf, 'lv2', has_objects=False)

    conf.run_env.append_unique('LV2_PATH',
                               [os.path.join(conf.path.abspath(), 'lv2')])

    if conf.env.BUILD_PLUGINS:
        for i in ['eg-amp.lv2',
                  'eg-fifths.lv2',
                  'eg-metro.lv2',
                  'eg-midigate.lv2',
                  'eg-params.lv2',
                  'eg-sampler.lv2',
                  'eg-scope.lv2']:
            try:
                path = os.path.join('plugins', i)
                conf.recurse(path)
                conf.env.LV2_BUILD += [path]
                conf.run_env.append_unique(
                    'LV2_PATH', [conf.build_path('plugins/%s/lv2' % i)])
            except Exception as e:
                Logs.warn('Configuration failed, not building %s (%s)' % (i, e))

    autowaf.display_summary(
        conf,
        {'Bundle directory': conf.env.LV2DIR,
         'Copy (not link) headers': bool(conf.env.COPY_HEADERS),
         'Version': VERSION})

def chop_lv2_prefix(s):
    if s.startswith('lv2/lv2plug.in/'):
        return s[len('lv2/lv2plug.in/'):]
    return s

def subst_file(template, output, dict):
    i = open(template, 'r')
    o = open(output, 'w')
    for line in i:
        for key in dict:
            line = line.replace(key, dict[key])
        o.write(line)
    i.close()
    o.close()

def specdirs(path):
    return (path.ant_glob('lv2/*', dir=True) +
            path.ant_glob('plugins/*.lv2', dir=True))

def ttl_files(path, specdir):
    def abspath(node):
        return node.abspath()

    return map(abspath,
               path.ant_glob(specdir.path_from(path) + '/*.ttl'))

def load_ttl(files, exclude = []):
    import rdflib
    model = rdflib.ConjunctiveGraph()
    for f in files:
        if f not in exclude:
            model.parse(f, format='n3')
    return model

# Task to build extension index
def build_index(task):
    src_dir = task.inputs[0].parent.parent
    sys.path.append(str(src_dir.find_node('lv2specgen')))
    import rdflib
    import lv2specgen

    doap = rdflib.Namespace('http://usefulinc.com/ns/doap#')
    lv2  = rdflib.Namespace('http://lv2plug.in/ns/lv2core#')
    rdf  = rdflib.Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')

    model = load_ttl([str(src_dir.find_node('lv2/core/meta.ttl'))])

    # Get date for this version, and list of all LV2 distributions
    proj  = rdflib.URIRef('http://lv2plug.in/ns/lv2')
    date  = None
    dists = []
    for r in model.triples([proj, doap.release, None]):
        revision = model.value(r[2], doap.revision, None)
        created  = model.value(r[2], doap.created, None)
        if str(revision) == VERSION:
            date = created

        dist = model.value(r[2], doap['file-release'], None)
        if dist and created:
            dists += [(created, dist)]
        else:
            print('warning: %s has no file release\n' % proj)

    # Get history for this LV2 release
    entries = lv2specgen.specHistoryEntries(model, proj, {})

    # Add entries for every spec that has the same distribution
    ctx     = task.generator.bld
    subdirs = specdirs(ctx.path)
    for specdir in subdirs:
        files   = ttl_files(ctx.path, specdir)
        exclude = [os.path.join(str(ctx.path), 'lv2/core/meta.ttl')]
        m       = load_ttl(files, exclude)
        name    = os.path.basename(specdir.abspath())
        spec    = m.value(None, rdf.type, lv2.Specification)
        if spec:
            for dist in dists:
                release = m.value(None, doap['file-release'], dist[1])
                if release:
                    entries[dist] += lv2specgen.releaseChangeset(
                        m, release, str(name))

    rows = []
    for f in task.inputs:
        if not f.abspath().endswith('index.html.in'):
            rowfile = open(f.abspath(), 'r')
            rows += rowfile.readlines()
            rowfile.close()

    if date is None:
        import datetime
        import time
        now = int(os.environ.get('SOURCE_DATE_EPOCH', time.time()))
        date = datetime.datetime.utcfromtimestamp(now).strftime('%F')

    subst_file(task.inputs[0].abspath(), task.outputs[0].abspath(),
               {'@ROWS@': ''.join(rows),
                '@LV2_VERSION@': VERSION,
                '@DATE@': date})

def build_spec(bld, path):
    name            = os.path.basename(path)
    bundle_dir      = os.path.join(bld.env.LV2DIR, name + '.lv2')
    include_dir     = os.path.join(bld.env.INCLUDEDIR, path)
    old_include_dir = os.path.join(bld.env.INCLUDEDIR, spec_map[name])

    # Build test program if applicable
    for test in bld.path.ant_glob(os.path.join(path, '*-test.c')):
        test_lib       = []
        test_cflags    = ['']
        test_linkflags = ['']
        if bld.is_defined('HAVE_GCOV'):
            test_lib       += ['gcov']
            test_cflags    += ['--coverage']
            test_linkflags += ['--coverage']
            if bld.env.DEST_OS not in ['darwin', 'win32']:
                test_lib += ['rt']

        # Unit test program
        bld(features     = 'c cprogram',
            source       = test,
            lib          = test_lib,
            uselib       = 'LV2',
            target       = os.path.splitext(str(test.get_bld()))[0],
            install_path = None,
            cflags       = test_cflags,
            linkflags    = test_linkflags)

    # Install bundle
    bld.install_files(bundle_dir,
                      bld.path.ant_glob(path + '/?*.*', excl='*.in'))

    # Install URI-like includes
    headers = bld.path.ant_glob(path + '/*.h')
    if headers:
        for d in [include_dir, old_include_dir]:
            if bld.env.COPY_HEADERS:
                bld.install_files(d, headers)
            else:
                bld.symlink_as(d,
                               os.path.relpath(bundle_dir, os.path.dirname(d)))

def build(bld):
    specs = (bld.path.ant_glob('lv2/*', dir=True))

    # Copy lv2.h to include directory for backwards compatibility
    old_lv2_h_path = os.path.join(bld.env.INCLUDEDIR, 'lv2.h')
    if bld.env.COPY_HEADERS:
        bld.install_files(os.path.dirname(old_lv2_h_path), 'lv2/core/lv2.h')
    else:
        bld.symlink_as(old_lv2_h_path, 'lv2/core/lv2.h')

    # LV2 pkgconfig file
    bld(features     = 'subst',
        source       = 'lv2.pc.in',
        target       = 'lv2.pc',
        install_path = '${LIBDIR}/pkgconfig',
        PREFIX       = bld.env.PREFIX,
        INCLUDEDIR   = bld.env.INCLUDEDIR,
        VERSION      = VERSION)

    # Validator
    bld(features     = 'subst',
        source       = 'util/lv2_validate.in',
        target       = 'lv2_validate',
        chmod        = Utils.O755,
        install_path = '${BINDIR}',
        LV2DIR       = bld.env.LV2DIR)

    # Build extensions
    for spec in specs:
        build_spec(bld, spec.path_from(bld.path))

    # Build plugins
    for plugin in bld.env.LV2_BUILD:
        bld.recurse(plugin)

    # Install lv2specgen
    bld.install_files('${DATADIR}/lv2specgen/',
                      ['lv2specgen/style.css',
                       'lv2specgen/template.html'])
    bld.install_files('${DATADIR}/lv2specgen/DTD/',
                      bld.path.ant_glob('lv2specgen/DTD/*'))
    bld.install_files('${BINDIR}', 'lv2specgen/lv2specgen.py',
                      chmod=Utils.O755)

    # Install schema bundle
    bld.install_files('${LV2DIR}/schemas.lv2/',
                      bld.path.ant_glob('schemas.lv2/*.ttl'))

    if bld.env.ONLINE_DOCS:
        # Generate .htaccess files
        for d in ('ns', 'ns/ext', 'ns/extensions'):
            path = os.path.join(str(bld.path.get_bld()), d)
            bld(features     = 'subst',
                source       = 'doc/htaccess.in',
                target       = os.path.join(path, '.htaccess'),
                install_path = None,
                BASE         = '/' + d)

    if bld.env.DOCS or bld.env.ONLINE_DOCS:
        # Copy spec files to build dir
        for spec in specs:
            srcpath   = spec.srcpath()
            basename  = os.path.basename(srcpath)
            full_path = spec_map[basename]
            name      = 'lv2core' if basename == 'core' else basename
            path      = chop_lv2_prefix(full_path)
            spec_path = os.path.join(path[3:], name + '.ttl')

            bld(features = 'subst',
                is_copy  = True,
                source   = os.path.join(spec.srcpath(), name + '.ttl'),
                target   = path + '.ttl')

        # Copy stylesheets to build directory
        for i in ['style.css', 'pygments.css']:
            bld(features = 'subst',
                is_copy  = True,
                name     = 'copy',
                source   = 'doc/%s' % i,
                target   = 'aux/%s' % i)

        # Build Doxygen documentation (and tags file)
        autowaf.build_dox(bld, 'LV2', VERSION, top, out, 'doc', False)
        bld.add_group()

        index_files = []
        for spec in specs:
            # Call lv2specgen to generate spec docs
            srcpath      = spec.path_from(bld.path)
            basename     = os.path.basename(srcpath)
            full_path    = spec_map[basename]
            name         = 'lv2core' if basename == 'core' else basename
            ttl_name     = name + '.ttl'
            index_file   = bld.path.get_bld().make_node('index_rows/' + name)
            index_files += [index_file.path_from(bld.path)]
            chopped_path = chop_lv2_prefix(full_path)

            assert chopped_path.startswith('ns/')
            root_path    = os.path.relpath('/', os.path.dirname(chopped_path[2:]))
            html_path    = '%s.html' % chopped_path
            out_dir      = os.path.dirname(html_path)

            cmd = (str(bld.path.find_node('lv2specgen/lv2specgen.py')) +
                   ' --root-uri=http://lv2plug.in/ns/ --root-path=' + root_path +
                   ' --list-email=devel@lists.lv2plug.in'
                   ' --list-page=http://lists.lv2plug.in/listinfo.cgi/devel-lv2plug.in'
                   ' --style-uri=' + os.path.relpath('aux/style.css', out_dir) +
                   ' --docdir=' + os.path.relpath('doc/html', out_dir) +
                   ' --tags=%s' % bld.path.get_bld().make_node('doc/tags') +
                   ' --index=' + str(index_file) +
                   ' ${SRC} ${TGT}')

            bld(rule   = cmd,
                source = os.path.join(srcpath, ttl_name),
                target = [html_path, index_file],
                shell  = False)

            # Install documentation
            base = chop_lv2_prefix(srcpath)
            bld.install_files(os.path.join('${DOCDIR}', 'lv2', os.path.dirname(html_path)),
                              html_path)

        index_files.sort()
        bld.add_group()

        # Build extension index
        bld(rule   = build_index,
            name   = 'index',
            source = ['doc/index.html.in'] + index_files,
            target = 'ns/index.html')

        # Install main documentation files
        bld.install_files('${DOCDIR}/lv2/aux/', 'aux/style.css')
        bld.install_files('${DOCDIR}/lv2/ns/', 'ns/index.html')

        def check_links(ctx):
            import subprocess
            if ctx.env.LINKCHECKER:
                if subprocess.call([ctx.env.LINKCHECKER[0], '--no-status', out]):
                    ctx.fatal('Documentation contains broken links')

        if bld.cmd == 'build':
            bld.add_post_fun(check_links)

    if bld.env.BUILD_TESTS:
        # Generate a compile test .c file that includes all headers
        def gen_build_test(task):
            out = open(task.outputs[0].abspath(), 'w')
            for i in task.inputs:
                out.write('#include "%s"\n' % i.bldpath())
            out.write('int main(void) { return 0; }\n')
            out.close()

        bld(rule         = gen_build_test,
            source       = bld.path.ant_glob('lv2/**/*.h'),
            target       = 'build-test.c',
            install_path = None)

        bld(features     = 'c cprogram',
            source       = bld.path.get_bld().make_node('build-test.c'),
            target       = 'build-test',
            includes     = '.',
            uselib       = 'LV2',
            install_path = None)

    if bld.env.BUILD_BOOK:
        # Build "Programming LV2 Plugins" book from plugin examples
        bld.recurse('plugins')

def lint(ctx):
    "checks code for style issues"
    import subprocess

    subprocess.call("flake8 --ignore E203,E221,W503,W504,E302,E305,E251,E241,E722 "
                    "wscript lv2specgen/lv2docgen.py lv2specgen/lv2specgen.py "
                    "plugins/literasc.py",
                    shell=True)

    cmd = ("clang-tidy -p=. -header-filter=.* -checks=\"*," +
           "-hicpp-signed-bitwise," +
           "-llvm-header-guard," +
           "-misc-unused-parameters," +
           "-readability-else-after-return\" " +
           "build-test.c")
    subprocess.call(cmd, cwd='build', shell=True)

def test(tst):
    with tst.group('Unit') as check:
        pattern = tst.env.cprogram_PATTERN % '**/*-test'
        for test in tst.path.get_bld().ant_glob(pattern):
            check([str(test)])

class Dist(Scripting.Dist):
    def execute(self):
        'Execute but do not call archive() since dist() has already done so.'
        self.recurse([os.path.dirname(Context.g_module.root_path)])

    def get_tar_path(self, node):
        'Resolve symbolic links to avoid broken links in tarball.'
        return os.path.realpath(node.abspath())

class DistCheck(Dist, Scripting.DistCheck):
    def execute(self):
        Dist.execute(self)
        self.check()

    def archive(self):
        Dist.archive(self)

def posts(ctx):
    "generates news posts in Pelican Markdown format"
    subdirs = specdirs(ctx.path)
    dev_dist = 'http://lv2plug.in/spec/lv2-%s.tar.bz2' % VERSION

    try:
        os.mkdir(os.path.join(out, 'posts'))
    except:
        pass

    # Get all entries (as in dist())
    top_entries = {}
    for specdir in subdirs:
        entries = autowaf.get_rdf_news(os.path.basename(specdir.abspath()),
                                       ttl_files(ctx.path, specdir),
                                       top_entries,
                                       dev_dist = dev_dist)

    entries = autowaf.get_rdf_news('lv2',
                                   ['lv2/core/meta.ttl'],
                                   None,
                                   top_entries,
                                   dev_dist = dev_dist)

    autowaf.write_posts(entries,
                        {'Author': 'drobilla'},
                        os.path.join(out, 'posts'))

def dist(ctx):
    subdirs  = specdirs(ctx.path)
    dev_dist = 'http://lv2plug.in/spec/lv2-%s.tar.bz2' % VERSION

    # Write NEWS files in source directory
    top_entries = {}
    for specdir in subdirs:
        entries = autowaf.get_rdf_news(os.path.basename(specdir.abspath()),
                                       ttl_files(ctx.path, specdir),
                                       top_entries,
                                       dev_dist = dev_dist)
        autowaf.write_news(entries, specdir.abspath() + '/NEWS')

    # Write top level amalgamated NEWS file
    entries = autowaf.get_rdf_news('lv2',
                                   ['lv2/core/meta.ttl'],
                                   None,
                                   top_entries,
                                   dev_dist = dev_dist)
    autowaf.write_news(entries, 'NEWS')

    # Build archive
    ctx.archive()

    # Delete generated NEWS files from source directory
    for i in subdirs + [ctx.path]:
        try:
            os.remove(os.path.join(i.abspath(), 'NEWS'))
        except:
            pass
