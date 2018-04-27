# Terminal Messenger

## Facebook Messenger Client


Requires `python3`, `pip3` and a terminal that supports n-curses.

Requires `fbchat` library:
[https://github.com/carpedm20/fbchat](https://github.com/carpedm20/fbchat)


```
pip3 install fbchat
```

```
$ git clone https://github.com/fg123/terminal-messenger.git
$ cd terminal-messenger
$ python3 main.py
```

On first launch, it will prompt for your Facebook login information.
Afterwards, it will store a session cookie, stored in a file called `session`
and use that to log-in instead. 

## Usage

On launch, there will be a tab called `Messenger`. This is the main tab that
allows you to open other threads in other tabs. Navigating between tabs is done
with `Tab` and `Shift-Tab`. Pressing enter will run the given command on the
`Messenger` tab or it will send a message in any other tab.

As stated on the main page, after loading, a list of your last 10 conversations
will appear. Sending a number on the main tab will open the thread
corresponding to that number. Typing a name will search and return the top
result. You can also type `quit` to exit without logging out, or `logout` to
exit and logout.

## Seen Behaviour

When a message is incoming, it will be marked as delivered, even if you are
currently on the tab. It is only marked as seen when you begin to type in the
input buffer.


