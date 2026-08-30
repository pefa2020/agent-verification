def status_from_return_code(return_code: int) -> str:
    return "PASS" if return_code == 0 else "FAIL"
