"""Build a QNX 8 executable and verify it on a trusted QNX target."""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def step(label, command, timeout, failure, *, report_success=True, stdin=None):
    try:
        process = subprocess.run(command, stdin=stdin, capture_output=True, text=True,
                                 errors="replace", timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"[{label}] {error}", file=sys.stderr)
        raise SystemExit(failure) from error
    if process.returncode:
        diagnostic = process.stderr.strip() or process.stdout.strip()
        print(f"[{label}] Exit {process.returncode}: {diagnostic}", file=sys.stderr)
        raise SystemExit(failure)
    if report_success:
        if process.stdout:
            print(process.stdout.strip(), flush=True)
        print(f"[{label}] OK", flush=True)
    return process.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=Path(__file__).with_name("target_probe.c"))
    parser.add_argument("--target", required=True, help="SSH user@host for the QNX VM")
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--arch", choices=("x86_64", "aarch64"), default="x86_64")
    parser.add_argument("--identity-file", type=Path, help="SSH private key for the test VM")
    parser.add_argument("--known-hosts", type=Path, help="Known hosts file containing the verified VM host key")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]*@[a-zA-Z0-9][a-zA-Z0-9.-]*", args.target):
        parser.error("Target must be user@hostname or user@IPv4.")
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535.")
    source = args.source.resolve()
    profile = "gcc_ntox86_64" if args.arch == "x86_64" else "gcc_ntoaarch64le"
    ssh = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
           "-o", "StrictHostKeyChecking=yes", "-p", str(args.port)]
    if args.identity_file:
        ssh.extend(["-o", "IdentitiesOnly=yes", "-i", str(args.identity_file.resolve())])
    if args.known_hosts:
        hosts_path = args.known_hosts.resolve().as_posix()
        if any(char in hosts_path for char in ('"', "\\", "\n", "\r")):
            parser.error("Known hosts path cannot contain quotes, backslashes or line breaks.")
        ssh.extend(["-o", f'UserKnownHostsFile="{hosts_path}"'])
    ssh.append(args.target)
    with tempfile.TemporaryDirectory(prefix="qnx-runcheck-") as directory:
        executable = Path(directory) / "probe"
        step("build", ["qcc", f"-V{profile}", "-Wall", "-Wextra", str(source), "-o", str(executable)],
             60, 10)
        identity = step("target", [*ssh, "uname -s && uname -r && uname -p"], 12, 20, report_success=False)
        identity_lines = identity.splitlines()
        machine_names = {"x86_64": {"x86_64", "amd64"}, "aarch64": {"aarch64", "aarch64le", "arm64"}}
        if (len(identity_lines) != 3 or identity_lines[0] != "QNX"
                or not re.match(r"^8(?:\.|$)", identity_lines[1])
                or identity_lines[2] not in machine_names[args.arch]):
            print(f"[target] Expected QNX 8 on {args.arch}. Received: {identity!r}", file=sys.stderr)
            return 20
        print(f"[target] OK {' '.join(identity_lines)}", flush=True)
        # The login shell creates the executable in a unique, private directory on the VM.
        remote_dir = step("workspace", [*ssh, "umask 077; mktemp -d /tmp/qnx-runcheck.XXXXXXXX"],
                          12, 30, report_success=False)
        if not re.fullmatch(r"/tmp/qnx-runcheck\.[a-zA-Z0-9]+", remote_dir):
            print("[workspace] Unexpected temporary directory path.", file=sys.stderr)
            return 30
        print("[workspace] OK", flush=True)
        remote_exe = f"{remote_dir}/probe"
        try:
            try:
                with executable.open("rb") as binary:
                    step("copy", [*ssh, f"umask 077; cat > {remote_exe}"], 20, 30, stdin=binary)
            except OSError as error:
                print(f"[copy] Could not read the built executable: {error}", file=sys.stderr)
                return 30
            step("run", [*ssh, f"chmod 700 {remote_exe} && {remote_exe}"], 20, 40)
        finally:
            try:
                cleanup = subprocess.run([*ssh, f"rm -f {remote_exe} && rmdir {remote_dir}"],
                                         capture_output=True, timeout=12, check=False)
                if cleanup.returncode:
                    print(f"[cleanup] Check {remote_dir} on the target.", file=sys.stderr)
            except (OSError, subprocess.TimeoutExpired):
                print(f"[cleanup] Check {remote_dir} on the target.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
