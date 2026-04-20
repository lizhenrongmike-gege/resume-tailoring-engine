from app.services.team_detector import detect_team

def test_detects_team_header():
    jd = "About the role\nTeam: Risk Management\nWe are looking for..."
    assert detect_team(jd) == "Risk Management"

def test_detects_department_header():
    jd = "Department: Customer Support\nJoin us..."
    assert detect_team(jd) == "Customer Support"

def test_detects_join_the_team():
    jd = "You will join the Detection Engineering team and work on..."
    assert detect_team(jd) == "Detection Engineering"

def test_detects_part_of_team():
    jd = "As part of our Ads & Shopping team, you'll build..."
    assert detect_team(jd) == "Ads & Shopping"

def test_returns_none_when_no_match():
    jd = "We are looking for a software engineer to build great products."
    assert detect_team(jd) is None

def test_handles_empty_input():
    assert detect_team("") is None
    assert detect_team(None) is None
