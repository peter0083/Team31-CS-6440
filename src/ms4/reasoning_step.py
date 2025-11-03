class ReasoningStep:
    def __init__(self, step: int, description: str, confidence: float) -> None:
        self.step = step
        self.description = description
        self.confidence = confidence
