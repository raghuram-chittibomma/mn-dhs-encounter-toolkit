"""National Provider Identifier (NPI) generation and validation.

NPI is a 10-digit number: 9 identifying digits + 1 Luhn check digit. The
check digit is computed per the CMS algorithm: prepend the fixed prefix
"80840" to the 9-digit base (forming a 14-digit payload), then apply the
standard Luhn (ISO/IEC 7812-1) check-digit algorithm to that 14-digit
payload. The prefix is a calculation constant only -- it is never part of
the final 10-digit NPI.

This is a base X12/CMS identifier rule (not MN/DHS-specific), so it carries
no companion-guide citation.
"""

from __future__ import annotations

import random

_NPI_LUHN_PREFIX = "80840"


def npi_check_digit(nine_digits: str) -> str:
    """Compute the Luhn check digit for a 9-digit NPI base."""
    if not (nine_digits.isdigit() and len(nine_digits) == 9):
        raise ValueError("nine_digits must be exactly 9 numeric characters.")
    payload = _NPI_LUHN_PREFIX + nine_digits
    total = 0
    for position_from_right, ch in enumerate(reversed(payload)):
        digit = int(ch)
        if position_from_right % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return str((10 - (total % 10)) % 10)


def is_valid_npi(npi: str) -> bool:
    """True if `npi` is exactly 10 digits and its check digit is correct."""
    if not (npi.isdigit() and len(npi) == 10):
        return False
    return npi_check_digit(npi[:9]) == npi[9]


def generate_npi(rng: random.Random, *, is_organization: bool = False) -> str:
    """Generate a structurally valid, fictional NPI.

    The first digit of the 9-digit base is conventionally 1 for individual
    providers and 2 for organizational providers (CMS NPI assignment
    convention); this is cosmetic realism, not a validation requirement.
    """
    first_digit = "2" if is_organization else "1"
    rest = "".join(str(rng.randint(0, 9)) for _ in range(8))
    nine = first_digit + rest
    return nine + npi_check_digit(nine)
