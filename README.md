# QNX Runcheck

Build a C file for QNX 8, check the VM's OS and architecture, copy the executable to a temporary directory, then run it and report the stage that failed. The default program prints the target identity and monotonic clock.

**Verification status:** Host unit tests and loopback SSH transport have been exercised with fixtures. The licensed QNX 8 QEMU run is pending.

## Run the check

1. Obtain and deploy a [non-commercial QNX SDP 8.0 license](https://www.qnx.com/getqnx). In QNX Software Center, install the SDK and the `com.qnx.qnx800.quickstart.qemu` image package. Unpack the image, source `qnxsdp-env.sh`, and start the guest with `mkqnximage --run` from the image directory. Launch one of the official demos and confirm it starts. See the [official QEMU image guide](https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti_qemu/getting_started.html).
2. Configure key-based SSH access to your own VM. Verify its host key from the VM console and add it to your known-hosts file. The tool uses your existing SSH key or agent and known-host configuration, with password prompts disabled. To use separate test credentials, pass `--identity-file` and `--known-hosts`.
3. Source the SDP environment in your shell and run `python3 runcheck.py --target user@127.0.0.1 --port 2222` from this directory. Set the port to the actual SSH port for your VM and use `--arch aarch64` when applicable.

To check failures, pass a C file with an intentional syntax error, then reuse the valid probe after stopping the test VM. Exit codes indicate the failed stage: build (10), SSH or target identity (20), workspace or upload (30), and target process (40).

The executable is streamed through the authenticated SSH connection. The guest needs SSH, a POSIX shell, `uname`, the QNX toybox `mktemp`, and the standard `cat`, `chmod`, `rm`, and `rmdir` utilities.

## Verify a clean checkout

Run `python3 -m unittest -v` with Python 3.10 or later. The host unit tests simulate the compiler and SSH responses, including a failed upload that still removes its temporary directory.

For real target evidence, record the QNX guest's OS and architecture, the QEMU version and the compiler's `qcc -V` output. Use the same SSH target and verified host key for all three checks:

| Scenario | Expected result |
| --- | --- |
| Guest running, included `target_probe.c` | Build, target, workspace, copy and run succeed. Probe prints `Target:` and `Monotonic clock:`. Exit 0. |
| Guest running, `printf 'int main( {\n' > /tmp/qnx-runcheck-invalid.c` and pass that file as the positional argument | qcc reports a compile error before any SSH step. Exit 10. |
| Test guest fully stopped, included probe | Build succeeds, then SSH reports that it cannot connect to the guest. Exit 20. |

Run the failure cases on a disposable test guest. The MIT license covers Runcheck's source files. Install the QNX SDK and target image separately under your QNX license.
