from . import Module


class Chat(Module):
    key, title, short, icon, kind = "chat", "Chat commands", "Chat", "💬", "utility"
    blurb = "Keys that type /hideout and your own chat commands into the game."

    def build(self, body):
        self.app.build_chat_window(body)

    def on_show(self):
        self.app.util_refresh()

    def status(self):
        return self.app.chat_status()
