import nox

PYTHONS = ["3.9", "3.10", "3.11", "3.12"]


@nox.session(python=PYTHONS)
def tests(session):
    session.install(".[dev]")
    session.run("coverage", "run", "-m", "unittest")
    session.run("coverage", "report", "-m")
