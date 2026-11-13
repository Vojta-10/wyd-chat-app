import unicodedata
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.core.constants import AllowedThemes

type AccentColor = Annotated[
    str,
    Field(pattern=r"^#[0-9a-fA-F]{6}$"),
    AfterValidator(lambda value: value.upper()),
]


def reject_control_chars(exempt_chars: frozenset[str] = frozenset()) -> AfterValidator:
    def _validator(value: str) -> str:
        categories = [(char, unicodedata.category(char)) for char in value]
        for char, category in categories:
            if category.startswith("C") and char not in exempt_chars:
                raise ValueError("Contains invalid characters")
        return value

    return AfterValidator(_validator)


type DisplayName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=64),
    reject_control_chars(),
]

type Bio = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=128),
    reject_control_chars(frozenset({"\n"})),
]

type Pronouns = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=16), reject_control_chars()
]


class UserProfileSelf(BaseModel):
    display_name: str
    bio: str
    theme: AllowedThemes
    accent_color: str | None
    pronouns: str


class UserProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accent_color: AccentColor | None = None
    display_name: DisplayName | None = None
    bio: Bio | None = None
    theme: AllowedThemes | None = None
    pronouns: Pronouns | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def enforce_non_null_display_name(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Display name must not be null")
        return v

    @field_validator("bio", mode="before")
    @classmethod
    def normalize_bio_new_lines(cls, v: Any) -> Any:
        if v is None:
            return ""
        if isinstance(v, str):
            v = v.replace("\r\n", "\n")
        return v

    @field_validator("theme", mode="before")
    @classmethod
    def normalize_theme_treat_null_as_system_default(cls, v: Any) -> Any:
        if v is None:
            return "system"
        return v

    @field_validator("pronouns", mode="before")
    @classmethod
    def normalize_pronouns_turn_null_to_empty_string(cls, v: Any) -> Any:
        if v is None:
            return ""
        return v
