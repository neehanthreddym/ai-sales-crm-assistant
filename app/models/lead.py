import re
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class ContactMethod(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"


class LeadInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    vehicle_interest: str | None = Field(default=None, max_length=160)
    budget: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    financing_interest: bool = False
    trade_in_interest: bool = False
    preferred_contact_method: ContactMethod = ContactMethod.EMAIL
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("first_name", "last_name")
    @classmethod
    def reject_blank_names(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name cannot be blank")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        digits = re.sub(r"\D", "", value)
        if not 7 <= len(digits) <= 15:
            raise ValueError("phone must contain 7 to 15 digits")
        return f"+{digits}" if value.startswith("+") else digits

    @model_validator(mode="after")
    def phone_method_requires_phone(self) -> "LeadInput":
        if (
            self.preferred_contact_method in {ContactMethod.PHONE, ContactMethod.SMS}
            and not self.phone
        ):
            raise ValueError("phone is required for phone or sms contact preference")
        return self
