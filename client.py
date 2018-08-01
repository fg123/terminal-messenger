# Client.py: The actual client.
import fbchat
import pickle  # For session file
import getpass
import curses
import string
import math
import textwrap
import logging
import threading
import queue

import tab
SESSION_FILE = 'session'

# To satisfy Pylint
curses.COLS = 0
curses.LINES = 0


class Client(object):
    def __init__(self):
        try:
            with open(SESSION_FILE, 'rb') as s:
                session = pickle.load(s)
                self.fb = ListeningClient('', '', session_cookies=session)
        except (IOError, fbchat.models.FBchatException):
            # Cookies Failed
            self.fb = None
            print('Session cookie not found, login with email and password.')
            while self.fb is None:
                email = input('Email: ')
                password = getpass.getpass('Password: ')
                try:
                    self.fb = ListeningClient(email, password, session_cookies=None)
                except fbchat.models.FBchatException:
                    print('Failed, please try again.')
                    self.fb = None
            try:
                with open(SESSION_FILE, 'wb') as s:
                    pickle.dump(self.fb.getSession(), s)
            except IOError:
                print('Error writing session cookie!')

        logging.critical(self.fb.getSession())
        self.quit = False
        self.logout = False
        self.fb.set_client(self)
        self.me = self.fb.fetchUserInfo(self.fb.uid)[self.fb.uid]
        assert self.me is not None
        self.tabs = [tab.MainTab(self, 'Messenger')]
        self.current_tab = 0
        self.user_cache = {}
        self.has_update = False

        # Start Listening
        thread = threading.Thread(target=self.fb.listen)
        thread.daemon = True
        thread.start()

        curses.wrapper(self.start)

    def get_user_by_id(self, id):
        if id not in self.user_cache:
            self.user_cache[id] = self.fb.fetchUserInfo(id)[id]
        return self.user_cache[id]

    def reset_ui(self):
        self.width = self.screen.getmaxyx()[1]
        self.height = self.screen.getmaxyx()[0]
        self.chat_width = self.width
        self.chat_height = self.height - 2
        self.screen.refresh()
        self.chat_window.resize(self.chat_height, self.chat_width)
        self.update_chat_window()
        self.update_tabs()
        self.update_command()

    def get_current_command_buffer(self):
        return self.tabs[self.current_tab].command_buffer

    def set_current_command_buffer(self, buf):
        self.tabs[self.current_tab].command_buffer = buf

    def get_current_messages(self):
        return self.tabs[self.current_tab].messages

    def close_tab(self, tab):
        if tab != 0:
            del self.tabs[tab]

    def start(self, screen):
        self.screen = screen
        # Setup ncurses
        self.screen.clear()
        self.chat_window = curses.newwin(0, 0, 1, 0)
        self.screen.nodelay(True)
        self.reset_ui()
        while not self.quit:
            self.update_tabs()
            self.update_command()
            if self.has_update:
                self.update_chat_window()
                self.has_update = False
            buf = self.get_current_command_buffer()
            c = self.screen.getch(self.height - 1, min(
                len(buf), self.width - 1))
            if c == curses.ERR: continue
            logging.debug('Got ch: ' + str(int(c)))
            if c == curses.KEY_RESIZE:
                self.reset_ui()
            elif c == curses.KEY_ENTER or c == 10 or c == 13:
                if len(buf) > 0:
                    self.set_current_command_buffer('')
                    self.tabs[self.current_tab].on_command(buf)
            elif c == curses.KEY_BACKSPACE or c == curses.KEY_DC or c == 127:
                if len(buf) > 0:
                    self.set_current_command_buffer(buf[:-1])
            elif c == 9:  # Tab
                self.go_to_tab(self.current_tab + 1)
            elif c == 353:  # Shift Tab
                self.go_to_tab(self.current_tab - 1)
            elif c == 23:  # Ctrl-W
                self.close_tab(self.current_tab)
                self.go_to_tab(self.current_tab - 1)
            elif chr(c) in string.printable:
                curr_tab = self.tabs[self.current_tab]
                self.set_current_command_buffer(buf + chr(c))
                curr_tab.mark_seen()

        if self.logout:
            self.fb.logout()

    def request_chat_update(self, tab):
        if tab is self.tabs[self.current_tab]:
            self.has_update = True

    def update_tabs(self):
        self.screen.move(0, 0)
        self.screen.clrtoeol()
        all_tabs = ''
        flags = []
        selected_start_pos = 0
        selected_len = 0
        for i in range(0, len(self.tabs)):
            flag = curses.A_REVERSE
            if i == self.current_tab:
                flag = curses.A_NORMAL
                selected_start_pos = len(all_tabs)
                selected_len = len(self.tabs[i].title) + 2
            if self.tabs[i]._notify:
                flag |= curses.A_BOLD
            str_to_add = ' ' + self.tabs[i].title + ' '
            all_tabs += str_to_add
            flags.extend([flag for i in range(0, len(str_to_add))])

        # Start represents at which character we start actually drawing
        start = 0
        if len(all_tabs) > self.width:
            # Not enough space, calculate resized left and right substring
            string_mid = selected_start_pos + math.floor(selected_len / 2)
            start = string_mid - math.floor(self.width / 2)
            if start < 0: start = 0
            if start > selected_start_pos:
                # Don't start at middle of string
                start = selected_start_pos
            while start + self.width > len(all_tabs):
                # Right bound past end
                start -= 1
        else:
            all_tabs = all_tabs.ljust(self.width, ' ')
            while len(flags) < self.width:
                flags.append(curses.A_REVERSE)

        all_tabs = all_tabs[start:start + self.width]
        flags = flags[start:start + self.width]
        for i in range(0, self.width):
            self.screen.addstr(0, i, all_tabs[i], flags[i])

    def update_chat_window(self):
        self.chat_window.clear()
        self.chat_window.box()
        # Subtract two for the borders
        max_rows = self.chat_height - 2
        row = 1
        actual_lines = []
        messages = self.get_current_messages()
        for string, attr in messages[-max_rows:]:
            lines = string.splitlines()
            if not lines:
                # We don't want to ignore empty lines (for new line purposes)
                actual_lines.append(('', attr))
            else:
                for line in lines:
                    parts = textwrap.wrap(line, self.chat_width - 2)
                    for part in parts:
                        actual_lines.append((part, attr))

        for line, attr in actual_lines[-max_rows:]:
            try:
                self.chat_window.addstr(row, 1, line, attr)
                row += 1
            except:
                pass
        self.chat_window.refresh()

    def update_command(self):
        self.screen.move(self.height - 1, 0)
        self.screen.clrtoeol()
        buf = self.get_current_command_buffer()
        self.screen.addstr(self.height - 1, 0, buf[-(self.width - 1):])

    def go_to_tab(self, i):
        self.current_tab = i
        if self.current_tab < 0: self.current_tab = len(self.tabs) - 1
        if self.current_tab >= len(self.tabs): self.current_tab = 0
        self.tabs[self.current_tab].mark_seen()
        self.update_chat_window()

    def thread_message_to_string(self, message: fbchat.models.Message):
        author = self.get_user_by_id(message.author).first_name
        if message.text:
            return author + ": " + message.text
        if message.sticker:
            return author + ': ' + '[Sticker]: ' + message.sticker.url
        if not message.attachments:
            return author + ': ' + '[Unhandled Message]'
        for attachment in message.attachments:
            if isinstance(attachment, fbchat.models.ImageAttachment):
                url = self.fb.fetchImageUrl(attachment.uid)
                return author + ': ' + '[Image Attachment]: ' + url
            elif isinstance(attachment, fbchat.models.VideoAttachment):
                return author + ': ' + '[Video Attachment]'
            else:
                return author + ': ' + '[Unhandled Attachment]'

    def go_to_thread(self, thread):
        # Check if tab exists for that thread
        # TODO(felixguo): Might be able to eliminate FB thread
        for i, _tab in enumerate(self.tabs[1:]):
            logging.debug(
                str(_tab._thread.uid) + ', ' + str(thread.thread.uid))
            if _tab._thread.uid == thread.thread.uid:
                self.go_to_tab(i + 1)
                return
        self.tabs.append(tab.ThreadTab(self, thread.thread))
        self.go_to_tab(len(self.tabs) - 1)

    def on_fb_message(self, author_id, message_object, thread_id, thread_type):
        # If thread is in a tab, we add to it, we request update
        for i, tab in enumerate(self.tabs[1:]):
            if tab._thread.uid == thread_id:
                tab.on_incoming_message(message_object)
                if self.current_tab == i + 1:
                    pass
                else:
                    tab.notify()
                self.has_update = True
                return
        self.tabs[0].push_message(
            'New message from ' + self.get_user_by_id(author_id).first_name +
            ' in ' + self.fetchThreadInfo(thread_id)[thread_id].name,
            curses.A_BOLD)
        self.tabs[0].notify()


class ListeningClient(fbchat.Client):
    def __init__(self, email, password, session_cookies):
        fbchat.Client.__init__(
            self,
            email=email,
            password=password,
            session_cookies=session_cookies,
            max_tries=1,
            logging_level=logging.CRITICAL)

    def set_client(self, client: Client):
        self._client = client

    def onMessage(self, author_id, message_object, thread_id, thread_type,
                  **kwargs):
        self.markAsDelivered(thread_id, message_object.uid)
        self._client.on_fb_message(author_id, message_object, thread_id,
                                   thread_type)
