import pytest
from pydantic import ValidationError

from app.models.lead import LeadInput


def valid_lead(**overrides: object) -> LeadInput:
    data = {
        "first_name": "Alex",
        "last_name": "Example",
        "email": "alex.synthetic@example.com",
        "phone": "(901) 555-0123",
        "vehicle_interest": "2025 Honda CR-V",
        "budget": "35000",
        "preferred_contact_method": "email",
    }
    data.update(overrides)
    return LeadInput.model_validate(data)


def test_valid_lead_normalizes_phone() -> None:
    assert valid_lead().phone == "9015550123"


@pytest.mark.parametrize(
    ("field", "value"),
    [("first_name", " "), ("email", "not-an-email"), ("budget", 0), ("phone", "123")],
)
def test_invalid_lead_is_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        valid_lead(**{field: value})


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        valid_lead(secret="unexpected")


def test_phone_contact_method_requires_phone() -> None:
    with pytest.raises(ValidationError):
        valid_lead(phone=None, preferred_contact_method="phone")
