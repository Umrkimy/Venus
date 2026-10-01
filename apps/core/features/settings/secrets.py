from cryptography.fernet import Fernet


# Fernet works on bytes, so text is encoded going in and decoded coming out.
def encrypt_text(text: str, secret_key: str) -> str:
    return Fernet(secret_key.encode()).encrypt(text.encode()).decode()


def decrypt_text(token: str, secret_key: str) -> str:
    return Fernet(secret_key.encode()).decrypt(token.encode()).decode()
