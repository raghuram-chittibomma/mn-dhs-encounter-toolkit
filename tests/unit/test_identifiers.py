import random

from mn_encounter_toolkit.identifiers.npi import generate_npi, is_valid_npi, npi_check_digit
from mn_encounter_toolkit.identifiers.tin import generate_tin
from mn_encounter_toolkit.identifiers.umpi import generate_umpi


def test_generated_npi_is_valid():
    rng = random.Random(1)
    for _ in range(50):
        npi = generate_npi(rng)
        assert len(npi) == 10
        assert npi.isdigit()
        assert is_valid_npi(npi)


def test_generated_organizational_npi_starts_with_2():
    rng = random.Random(2)
    npi = generate_npi(rng, is_organization=True)
    assert npi[0] == "2"


def test_generated_individual_npi_starts_with_1():
    rng = random.Random(2)
    npi = generate_npi(rng, is_organization=False)
    assert npi[0] == "1"


def test_npi_with_corrupted_check_digit_is_invalid():
    rng = random.Random(3)
    npi = generate_npi(rng)
    correct_check_digit = npi[9]
    bad_digit = str((int(correct_check_digit) + 1) % 10)
    corrupted = npi[:9] + bad_digit
    assert not is_valid_npi(corrupted)


def test_is_valid_npi_rejects_wrong_length():
    assert not is_valid_npi("123456789")
    assert not is_valid_npi("12345678901")


def test_is_valid_npi_rejects_non_digit():
    assert not is_valid_npi("12345abcd9")


def test_npi_check_digit_requires_nine_digits():
    import pytest

    with pytest.raises(ValueError):
        npi_check_digit("12345")


def test_generate_npi_is_deterministic_given_seed():
    a = generate_npi(random.Random(42))
    b = generate_npi(random.Random(42))
    assert a == b


def test_generate_umpi_is_eight_numeric_digits():
    rng = random.Random(4)
    umpi = generate_umpi(rng)
    assert len(umpi) == 8
    assert umpi.isdigit()


def test_generate_tin_uses_fictional_prefix_and_nine_digits():
    rng = random.Random(5)
    for _ in range(25):
        tin = generate_tin(rng)
        assert len(tin) == 9
        assert tin.isdigit()
        assert tin[:2] in ("90", "91", "92", "93")
