# Import Guard and Validator
from guardrails.hub import ToxicLanguage
from guardrails import Guard

# Use the Guard with the validator
guard = Guard().use(
    ToxicLanguage, threshold=0.5, validation_method="sentence", on_fail="exception"
)

# Test passing response
guard.validate("Love how you think and attack the problem. Great job!")

try:
    # Test failing response
    guard.validate(
        "Please look carefully. Eres un estupido que no hace nada bien."
    )
except Exception as e:
    print(e)