from features.auth.passwords import hash_password, verify_password


def test_verify_password_accepts_correct_password():
    stored_hash = hash_password("correct horse")

    assert verify_password("correct horse", stored_hash) is True


def test_verify_password_rejects_wrong_password():
    stored_hash = hash_password("correct horse")

    assert verify_password("wrong", stored_hash) is False