class ReasoningStep:
    def __init__(self,step:int, description:str, confidence:float) -> None:
        self.__step = step
        self.__description = description
        self.__confidence = confidence

    @property
    def step(self) -> int:
        return self.__step

    @property
    def description(self) -> str:
        return self.__description

    @property
    def confidence(self) -> float:
        return self.__confidence