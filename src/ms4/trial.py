from criteria import Criteria
from reasoning_step import ReasoningStep
from scored_patient import ScoredPatient


class Trial:
    def __init__(self,trial_data: dict)->None:
        self.nct_id = trial_data['nct_id']
        self.parsing_timestamp = trial_data['parsing_timestamp']
        self.inclusion_criteria = []

        if 'inclusion_criteria' in trial_data:
            inclusion_criteria = trial_data['inclusion_criteria']

            for crit in inclusion_criteria:
                rule_id = crit['rule_id']
                crit_type = crit['type']
                identifier = crit['identifier']
                field = crit['field']
                operator = crit['operator']
                value = crit['value']
                raw_text = crit['raw_text']
                description = crit['description'] if 'description' in crit else None
                confidence = crit['confidence'] if 'confidence' in crit else None
                coding_system = crit['coding_system'] if 'coding_system' in crit else None
                coding = crit['coding'] if 'coding' in crit else None
                unit = crit['unit'] if 'unit' in crit else None
                '''self,crit_rule_id:str, +
                crit_type:str, +
                crit_identifier: list[str], +
                crit_field:str,+
                 crit_operator:str, +
                 crit_value: list, +
                  raw_text:str, +
                  description:str, 
                  confidence: float,
                 coding_system:str=None,
                 code:str=None, 
                 unit:str=""'''
                self.inclusion_criteria.append(Criteria(rule_id, crit_type,identifier, field, operator,
                            value, raw_text, description, confidence, coding_system,coding, unit))

        self.exclusion_criteria = []
        if 'exclusion_criteria' in trial_data:
            exclusion_criteria = trial_data['exclusion_criteria']

            for crit in exclusion_criteria:
                rule_id = crit['rule_id']
                crit_type = crit['type']
                identifier = crit['identifier']
                field = crit['field']
                operator = crit['operator']
                raw_text = crit['raw_text']
                values = crit['value']
                description = crit['description'] if 'description' in crit else None
                confidence = crit['confidence'] if 'confidence' in crit else None
                coding_system = crit['coding_system'] if 'coding_system' in crit else None
                coding = crit['coding'] if 'coding' in crit else None
                unit = crit['unit'] if 'unit' in crit else None

                self.exclusion_criteria.append(Criteria(rule_id, crit_type,identifier, field, operator,
                            value, raw_text, description, confidence, coding_system,coding, unit))

        self.parsing_confidence = trial_data['parsing_confidence'] if 'parsing_confidence' in trial_data else None
        self.total_rules_extracted = trial_data['total_rules_extracted'] if 'total_rules_extracted' in trial_data else None
        self.model_used = trial_data['model_used'] if 'model_used' in trial_data else None
        self.meet_percentage = 100

        self.reasoning_steps = []
        if 'reasoning_steps' in trial_data:
            reasoning_steps = trial_data['reasoning_steps']

            for reason in reasoning_steps:
                step = int(reason['step'])
                description = reason['description']
                confidence = float(reason['confidence'])
                self.reasoning_steps.append(ReasoningStep(step, description, confidence))

    def get_total_weight(self) -> float:
        total = 0
        for inclusion in self.inclusion_criteria:
            total += inclusion.weight
        return total

    def get_heading(self) -> str:
        heading = f'Finding Matches ({self.meet_percentage:.2f}%):\n'
        heading+= f'{"patient id":<15}|{"percentage":<12}|{"total score":<12}'
        for crit in self.inclusion_criteria:
            if crit.is_active():
                heading+=f'|{crit.get_raw_text()+" ("+str(crit.get_weight())+")":<20}'
        heading+="|"
        return heading

    def set_meet_percentage(self, meet_percentage) -> None:
        self.meet_percentage = meet_percentage

    def str(self) -> str:
        text = "Trial ID: " + str(self.nct_id)
        return text

    def evaluate(self, patients) -> str:
        matches = []
        total_patients_evaluated = 0
        total_patients_matches_found=0
        exclusion_count = 0
        total_match_score = 0
        perfect_match_count = 0
        for patient in patients:
            total_patients_evaluated += 1
            patient_id = patient['general']['patient_id']
            #print("Processing:" + patient_id)

            exclude = False
            for exclusion in self.exclusion_criteria:
                #print("Exclusion:", exclusion, exclusion.active, exclusion.meets(patient)[0])
                if exclusion.active and exclusion.meets(patient)[0]:
                    #print("\tExcluded due to :" + str(exclusion))
                    exclude = True
                    break

            if exclude:
                exclusion_count += 1
                continue

            # print("\tNot Excluded ")

            category_results = []
            total = 0

            for inclusion in self.inclusion_criteria:
                if inclusion.active:
                    results = inclusion.meets(patient)

                    if results[0]:
                        total += inclusion.weight

                    category_results.append((inclusion.rule_id,
                                             inclusion.description,
                                             inclusion.raw_text,
                                             results[1],
                                             inclusion.weight,
                                             results[0]))
            '''
                tuple description:
                rule_id,
                description,
                raw_text,
                value,
                weight,
                meets
                '''
            total_match_score += total
            percentage = 100 * total / self.get_total_weight()
            #print(f"\t Score: {total} Percentage {100*percentage:.2f}%")

            # print("***"+str(trial.get_meet_percentage()))

            if total == self.get_total_weight():
                perfect_match_count += 1

            if percentage >= self.meet_percentage:
                # print("Added")
                total_patients_matches_found += 1
                matches.append(ScoredPatient(patient_id, percentage, total, category_results))

        json= ('{\n'
               '\t"nct_id": "' + str(self.nct_id) +'"\n'
               '\t"parsing_timestamp": "' + str(self.parsing_timestamp) + '"\n'
               '\t"matching_timestamp": "' + str("NOT IMPLEMENTED") + '"\n'
               '\t"total_weight": ' + str(self.get_total_weight()) + '\n'
               '\t"required_percentage": ' + str(self.meet_percentage) + '\n'
               '\t"patients_evaluated": ' + str(total_patients_evaluated) + '\n'
               '\t"exclusion_count": ' + str(exclusion_count) + '\n'
               '\t"match_count": ' + str(total_patients_matches_found) + '\n'
               '\t"average_match_score": ' + str(total_match_score/total_patients_matches_found) + '\n'
               '\t"perfect_match_count": ' + str(perfect_match_count) + '\n'
               '\t"matches": [\n')

        match_text=""
        for match in matches:
            match_text += match.generate_json()+",\n"

        json += (match_text[0:-2] if match_text else "") + "\n\t]\n}"

        return json