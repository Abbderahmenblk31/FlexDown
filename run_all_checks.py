import os
import pathlib
import subprocess
import time


def run_cmd(cmd):
    """Run a shell command and return (returncode, output)."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return result.returncode, result.stdout + result.stderr


def main():
    steps = []
    # 1. Unit tests
    rc, out = run_cmd("pytest -q")
    steps.append(("Pytest", rc, out))

    # 2. Linting (flake8)
    rc, out = run_cmd("flake8 .")
    steps.append(("Flake8", rc, out))

    # 3. Type checking (mypy)
    mypy_cmd = (
        "mypy --ignore-missing-imports --exclude \"(dist|_internal)\" "
        "--disable-error-code union-attr --disable-error-code override "
        "--disable-error-code attr-defined flexdown"
    )
    rc, out = run_cmd(mypy_cmd)
    steps.append(("Mypy", rc, out))

    # 4. Security analysis (bandit)
    rc, out = run_cmd("bandit -r flexdown -x dist,_internal -ll")
    steps.append(("Bandit", rc, out))

    # 5. Dependency audit (pip-audit on project requirements)
    rc, out = run_cmd("pip-audit -r requirements.txt")
    steps.append(("Pip-audit", rc, out))

    # 6. Performance download test
    url = "https://proof.ovh.net/files/10Mb.dat"
    tmp_file = pathlib.Path("performance_test.bin")
    start = time.time()
    ps_cmd = f'powershell -Command "Invoke-WebRequest -Uri {url} -OutFile {tmp_file} -UseBasicParsing"'
    rc, out = run_cmd(ps_cmd)
    duration = time.time() - start
    if tmp_file.exists():
        size_mb = tmp_file.stat().st_size / (1024 * 1024)
        speed_mb_s = size_mb / duration if duration > 0 else 0
        perf_msg = f"Downloaded {size_mb:.2f} MiB in {duration:.2f}s -> {speed_mb_s:.2f} MiB/s"
        try:
            tmp_file.unlink()
        except OSError:
            pass
    else:
        perf_msg = f"Download failed (rc={rc}). Output: {out}"
    steps.append(("Download-Performance", rc, perf_msg))

    # 7. Generate markdown report
    report_path = pathlib.Path("evaluation_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Full Evaluation Report\n\n")
        for name, rc, details in steps:
            status = "PASS" if rc == 0 else "FAIL"
            f.write(f"## {name}: {status}\n```\n{details}\n```\n\n")
        passes = sum(1 for _, rc, _ in steps if rc == 0)
        total = len(steps)
        grade = "A" if passes == total else ("B" if passes >= total * 0.8 else ("C" if passes >= total * 0.6 else "F"))
        f.write(f"**Overall grade:** {grade} ({passes}/{total} passed)\n")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
