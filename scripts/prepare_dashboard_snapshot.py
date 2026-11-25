"""Export the recoverable historical dashboard source for local pilot work."""

import argparse
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory


UPSTREAM = "https://github.com/roudayn-kouka/BH-Assurance.git"
REVISION = "a18e1e0fc402af64d63a16fba5532bc357d077e1"
MANIFESTS = {
    "backend/package.json", "backend/package-lock.json", "backend/tsconfig.json",
    "frontend/package.json", "frontend/package-lock.json", "frontend/index.html",
    "frontend/eslint.config.js", "frontend/postcss.config.js", "frontend/tailwind.config.ts",
    "frontend/tsconfig.json", "frontend/tsconfig.app.json", "frontend/tsconfig.node.json",
    "frontend/vite.config.ts", "frontend/components.json",
    "frontend/public/favicon.ico", "frontend/public/placeholder.svg",
    "frontend/public/robots.txt",
}
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".css", ".png", ".jpg", ".jpeg", ".svg"}


def prepare(destination):
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination}")

    with TemporaryDirectory(prefix="bh-dashboard-source-") as temporary:
        def git(*args, capture_output=False):
            return subprocess.run(
                ["git", "-C", temporary, *args], check=True, capture_output=capture_output,
            ).stdout

        git("init", "--bare", "--quiet")
        git("fetch", "--quiet", "--depth=1", "--no-tags", UPSTREAM, REVISION)
        fetched = git("rev-parse", "FETCH_HEAD^{commit}", capture_output=True).decode().strip()
        if fetched != REVISION:
            raise RuntimeError(f"Expected {REVISION}, fetched {fetched}")

        entries = git("ls-tree", "-rz", REVISION, "backend", "frontend", capture_output=True)
        paths = []
        for entry in entries.split(b"\0"):
            if not entry:
                continue
            metadata, name = entry.decode().split("\t", 1)
            mode = metadata.split()[0]
            path = PurePosixPath(name)
            is_source = (
                path.parts[1:2] == ("src",)
                and path.suffix in SOURCE_SUFFIXES
                and all(not part.startswith(".") for part in path.parts)
            )
            if mode in {"100644", "100755"} and (is_source or name in MANIFESTS):
                paths.append(name)

        if not {"backend/package-lock.json", "frontend/package-lock.json"}.issubset(paths):
            raise RuntimeError("The snapshot is missing a dashboard dependency lock file")

        archive = Path(temporary) / "source.tar"
        git("archive", "-o", str(archive), REVISION, "--", *paths)
        destination.mkdir()
        with tarfile.open(archive) as source:
            source.extractall(destination, filter="data")

    print(f"Historical dashboard {fetched} exported to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New directory for the dashboard source")
    prepare(parser.parse_args().destination)
