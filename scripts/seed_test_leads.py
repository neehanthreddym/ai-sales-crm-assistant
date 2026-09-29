import json
from pathlib import Path

FIXTURE = Path(__file__).parents[1] / "tests" / "fixtures" / "synthetic_leads.json"


def main() -> None:
    leads = json.loads(FIXTURE.read_text())
    print(json.dumps(leads, indent=2))


if __name__ == "__main__":
    main()
