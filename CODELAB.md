# Locate the first failing stage in a QNX 8 build-and-run

A C program that fails to appear on a QNX target may never have left the host. In this lab you run one small probe on your own QNX 8 QEMU guest, introduce a compiler error, and then take the guest offline. At each checkpoint, predict which stages can have run before checking the exit code.

## Prepare the host and guest

1. Start with Python 3.10+, Git, OpenSSH and a licensed QNX SDP 8.0 installation with the x86-64 compiler and the QEMU Quick Start Target Image. Use the [QNX deployment guide](https://www.qnx.com/developers/docs/qnxeverywhere/com.qnx.doc.target_images/topic/qsti_qemu/getting_started.html) to boot a disposable guest. Note the SSH user and the port forwarded to the guest. The commands below use a POSIX host shell with the SDP environment loaded.
2. On the guest console, check `uname -s`, `uname -r` and `uname -p`. This exercise expects QNX, release 8 and an x86-64 processor. Configure key-based SSH and verify the guest host key against the console. Use a test account that can create its own temporary working directory.
3. In your host shell, clone the project and enter it. Set `target` and `port` to your test guest. Check the QNX compiler and the SSH connection separately.

```sh
git clone https://github.com/LeeJinMing/qnx-runcheck
cd qnx-runcheck
target=user@127.0.0.1
port=2222
qcc -V
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -p "$port" "$target" uname -s
```

Look for the `gcc_ntox86_64` variant in your SDP installation and `QNX` in the SSH output. A different port, account, or key location may be required. The [project README](README.md) documents Windows SDP setup and the SSH client used in our Windows-host run.

## 1. Build, transfer and execute

```sh
python3 runcheck.py --target "$target" --port "$port"
echo "$?"
```

The host compiles [the probe](target_probe.c). The tool verifies the target identity, creates a temporary directory, streams the executable over SSH and runs it. In our official QNX 8.0.0 x86-64 QEMU guest, the output included:

```text
[build] OK
[target] OK QNX 8.0.0 x86_64
[workspace] OK
[copy] OK
Target: QNX 8.0.0 x86pc
Monotonic clock: 147.241950008 s
[run] OK
```

Exit code **0** confirms completion. Your clock value will differ. It measures the guest monotonic clock at the time of the probe.

## 2. Introduce a compiler error

```sh
bad_source=$(mktemp -d)
printf '%s\n' 'int main( {' > "$bad_source/invalid.c"
python3 runcheck.py "$bad_source/invalid.c" --target "$target" --port "$port"
echo "$?"
```

Expected result: a qcc diagnostic at `[build]` and exit code **10**. There is no target-stage output because execution stopped on the host. Fix the source or use the original probe before investigating SSH.

## 3. Separate an offline target from a failed build

Shut down only your disposable guest using its normal shutdown procedure. Confirm the forwarded port has closed. Leave the compiler environment intact and retry the original probe.

```sh
python3 runcheck.py --target "$target" --port "$port"
echo "$?"
```

In our run, `[build] OK` was followed by a target connection refusal and exit code **20**. The C file compiled successfully. Check the VM, port forwarding, account and verified SSH configuration before changing the program. Restart the guest and repeat checkpoint 1 to restore the working setup.

| First failing stage | Exit | What to inspect |
| --- | --- | --- |
| Build | 10 | qcc, compiler profile, source diagnostic |
| Target | 20 | Reachability, verified SSH identity, OS and architecture |
| Workspace or copy | 30 | Guest temporary directory, permissions and transfer |
| Run | 40 | Target program output and process status |

The three observed checkpoints used qcc 12.2.0, QEMU 8.2.2 and the official x86-64 image. The final two rows document other CLI outcomes. Compare your observations with the [recorded run](https://youtu.be/8iiXT4vnIQs) or the stage handling in [runcheck.py](runcheck.py).
