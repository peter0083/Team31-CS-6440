
class Criteria:
    def __init__(self,crit_rule_id:str, crit_type:str, crit_identifier: list[str], crit_field:str,
                 crit_operator:str, crit_value: list, raw_text:str, description:str, confidence: float,
                 coding_system:str,code:str, unit:str) -> None:
        self.__rule_id = crit_rule_id
        self.__type = crit_type
        self.__identifier = crit_identifier
        self.__field = crit_field
        self.__operator = crit_operator
        self.__value = crit_value
        self.__raw_text = raw_text
        self.__weight = 1
        self.__active = True
        self.__description = description
        self.__confidence = confidence
        if coding_system is not None:
            self.__coding_system = coding_system
        if code is not None:
            self.__code = code
        if unit:
            self.__unit = unit

    @property
    def rule_id(self) -> str:
        return self.__rule_id

    @property
    def type(self) -> str:
        return self.__type

    @property
    def identifier(self) -> list[str]:
        return self.__identifier

    @property
    def field(self) -> str:
        return self.__field

    @property
    def operator(self) -> str:
        return self.__operator

    @property
    def value(self) -> list[str]:
        return self.__value

    @property
    def raw_text(self) -> str:
        return self.__raw_text

    @property
    def description(self) -> str:
        return self.__description

    @property
    def confidence(self) -> float:
        return self.__confidence

    @property
    def coding_system(self) -> str:
        return self.__coding_system

    @property
    def code(self) -> str:
        return self.__code

    @property
    def unit(self) -> str:
        return self.__unit

    @property
    def weight(self) -> float:
        return self.__weight

    @property
    def active(self) -> bool:
        return self.__active

    def meets(self, patient)-> tuple[bool,str]:
        if self.__type == 'demographic':
            if 'demographics' not in patient['general']:
                #print("check 1")
                return False,"NA"
            section = patient['general']['demographics']
        elif self.__type == 'lab_result':
            if 'lab_results' not in patient:
                #print("check 2")
                return False,"NA"
            section = patient['lab_results']
        elif self.__type == 'condition':
            if 'conditions' not in patient:
                #print("check 2")
                return False,"NA"
            section = patient['conditions']
        else:
            #print("check 4")
            return False,"NA"

        if section is None:
            #print("check 5")
            return False,"NA"

        value = None

        if type(section) is not list and self.__identifier[0] in section:
            #print("not list",self.__identifier[0])
            value = section[self.__field]
        else:
            for item in section:
                #print(item,self.__identifier)
                if self.__identifier[0] in item and (len(self.__identifier) == 1 or
                    self.__identifier[1] == item[self.__identifier[0]]):
                    #print(item)
                    #print(self.__field)
                    value = item[self.__field]

        if value is None:
            #print("check 6")
            return False,"NA"

        if self.__operator == "between":
            min = float(self.__value[0])
            max = float(self.__value[1])
            return min <= value <= max, value
        elif self.__operator == "==":
            return self.__value[0] == value, value
        elif self.__operator == "!=":
            return self.__value[0] != value, value
        elif self.__operator == ">":
            return float(value) > float(self.__value[0]), value
        elif self.__operator == "<":
            return float(value) < float(self.__value[0]), value
        elif self.__operator == ">=":
            return float(value) >= float(self.__value[0]), value
        elif self.__operator == "<=":
            return float(value) <= float(self.__value[0]), value
        else:
            return False,"NA"

    def __str__(self) -> str:
        return self.__rule_id