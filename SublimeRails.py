import os
import os.path
import sublime
import sublime_plugin
import subprocess
import pipes
import re
import sys
import fnmatch
import threading


# Taken completely from Package Control
class ThreadProgress():
    """
    Animates an indicator, [=   ], in the status area while a thread runs

    :param thread:
        The thread to track for activity

    :param message:
        The message to display next to the activity indicator

    :param success_message:
        The message to display once the thread is complete
    """

    def __init__(self, thread, message, success_message):
        self.thread = thread
        self.message = message
        self.success_message = success_message
        self.addend = 1
        self.size = 8
        sublime.set_timeout(lambda: self.run(0), 100)

    def run(self, i):
        if not self.thread.is_alive():
            if hasattr(self.thread, 'result') and not self.thread.result:
                sublime.status_message('')
                return
            sublime.status_message(self.success_message)
            return

        before = i % self.size
        after = (self.size - 1) - before

        sublime.status_message('%s [%s=%s]' % \
            (self.message, ' ' * before, ' ' * after))

        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        i += self.addend

        sublime.set_timeout(lambda: self.run(i), 100)


class BundleUtil():
    """
    A utility class for working with Bundler
    """

    PATTERN_GEM_VERSION = "\* (.*)"
    PATTERN_GEM_NAME = "(.*)\("
    GEMS_NOT_FOUND = 'Gems Not Found'

    def __init__(self, root_path):
        self.root_path = root_path

    def bundle_list(self):
        output = self.run_subprocess("bundle list")
        gems = []

        if output is not None:
            if sys.version_info < (3, 0):
                output = str(output)
            else:
                output = str(output, encoding='utf-8')

            for line in output.split('\n'):
                gem_name_version = re.search(self.PATTERN_GEM_VERSION, line)
                if gem_name_version is not None:
                    gems.append(gem_name_version.group(1))

            if gems == []:
                gems.append(self.GEMS_NOT_FOUND)

        return gems

    def bundle_list_done(self, picked):
        if picked == -1:
            return
        pass

    def bundle_install(self):
        output = self.run_subprocess("bundle install")
        gems = []

        if output is not None:
            if sys.version_info < (3, 0):
                output = str(output)
            else:
                output = str(output, encoding='utf-8')

            for line in output.split('\n'):
                gem_name_version = re.search('(Using|Installed)+(.*)', line)
                if gem_name_version is not None:
                    gems.append(gem_name_version.group(1))

            if gems == []:
                gems.append(self.GEMS_NOT_FOUND)

        return gems

    def bundle_update(self):
        output = self.run_subprocess("bundle update")
        gems = []

        if output is not None:
            if sys.version_info < (3, 0):
                output = str(output)
            else:
                output = str(output, encoding='utf-8')

            for line in output.split('\n'):
                gem_name_version = re.search("(Using|Installed)+(.*)", line)
                if gem_name_version is not None:
                    gems.append(gem_name_version.group())

            if gems == []:
                gems.append(self.GEMS_NOT_FOUND)

        return gems

    def bundle_update_done(self, picked):
        if picked == -1:
            return
        pass

    def bundle_exec(self, command):
        cmd = 'bundle exec ' + command
        return self.run_subprocess(cmd)

    def run_subprocess(self, command):
        gemfile_folder = self.gemfile_folder()
        if gemfile_folder is not None:
            current_path = pipes.quote(gemfile_folder)
        else:
            current_path = None
        if current_path is None:
            return None

        command_with_cd = 'cd ' + current_path + ' && ' + command

        # Search for RVM
        shell_process = subprocess.Popen(" if [ -f $HOME/.rvm/bin/rvm-auto-ruby ]; then echo $HOME/.rvm/bin/rvm-auto-ruby; fi", stdout=subprocess.PIPE, shell=True)
        rvm_executable = shell_process.communicate()[0].rstrip()

        if rvm_executable != '':
            rvm_command = 'cd ' + current_path + ' && $HOME/.rvm/bin/rvm-auto-ruby -S ' + command
            process = subprocess.Popen(rvm_command, stdout=subprocess.PIPE, shell=True)
            return process.communicate()[0]
        else:  # Search for rbenv
            rbenv_command = 'cd ' + current_path + ' && ~/.rbenv/shims/' + command
            process = subprocess.Popen(rbenv_command, stdout=subprocess.PIPE, shell=True)
            output = process.communicate()[0]
            if output != '':
                return output
            else:  # Try for a windows output
                process = subprocess.Popen(command_with_cd, stdout=subprocess.PIPE, shell=True)
                output = process.communicate()[0]
                if output != '':
                    return output

    def gemfile_folder(self):
        """
        Search for the Gemfile in the project
        """

        root = self.root_path
        matches = []
        for root, dirnames, filenames in os.walk(root):
            for filename in fnmatch.filter(filenames, 'Gemfile'):
                matches.append(os.path.join(root, filename))
                break
        if matches == []:
            return None
        return os.path.dirname(matches[0])

    def get_sublime_path(self):
        """
        Find the path to sublime

        Initially taken from the sublime gem package, https://github.com/NaN1488/sublime-gem-browser
        """
        if sublime.platform() == 'osx':
            if not self.app_path_mac:
                # taken from https://github.com/freewizard/SublimeGotoFolder/blob/master/GotoFolder.py:
                from ctypes import cdll, c_int, c_char_p, c_void_p
                # Structure, byref
                from ctypes.util import find_library
                Foundation = cdll.LoadLibrary(find_library('Foundation'))
                CFBundleGetMainBundle = Foundation.CFBundleGetMainBundle
                CFBundleGetMainBundle.restype = c_void_p
                bundle = CFBundleGetMainBundle()
                CFBundleCopyBundleURL = Foundation.CFBundleCopyBundleURL
                CFBundleCopyBundleURL.argtypes = [c_void_p]
                CFBundleCopyBundleURL.restype = c_void_p
                url = CFBundleCopyBundleURL(bundle)
                CFURLCopyFileSystemPath = Foundation.CFURLCopyFileSystemPath
                CFURLCopyFileSystemPath.argtypes = [c_void_p, c_int]
                CFURLCopyFileSystemPath.restype = c_void_p
                path = CFURLCopyFileSystemPath(url, c_int(0))
                CFStringGetCStringPtr = Foundation.CFStringGetCStringPtr
                CFStringGetCStringPtr.argtypes = [c_void_p, c_int]
                CFStringGetCStringPtr.restype = c_char_p
                self.app_path_mac = CFStringGetCStringPtr(path, 0)
                CFRelease = Foundation.CFRelease
                CFRelease.argtypes = [c_void_p]
                CFRelease(path)
                CFRelease(url)
            return self.app_path_mac.decode() + '/Contents/SharedSupport/bin/subl'
        if sublime.platform() == 'linux':
            return open('/proc/self/cmdline').read().split(chr(0))[0]
        return sys.executable


class BundleExecCommand(sublime_plugin.WindowCommand):
    """
    A command to run an arbitrary bundle exec command
    """
    def run(self):
        self.window.show_input_panel('Bundle command', '',
                                     self.on_done, self.on_change, self.on_cancel)

    def on_done(self, input):
        self.command = input
        thread = BundleExecThread(self.window, self.window.folders()[0], input)
        thread.start()
        ThreadProgress(thread, 'Executing Bundler Command', '')

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass


class BundleExecThread(threading.Thread, BundleUtil):
    def __init__(self, window, root_path, command):
        self.window = window
        self.root_path = root_path
        self.command = command
        threading.Thread.__init__(self)
        BundleUtil.__init__(self, root_path)

    def run(self):
        self.output = self.bundle_exec(self.command)

        def show_output():
            if self.output == "":
                return
            self.output_view = self.window.get_output_panel('bundle_exec')
            self.output_view.set_read_only(False)
            edit = self.output_view.begin_edit()
            self.output_view.insert(edit, 0, self.output)
            self.output_view.end_edit(edit)
            self.output_view.set_read_only(True)
            self.window.run_command("show_panel", {"panel": "output.bundle_exec"})

        sublime.set_timeout(show_output, 10)


class BundleInstallCommand(sublime_plugin.WindowCommand):
    """
    A command that installs the gems in the Gemfile (by bundle install command)
    """
    def run(self):
        thread = BundleListThread(self.window, self.window.folders()[0])
        thread.start()
        ThreadProgress(thread, 'Installing Packages', '')


class BundleInstallThread(threading.Thread, BundleUtil):
    """
    A thread to prevent freezing the UI
    """

    def __init__(self, window, root_path):
        self.window = window
        self.root_path = root_path
        threading.Thread.__init__(self)
        BundleUtil.__init__(self, root_path)

    def run(self):
        self.gems = self.bundle_install()

        def show_quick_panel():
            if not self.gems:
                sublime.error_message(('%s: Unable to install') % __name__)
                return
            self.window.show_quick_panel(self.gems, self.bundle_list_done)

        sublime.set_timeout(show_quick_panel, 10)


class BundleListCommand(sublime_plugin.WindowCommand):
    """
    A command that shows a list of all installed gems (by bundle list command)
    """
    def run(self):
        thread = BundleListThread(self.window, self.window.folders()[0])
        thread.start()
        ThreadProgress(thread, 'Gathering Packages', '')


class BundleListThread(threading.Thread, BundleUtil):
    """
    A thread to prevent freezing the UI
    """

    def __init__(self, window, root_path):
        self.window = window
        self.root_path = root_path
        threading.Thread.__init__(self)
        BundleUtil.__init__(self, root_path)

    def run(self):
        self.gems = self.bundle_list()

        def show_quick_panel():
            if not self.gems:
                sublime.error_message(('%s: No gems to list') % __name__)
                return
            self.window.show_quick_panel(self.gems, self.bundle_list_done)

        sublime.set_timeout(show_quick_panel, 10)


class BundleUpdateCommand(sublime_plugin.WindowCommand):
    """
    A command that update the installed gems (by bundle update command)
    """
    def run(self):
        thread = BundleUpdateThread(self.window, self.window.folders()[0])
        thread.start()
        ThreadProgress(thread, 'Updating Bundle', '')


class BundleUpdateThread(threading.Thread, BundleUtil):
    """
    A Thread to prevent freezing while bundle update does its thing.
    """
    def __init__(self, window, root_path):
        self.window = window
        self.root_path = root_path
        threading.Thread.__init__(self)
        BundleUtil.__init__(self, root_path)

    def run(self):
        self.gems = self.bundle_update()
        def show_quick_panel():
           if not self.gems:
               sublime.error_message(('%s: No gems to list') % __name__)
               return
           self.window.show_quick_panel(self.gems, self.bundle_update_done)
        sublime.set_timeout(show_quick_panel, 10)
