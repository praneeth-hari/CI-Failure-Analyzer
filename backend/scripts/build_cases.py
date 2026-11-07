import sys

from app.analysis.cases import build_cases
from app.db.session import SessionLocal

if __name__ == "__main__":
    owner = name = None
    limit = None
    if len(sys.argv) > 1 and "/" in sys.argv[1]:
        owner, name = sys.argv[1].split("/", 1)
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    with SessionLocal() as session:
        print(build_cases(session, owner, name, limit))

