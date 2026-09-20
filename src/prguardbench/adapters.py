"""JSON stdin/stdout command bridge. Running a wrapper is an explicit trust decision."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from .models import Prediction, ReviewCase, ValidationError, canonical_json

MAX_OUTPUT = 1_000_000


def command_prediction(case: ReviewCase, command: list[str], timeout: float = 60,
                       pass_env: tuple[str, ...] = ()) -> Prediction:
    if not command or not all(isinstance(x, str) and x for x in command):
        raise ValidationError("Command must be a nonempty JSON argv array; no shell strings")
    if not 0 < timeout <= 3600:
        raise ValidationError("Timeout must be in (0, 3600]")
    env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR", "LANG") if k in os.environ}
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    for key in pass_env:
        if key not in os.environ:
            raise ValidationError(f"Requested environment variable is not set: {key}")
        env[key] = os.environ[key]
    request = {"schema": "prguardbench.adapter.v1", "case": case.to_dict()}
    # Labels, rationales and benchmark-family metadata are deliberately excluded.
    with tempfile.TemporaryDirectory(prefix="prguardbench-adapter-") as temp:
        temp_path = Path(temp)
        inp = temp_path / "request.json"
        inp.write_text(canonical_json(request), encoding="utf-8")
        with inp.open("rb") as stdin, (temp_path / "out").open("w+b") as stdout, (temp_path / "err").open("w+b") as stderr:
            try:
                proc = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr,
                                        cwd=temp, env=env, shell=False,
                                        start_new_session=(os.name == "posix"))
            except OSError as exc:
                return Prediction(case.case_id, "error", note=f"Wrapper launch failed ({type(exc).__name__}).")
            started = time.monotonic()
            failure = None
            while proc.poll() is None:
                if time.monotonic() - started > timeout:
                    failure = "Wrapper timed out."
                    break
                if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > MAX_OUTPUT:
                    failure = "Wrapper output exceeded the limit."
                    break
                time.sleep(0.01)
            if failure:
                if os.name == "posix":
                    import signal
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                proc.wait()
                return Prediction(case.case_id, "error", note=failure)
            if proc.returncode:
                # Do not echo stderr, which may contain user-supplied credentials.
                return Prediction(case.case_id, "error", note=f"Wrapper exited with code {proc.returncode}.")
            stdout.seek(0)
            payload = stdout.read(MAX_OUTPUT + 1)
            if len(payload) > MAX_OUTPUT:
                return Prediction(case.case_id, "error", note="Wrapper output exceeded the limit.")
    try:
        result = Prediction.from_dict(json.loads(payload))
        if result.case_id != case.case_id:
            raise ValidationError("Wrapper returned the wrong case ID")
        return result
    except (ValidationError, ValueError, UnicodeDecodeError):
        return Prediction(case.case_id, "error", note="Wrapper returned invalid JSON or violated the prediction contract.")
