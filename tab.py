# Tab.py
# Represents one thread in messenger, with a buffer for the current message.

import fbchat
import curses
import logging
import threading


class Tab(object):
    def __init__(self, client):
        self.command_buffer = ''
        self.title = ''
        self.messages = []
        self.client = client
        self._notify = False

    def push_message(self, message, attr=curses.A_NORMAL):
        self.messages.append((message, attr))
        self.client.request_chat_update(self)

    def notify(self):
        self._notify = True
        self.client.update_tabs()

    def mark_seen(self):
        self._notify = False

    def on_command(self, command):
        # Must Implement
        pass


class FbThread(object):
    def __init__(self, client, thread):
        self.thread = thread
        self.client = client
        self.last_messages = client.fb.fetchThreadMessages(self.thread.uid)
        self.is_unread = False
        if len(self.last_messages) > 0:
            self.is_unread = not self.last_messages[0].is_read


class MainTab(Tab):
    def __init__(self, client, title):
        Tab.__init__(self, client)
        self.title = title
        self.load_welcome_message()

    def load_welcome_message(self):
        # Don't force a update because we haven't initialized curses yet!
        self.messages.append(('Welcome to Terminal Messenger',
                              curses.A_NORMAL))
        self.messages.append(('You\'re logged in as ' + self.client.me.name,
                              curses.A_NORMAL))
        self.messages.append(('', curses.A_NORMAL))
        self.messages.append(
            ('Type `quit` to exit the program without logging out.',
             curses.A_NORMAL))
        self.messages.append(('Type `logout` to log out then exit.',
                              curses.A_NORMAL))
        self.messages.append(('Type `reload` to reload your last threads.',
                              curses.A_NORMAL))
        self.messages.append(('Type a number to open that person\'s chat.',
                              curses.A_NORMAL))
        self.messages.append(('Type a name to search for that person.',
                              curses.A_NORMAL))
        self.messages.append(('', curses.A_NORMAL))
        self.threads = []

        threading.Thread(target=self.load_top_threads).start()

    def load_top_threads(self):
        self.threads = list(
            map(lambda thread: FbThread(self.client, thread),
                self.client.fb.fetchThreadList(limit=10)))

        self.messages.append(
            ('Your last ' + str(len(self.threads)) + ' threads:',
             curses.A_NORMAL))

        for i, thread in enumerate(self.threads):
            flag = curses.A_BOLD if thread.is_unread else curses.A_NORMAL
            self.messages.append(('[' + str(i) + '] ' + thread.thread.name,
                                  flag))
        self.client.has_update = True

    def on_command(self, command):
        if command.lower() == 'quit':
            self.client.quit = True
        elif command.lower() == 'logout':
            self.client.logout = True
            self.client.quit = True
        elif command.lower() == 'reload':
            self.messages.clear()
            self.load_welcome_message()
            self.client.has_update = True
        elif command.isdigit():
            # Go to thread
            idx = int(command)
            if idx < 0 or idx >= len(self.threads):
                self.push_message('Out of range, no thread on that index.',
                                  curses.A_BOLD)
            else:
                self.client.go_to_thread(self.threads[idx])
        else:
            # Search for
            self.push_message('Searching for ' + command)
            threads = self.client.fb.searchForThreads(command)
            start_index = len(self.threads)
            self.threads.extend(
                map(lambda thread: FbThread(self.client, thread), threads))
            logging.debug(threads)
            for thread in threads:
                self.push_message('[' + str(start_index) + '] ' + thread.name)
                start_index += 1


class ThreadTab(Tab):
    def __init__(self, client, thread: fbchat.models.Thread):
        Tab.__init__(self, client)
        self._thread = thread
        self._client = client
        self.message_buffer = ''
        self.title = thread.name
        self.thread_messages = []
        self.has_unread = False
        self.has_added = set()
        threading.Thread(target=self.load_thread_messages).start()

    def load_thread_messages(self):
        self.thread_messages = self.client.fb.fetchThreadMessages(
            thread_id=self._thread.uid, limit=self.client.height - 3)
        self.thread_messages.reverse()
        for message in self.thread_messages:
            self.push_message(self.client.thread_message_to_string(message))

    def on_incoming_message(self, message):
        if message.uid not in self.has_added:
            self.has_added.add(message.uid)
            self.push_message(self.client.thread_message_to_string(message))
            self.has_unread = True

    def mark_seen(self):
        Tab.mark_seen(self)
        if self.has_unread:
            threading.Thread(
                target=self.client.fb.markAsRead,
                args=(self._thread.uid, )).start()
            self.has_unread = False

    def on_command(self, command):
        # Send Message
        self.client.fb.send(
            fbchat.models.Message(text=command),
            thread_id=self._thread.uid,
            thread_type=self._thread.type)
