
class Criteria:
    def __init__(self,crit_rule_id:str, crit_type:str, crit_identifier: list[str], crit_field:str,
                 crit_operator:str, crit_value: list, raw_text:str, description:str, confidence: float,
                 coding_system:str,code:str, unit:str) -> None:
        self.rule_id = crit_rule_id
        self.type = crit_type
        self.identifier = crit_identifier
        self.field = crit_field
        self.operator = crit_operator
        self.value = crit_value
        self.raw_text = raw_text
        self.weight = 1
        self.active = True
        self.description = description
        self.confidence = confidence
        if coding_system is not None:
            self.coding_system = coding_system
        if code is not None:
            self.code = code
        if unit:
            self.unit = unit

    def meets(self, patient)-> tuple[bool,str]:
        if self.type == 'demographic':
            if 'demographics' not in patient['general']:
                #print("check 1")
                return False,"NA"
            section = patient['general']['demographics']
        elif self.type == 'lab_result':
            if 'lab_results' not in patient:
                #print("check 2")
                return False,"NA"
            section = patient['lab_results']
        elif self.type == 'condition':
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

        if type(section) is not list and self.identifier[0] in section:
            #print("not list",self.identifier[0])
            value = section[self.field]
        else:
            for item in section:
                #print(item,self.identifier)
                if self.identifier[0] in item and (len(self.identifier) == 1 or
                    self.identifier[1] == item[self.identifier[0]]):
                    #print(item)
                    #print(self.field)
                    value = item[self.field]

        if value is None:
            #print("check 6")
            return False,"NA"

        if self.operator == "between":
            min = float(self.value[0])
            max = float(self.value[1])
            return min <= value <= max, value
        elif self.operator == "==":
            return self.value[0] == value, value
        elif self.operator == "!=":
            return self.value[0] != value, value
        elif self.operator == ">":
            return float(value) > float(self.value[0]), value
        elif self.operator == "<":
            return float(value) < float(self.value[0]), value
        elif self.operator == ">=":
            return float(value) >= float(self.value[0]), value
        elif self.operator == "<=":
            return float(value) <= float(self.value[0]), value
        else:
            return False,"NA"

    def str(self) -> str:
        return self.rule_id