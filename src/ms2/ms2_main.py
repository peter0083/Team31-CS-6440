
"""MS2 Microservice: clinical trial criteria parser"""

from datetime import datetime

from src.ms2.ms2_models import (
    ExampleRequest,
    ExclusionCriteriaRule,
    InclusionCriteriaRule,
    ParsedCriteriaResponse,
)


class MS2Service:
    async def process(self, request: ExampleRequest) -> None:
        # Implement the processing logic here
        pass
        return

    async def parse_criteria(
        self, nct_id: str, raw_text: str
    ) -> ParsedCriteriaResponse:
        parsing_timestamp = datetime.now()
        inclusion_rules = []
        exclusion_rules = []

        # Example parsing logic (to be replaced with actual NLP processing)
        lines = raw_text.splitlines()
        for i, line in enumerate(lines):
            if "Inclusion Criteria:" in line:
                rule_id = f"inc{i+1:03}"
                type_ = "demographic"
                field = "age"
                operator = "between"
                min_value = 18
                max_value = 65
                unit = "years"
                raw_text = lines[i + 1]
                inclusion_rules.append(
                    InclusionCriteriaRule(
                        rule_id=rule_id,
                        type=type_,
                        field=field,
                        operator=operator,
                        min_value=min_value,
                        max_value=max_value,
                        unit=unit,
                        raw_text=raw_text,
                    )
                )

            elif "Exclusion Criteria:" in line:
                rule_id = f"exc{i+1:03}"
                type_ = "condition"
                field = "pregnancy_status"
                value = "pregnant"
                raw_text = lines[i + 1]
                exclusion_rules.append(
                    ExclusionCriteriaRule(
                        rule_id=rule_id,
                        type=type_,
                        field=field,
                        value=value,
                        raw_text=raw_text,
                    )
                )

        parsing_confidence = 0.92
        total_rules_extracted = len(inclusion_rules) + len(exclusion_rules)

        return ParsedCriteriaResponse(
            nct_id=nct_id,
            parsing_timestamp=parsing_timestamp,
            inclusion_criteria=inclusion_rules,
            exclusion_criteria=exclusion_rules,
            parsing_confidence=parsing_confidence,
            total_rules_extracted=total_rules_extracted,
        )