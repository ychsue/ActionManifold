import weakref
import gc
import threading

class LeakMonitor:
    orchestrators = []
    contexts = []

    @staticmethod
    def track_orchestrator(orch):
        LeakMonitor.orchestrators.append(weakref.ref(orch))

    @staticmethod
    def track_ctx(ctx):
        LeakMonitor.contexts.append(weakref.ref(ctx))
        
    @staticmethod
    def check():
        gc.collect()

        alive_orch = [r() for r in LeakMonitor.orchestrators if r() is not None]
        alive_ctx  = [r() for r in LeakMonitor.contexts if r() is not None]

        print(f"Alive orchestrators: {len(alive_orch)}")
        print(f"Alive contexts: {len(alive_ctx)}")

        if alive_orch or alive_ctx:
            print("⚠️ Possible memory leak detected")
        else:
            print("✅ No leaks detected")

    @staticmethod
    def check_orch():
        gc.collect()

        alive_orch = [r() for r in LeakMonitor.orchestrators if r() is not None]

        if alive_orch:
            print("⚠️ Possible memory leak detected, alive orchestrators:")
            for orch in alive_orch:
                print(f"  - {orch}")
        else:
            print("✅ No leaks orchestrator detected")


def leak_orch_checked_run(fn):
    async def wrapper(self, *args, **kwargs):
        # 1. track orchestrator
        LeakMonitor.track_orchestrator(self)

        # 2. run the orchestrator
        result = await fn(self, *args, **kwargs)

        # 3. schedule delayed check
        def delayed_check():
            LeakMonitor.check_orch()

        threading.Timer(0.1, delayed_check).start()

        return result
    return wrapper