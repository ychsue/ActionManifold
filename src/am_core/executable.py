class Executable:
    def __init__(self, ctx, parent=None):
        self.ctx = ctx
        self.parent = parent

    async def run(self, metadata):
        raise NotImplementedError

    def emit(self, event):
        # event 冒泡到 parent
        if self.parent:
            self.parent.emit(event)