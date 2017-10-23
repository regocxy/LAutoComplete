import sublime
import sublime_plugin

import glob
import json
import codecs
import threading
import os
from os import path

from . import ProgressBar

class Node:
    (
        TYPE_NONE,
        TYPE_SEP,
        TYPE_WORD,
        TYPE_STR,
        TYPE_FUNCTION,
        TYPE_FUNCTION_NAME,
        TYPE_COMMIT
    ) = range(0, 7)

    def __init__(self, name='', type=TYPE_NONE):
        self.name = name
        self.type = type
        self.parent = None
        self.child = None

    def behind(self, node):
        if self.child:
            self.child.parent = node
        node.child = self.child
        node.parent = self
        self.child = node

    def front(self, node):
        if self.parent:
            self.parent.child = node
        node.parent = self.parent
        node.child = self
        self.parent = node


class Link:

    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def append(self, node):
        if not self.tail:
            self.head = self.tail = node
        else:
            self.tail.behind(node)
            self.tail = node
        self.size += 1

    def remove(self, node):
        pass


class Parser:

    CHAR_ENTER = '\n'
    Seps = ['.', '~', '>', '<', '=', '+', '-', '*', '/', '%', ':', ',', ' ', '\t', CHAR_ENTER, '\'', '"', '{', '}', '(', ')', '[', ']']

    def __init__(self):
        self.link = Link()
        self.link2 = Link()
        self.tab_size = 4

    def do_link(self, ctx):
        cache = ''
        for c in ctx:
            if c in Parser.Seps:
                if cache:
                    self.link.append(Node(cache, Node.TYPE_WORD))
                    cache = ''
                self.link.append(Node(c, Node.TYPE_SEP))
            else:
                cache += c
        if cache:
            self.link.append(Node(cache, Node.TYPE_WORD))
        node = self.link.head
        while node:
            if node.name == '[' and node.child and node.child.name == '[':
                cache = '[['
                node = node.child.child
                if node:
                    while node and not (node.name == ']' and node.child.name == ']'):
                        cache += node.name
                        node = node.child
                    cache += ']]'
                    node = node.child
                self.link2.append(Node(cache, Node.TYPE_STR))
            # elif node.name == '[' and node.child.name == '=':
            #     n = 1
            #     while node and node.name == '=':
            #         n += 1
            #         node = node.child
            #     if node.name == '[':
            #         while node and not (node.name == ']' and node.child.name == '='):
            #             cache += node.name
            #             node = node.child
            elif node.name == '\'':
                cache = '\''
                node = node.child
                if node:
                    while node and node.name != '\'':
                        cache += node.name
                        node = node.child
                    cache += '\''
                self.link2.append(Node(cache, Node.TYPE_STR))
            elif node.name == '"':
                cache = '"'
                node = node.child
                if node:
                    while node and node.name != '"':
                        cache += node.name
                        node = node.child
                    cache += '"'
                self.link2.append(Node(cache, Node.TYPE_STR))
            elif node.name == '-' and node.child and node.child.name == '-':
                cache = '--'
                node = node.child.child
                if node:
                    if node.name == '[' and node.child and node.child.name == '[':
                        cache += '[['
                        node = node.child.child
                        if node:
                            while node and not (node.name == ']' and node.child.name == ']'):
                                cache += node.name
                                node = node.child
                            cache += ']]'
                            node = node.child
                        self.link2.append(Node(cache, Node.TYPE_COMMIT))
                    else:
                        while node and node.name != Parser.CHAR_ENTER:
                            cache += node.name
                            node = node.child
                        self.link2.append(Node(cache, Node.TYPE_COMMIT))
            else:
                ignore = [' ', '\t']
                if node.name not in ignore:
                    if node.name == 'function':
                        self.link2.append(Node(node.name, Node.TYPE_FUNCTION))
                    else:
                        self.link2.append(Node(node.name, Node.TYPE_WORD))
            if node:
                node = node.child

    def do_parse(self, ctx):
        self.do_link(ctx)
        node = self.link2.head
        result = {}
        while node:
            if node.type == Node.TYPE_FUNCTION:
                func_name = ''
                base_func_name = ''
                if node.parent and node.parent.name == 'local':
                    pass
                elif node.parent and node.parent.name == '=':
                    parent = node.parent.parent
                    if parent and parent.parent and parent.parent.name == '.' and parent.parent.parent and (not parent.parent.parent.parent or parent.parent.parent.parent.name == Parser.CHAR_ENTER):
                        base_func_name = parent.name
                        func_name += parent.parent.parent.name + parent.parent.name + base_func_name
                        node = node.child
                        if node.name != '(':
                            continue
                    elif parent and (not parent.parent or parent.parent.name == Parser.CHAR_ENTER):
                        func_name += parent.name
                        node = node.child
                        if node.name != '(':
                            continue
                    else:
                        pass
                else:
                    if node.child and node.child.child and node.child.child.child and node.child.child.child.child and node.child.child.child.child.name == '(':
                        base_func_name = node.child.child.child.name
                        func_name += node.child.name + node.child.child.name + base_func_name
                        node = node.child.child.child.child.child
                    elif node.child and node.child.child and node.child.child.name == '(':
                        base_func_name = node.child.name
                        func_name += base_func_name
                        node = node.child.child.child
                    else:
                        pass
                if func_name:
                    params = '('
                    func_name += '('
                    sz = 0
                    while node:
                        if node.name == ')':
                            params += ')'
                            func_name += ')'
                            break
                        if node.child:
                            if node.child.name == ',':
                                sz += 1
                                func_name += node.name + ', '
                                params += '${' + str(sz) + ':' + node.name + '}' + ', '
                                node = node.child
                            elif node.child.name == ')':
                                sz += 1
                                func_name += node.name + ')'
                                params += '${' + str(sz) + ':' + node.name + '}' + ')'
                                break
                            else:
                                break
                        else:
                            break
                        node = node.child
                    if params == '(':
                        func_name += '...)'
                        params += '${1:...})'
                    result[func_name] = base_func_name + params
            if node:
                node = node.child
        return result

_dir_ = path.dirname(path.realpath(__file__))


class LAutoManager:

    FILE_NAME = 'LAutoComplete.sublime-completions'

    def __init__(self):
        self.completions = {}
        self.filepath = path.join(_dir_, LAutoManager.FILE_NAME)
        self.lock = threading.Lock()
        self.progress_bar = ProgressBar.ProgressBar()

    def write_rule(self, project):
        if type(self.completions.get(project)) is dict:
            completions = []
            def _add(completion):
                delete_items = []
                for (file_name, ctx) in completion.items():
                    if path.isfile(file_name):                      
                        for (trigger, contents) in ctx.items():
                            completions.append({'contents': contents, 'trigger': trigger})
                    else:
                        delete_items.append(file_name)
                for item in delete_items:
                    completion.pop(item)
            _add(self.completions[project])
            if project and self.completions.get(project+'0'):
                _add(self.completions[project+'0'])
            tbl = {
                'scope': 'source.lua',
                'completions': completions
            }
            stream = json.dumps(tbl)
            with codecs.open(self.filepath, 'w', 'utf-8') as f:
                f.write(stream)

    def init_data(self, project, project_path):
        if project and project_path and not self.completions.get(project):
            filepath = path.join(project_path, '.lauto')
            if path.isfile(filepath):
                with codecs.open(filepath, 'r', 'utf-8') as f:
                    try:
                        self.completions[project] = json.loads(f.read())
                    except Exception as e:
                       return False
                return True
        return False    

    def save_data(self, project, project_path):
        if project and project_path and self.completions.get(project):
            stream = json.dumps(self.completions[project])
            with codecs.open(path.join(project_path, '.lauto'), 'w', 'utf-8') as f:
                f.write(stream)

    def is_valid_file(self, file_name):
        if file_name and file_name.endswith('.lua'):
            return True
        return False

    def is_added_file(self, project, file_name):
        if self.completions.get(project):
            if self.completions[project].get(file_name):
                return True
        return False

    def set_data(self, project, file_name, ctx):
        if not ctx or ctx.find('function') == -1:
            return False
        if not self.completions.get(project):
            self.completions[project] = {}
        self.completions[project][file_name] = {}
        completions = self.completions[project][file_name]
        parser = Parser()
        result = parser.do_parse(ctx)
        for (trigger, contents) in result.items():
            completions[trigger] = contents
        return True

    def add_folder(self, project, dirs):
        with self.lock:
            self.progress_bar.start(sublime.status_message)
            for d in dirs:
                for (dirname, subdir, subfile) in os.walk(d):
                    for file_name in subfile:
                        if self.is_valid_file(file_name):
                            file_name = path.join(dirname, file_name)
                            with codecs.open(file_name, 'r', 'utf-8') as f:
                                self.set_data(project, file_name, f.read())
            self.write_rule(project)
            self.progress_bar.stop()
            sublime.status_message("Success to add_folder")

    def remove_folder(self, project, dirs):
        with self.lock:
            self.progress_bar.start(sublime.status_message)
            for d in dirs:
                for (dirname, subdir, subfile) in os.walk(d):
                    for file_name in subfile:
                        if self.is_valid_file(file_name) and self.completions.get(project):
                            file_name = path.join(dirname, file_name)
                            if self.completions[project].get(file_name):
                                self.completions[project].pop(file_name)
            self.write_rule(project)
            self.progress_bar.stop()
            sublime.status_message("Success to remove_folder")

lauto = LAutoManager()


class LSublimeListener(sublime_plugin.EventListener):

    def __init__(self):
        self.pending = 0
        self.project = -1

    def on_hover(self, view, point, hover_zone):
        pass

    def get_project_info(self):
        window = sublime.active_window()
        info = window.extract_variables()
        project = info.get('project', 0)
        project_path = info.get('project_path')
        return (project, project_path)

    def on_close(self, view):
        file_name = view.file_name()
        if lauto.is_valid_file(view.file_name()):
            (project, project_path) = self.get_project_info()
            lauto.save_data(project, project_path)

    def on_activated_async(self, view):
        file_name = view.file_name()
        if lauto.is_valid_file(view.file_name()):
            (project, project_path) = self.get_project_info()
            if lauto.init_data(project, project_path):
                lauto.write_rule(project)
            else:
                if self.project != project:
                    lauto.write_rule(project)
                    self.project = project

    def on_pre_save_async(self, view):
        file_name = view.file_name()
        if lauto.is_valid_file(file_name): 
            if self.pending > 0:
                return
            self.pending += 1
            ctx = view.substr(sublime.Region(0, view.size()))
            (project, project_path) = self.get_project_info()
            ret = False
            if project and not lauto.is_added_file(project, file_name):
                ret = lauto.set_data(project+'0', file_name, ctx)
            else:
                ret = lauto.set_data(project, file_name, ctx)
            if ret:
                lauto.write_rule(project)
            self.pending -= 1


class LAutoAddFolderCommand(sublime_plugin.WindowCommand):

    def run(self, dirs):
        info = self.window.extract_variables()
        project = info.get('project', 0)
        sublime.set_timeout_async(lambda: lauto.add_folder(project, dirs), 0)

    def is_visible(self, dirs):
        return len(dirs) > 0

class LAutoRemoveFolderCommand(sublime_plugin.WindowCommand):

    def run(self, dirs):
        info = self.window.extract_variables()
        project = info.get('project', 0)
        sublime.set_timeout_async(lambda: lauto.remove_folder(project, dirs), 0)

    def is_visible(self, dirs):
        return len(dirs) > 0

