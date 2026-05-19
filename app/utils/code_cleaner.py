def clean_code(code: str) -> str:
    code = code.strip()
    code = code.replace("\r\n", "\n")
    return code


def is_empty(code: str) -> bool:
    """
    Kodun boş olup olmadığını kontrol eder.
    """
    return len(clean_code(code)) == 0