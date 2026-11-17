import unicodedata

from pydantic import AfterValidator


def reject_control_chars(exempt_chars: frozenset[str] = frozenset()) -> AfterValidator:
    def _validator(value: str) -> str:
        categories = [(char, unicodedata.category(char)) for char in value]
        for char, category in categories:
            if category.startswith("C") and char not in exempt_chars:
                raise ValueError("Contains invalid characters")
        return value

    return AfterValidator(_validator)


def username_not_reserved(reserved_names: list[str]) -> AfterValidator:
    def _validator(username: str) -> str:
        if username.lower() in reserved_names:
            raise ValueError("Reserved username")
        return username

    return AfterValidator(_validator)
