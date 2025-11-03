class ScoredPatient:

    def __init__(self, patient_id:str, percentage:float, score:float,
                 categories: list[tuple[str, str, str, str, float, bool]]) -> None:
        self.__patient_id = patient_id
        self.__score = score
        self.__percentage = percentage
        self.categories = categories

    def get_patient_id(self) -> str:
        return self.__patient_id

    def get_score(self) -> float:
        return self.__score

    def get_percentage(self) -> float:
        return self.__percentage

    def get_categories(self) -> list[tuple[str, str, str, str, float, bool]]:
        return self.categories

    def generate_json(self) -> str:
        json = ('\t\t{\n'
                '\t\t\t"patient_id": "' + str(self.__patient_id) + '"\n'
                '\t\t\t"score": "' + str(self.__score) + '"\n'
                '\t\t\t"percentage": ' + str(self.__percentage) + '"\n')

        json += "\t\t\tcriteria_results: [\n"
        criteria_results_text = ""
        for category in self.categories:
            criteria_results_text += "\t\t\t\t{\n"
            criteria_results_text += '\t\t\t\t\t"rule_id": "'+str(category[0])+'"\n'
            criteria_results_text += '\t\t\t\t\t"description": "' + str(category[1]) + '"\n'
            criteria_results_text += '\t\t\t\t\t"raw_text": "' + str(category[2]) + '"\n'
            criteria_results_text += '\t\t\t\t\t"value": ' + str(category[0]) + '\n'
            criteria_results_text += '\t\t\t\t\t"weight": ' + str(category[0]) + '\n'
            criteria_results_text += '\t\t\t\t\t"meets": ' + str(category[0]) + '\n'
            criteria_results_text += "\t\t\t\t},\n"

        json += (criteria_results_text[0:-2] if criteria_results_text else "") + "\n\t\t\t]\n\t\t}"

        return json