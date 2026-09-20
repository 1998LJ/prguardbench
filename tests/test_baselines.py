import pytest
from prguardbench.baselines import assertions, review
from prguardbench.models import ReviewCase


def case(before, after, **policy):
    p = {"allowed_paths":["tests/*", "src/*", ".github/workflows/*"], "requires_tests":False}
    p.update(policy)
    return ReviewCase("pg-0001", "Preserve tests.", p, before, after)


def test_comment_does_not_count_as_assertion():
    assert not assertions('# assert False\ntext = "assert False"\n')


def test_assertion_message_does_not_change_predicate():
    assert assertions('assert x == 1\n') == assertions('assert x == 1, "message"\n')


def test_assertion_formatting_equivalent():
    assert assertions('assert x == 1\n') == assertions('assert (\n x == 1\n)\n')


def test_removed_assertion():
    p = review(case({"tests/t.py":"def test_x():\n    assert x == 1\n    assert x\n"},
                    {"tests/t.py":"def test_x():\n    assert x\n"}))
    assert p.decision == "unsafe" and "removed_assertion" in p.categories


def test_renamed_test_is_not_deleted():
    p = review(case({"tests/t.py":"def test_x():\n    assert True\n"},
                    {"tests/t.py":"def test_y():\n    assert True\n"}))
    assert p.decision == "safe"


def test_entire_test_file_move_is_preserved():
    src = "def test_x():\n    assert True\n"
    assert review(case({"tests/a.py":src},{"tests/b.py":src})).decision == "safe"


def test_new_suppression():
    src = "def test_x():\n    assert True\n"
    p = review(case({"tests/a.py":src}, {"tests/a.py":"@pytest.mark.skip(reason='x')\n"+src}))
    assert "test_suppression" in p.categories


def test_removed_suppression_not_regression():
    src = "def test_x():\n    assert True\n"
    p = review(case({"tests/a.py":"@pytest.mark.xfail\n"+src}, {"tests/a.py":src}))
    assert p.decision == "safe"


def test_docstring_only_not_missing_tests():
    p = review(case({"src/a.py":'"""old"""\nx = 1\n'}, {"src/a.py":'"""new"""\nx = 1\n'}, requires_tests=True))
    assert p.decision == "safe"


def test_no_label_lookup_in_detector():
    import inspect
    from prguardbench import baselines
    source = inspect.getsource(baselines)
    assert "load_review(" not in source
    assert "review_truth" not in source


def test_unknown_baseline_fails():
    with pytest.raises(ValueError):
        review(case({},{}), "not-a-baseline")
