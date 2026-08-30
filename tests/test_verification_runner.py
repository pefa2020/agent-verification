from verification.runner_logic import status_from_return_code

def test_zero_exit_code_is_pass():
    assert status_from_return_code(0) == "PASS"

def test_nonzero_exit_code_is_fail():
    assert status_from_return_code(1) == "FAIL"

def test_any_nonzero_exit_code_is_fail():
    assert status_from_return_code(127) == "FAIL"
