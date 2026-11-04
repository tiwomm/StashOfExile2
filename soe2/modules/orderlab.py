from . import Module


class OrderLab(Module):
    """2.88.0: works out the trade site's listing order for a public tab (admins only)."""
    key, title, short, icon, kind = "orderlab", "Listing order lab", "Order lab", "🧪", "tool"
    parent = "library"                 # inside Under the hood
    advanced = True
    admin_only = True                  # only for a community board admin

    def build(self, body):
        self.app.build_orderlab(body)
