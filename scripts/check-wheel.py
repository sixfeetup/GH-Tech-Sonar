"""Check that a built wheel includes Tech Sonar's managed resources."""

import sys
import zipfile


def main() -> None:
    required = {
        "tech_sonar/issue_templates/technology.yml",
        "tech_sonar/web/index.html",
        "tech_sonar/web/package.json",
        "tech_sonar/web/package-lock.json",
        "tech_sonar/web/src/main.tsx",
        "tech_sonar/web/vite.config.ts",
    }
    with zipfile.ZipFile(sys.argv[1]) as wheel:
        missing = required.difference(wheel.namelist())
    if missing:
        raise SystemExit(f"wheel is missing resources: {sorted(missing)}")


if __name__ == "__main__":
    main()
