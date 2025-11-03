class ScoredPatient:

    def __init__(self, patient_id:str, percentage:float, score:float,
                 categories: list[tuple[str, str, str, str, float, bool]]) -> None:
        self.patient_id = patient_id
        self.score = score
        self.percentage = percentage
        self.categories = categories

    def generate_json(self) -> str:
        json = ('\t\t{\n'
                '\t\t\t"patient_id": "' + str(self.patient_id) + '"\n'
                '\t\t\t"score": "' + str(self.score) + '"\n'
                '\t\t\t"percentage": ' + str(self.percentage) + '"\n')

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