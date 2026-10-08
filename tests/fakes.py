from bharatbench.adapters.base import AdapterError, Settings


class FakeAdapter:
    """Stands in for a real provider. Records every call; never touches the network."""

    def __init__(self, model="fake-1", provider="fake", settings=None, fail_on=(), reply=None):
        self.model, self.provider = model, provider
        self.settings = settings or Settings(temperature=0.0)
        self.calls = []
        self.fail_on = set(fail_on)
        self.reply = reply or (lambda prompt, system: f"echo:{prompt}")

    def generate(self, prompt, system=None):
        self.calls.append((prompt, system))
        if prompt in self.fail_on:
            raise AdapterError("boom")
        return self.reply(prompt, system)


def make_task(tid, category="gst_tax", verified=True, prompt=None):
    return {
        "id": tid, "category": category, "prompt": prompt or f"prompt for {tid}", "language": "en",
        "answer_type": "numeric", "reference_answer": 1, "worked_solution": "1",
        "difficulty": "easy", "verified": verified,
    }
