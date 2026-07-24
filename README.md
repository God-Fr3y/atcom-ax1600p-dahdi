# ATCOM AX1600P / AX800P — Patched DAHDI Driver for Issabel 5 / Rocky Linux 8

**Kernel:** `4.18.0-xxx.el8.x86_64`

---

## What Is This?

This repository contains the **pre-patched** DAHDI 2.11.1 source with the
ATCOM AX1600P/AX800P driver built-in, ready to compile on Issabel 5 /
Rocky Linux 8 running kernel 4.18.

The ATCOM ax1600p driver was originally written for DAHDI 2.6.1 and fails to
compile or work with DAHDI 2.11.1 (shipped with Issabel 5) without
modifications. All required patches have already been applied — just clone,
compile, and install.

---

## Compatible Hardware

| Card Model    | PCI Chipset       | PCI Subsystem ID |
|---------------|-------------------|-------------------|
| ATCOM AX1600P | Tiger Jet TJ3XX   | `b700:0003`       |
| ATCOM AX800P  | Tiger Jet TJ3XX   | `b700:0003`       |

Verify your card is detected before installing:

```bash
lspci -nn | grep -i tiger
# Expected output:
# XX:XX.X Communication controller: Tiger Jet Network Inc. Tiger3XX [e159:0001]
#     Subsystem: Device b700:0003
```

---

## Tested Environment

| Component   | Version                                   |
|--------------|--------------------------------------------|
| OS           | Issabel 5 (Rocky Linux 8)                   |
| Kernel       | 4.18.0-553.144.1.el8_10.x86_64              |
| Asterisk     | 18.19.0                                     |
| DAHDI        | 2.11.1 (with ax1600p built-in)              |
| Echo Cancel  | MG2                                         |


## Installation

### Step 1 — Install build dependencies

```bash
sudo yum update && sudo dnf install -y git gcc make kernel-devel-$(uname -r)
```

### Step 2 — Clone and checkout the Issabel 5 branch

```bash
git clone https://github.com/God-Fr3y/atcom-ax1600p-dahdi.git
cd atcom-ax1600p-dahdi
git checkout issabel5
```

### Step 3 — Stop services and unload old modules

```bash
sudo systemctl stop asterisk
sudo rmmod ax1600p dahdi_echocan_mg2 dahdi 2>/dev/null || true
```

### Step 4 — Build and install

```bash
make
sudo make install
sudo depmod -a
```

### Step 5 — Configure auto-assign spans and udev permissions

```bash
echo 'options dahdi auto_assign_spans=1' | sudo tee /etc/modprobe.d/dahdi.conf

sudo tee /etc/udev/rules.d/99-dahdi.rules << 'EOF'
SUBSYSTEM=="dahdi", OWNER="asterisk", GROUP="asterisk", MODE="0660"
EOF
```

### Step 6 — Load modules and create a persistent DAHDI configure service

Loading modules manually and running `dahdi_genconf`/`dahdi_cfg` by hand
works for the current session, but **does not survive a reboot** — on
Issabel 5 the DAHDI kernel modules and Asterisk's own systemd unit start in
an unpredictable order, so channels may come up empty or Asterisk may
crash-loop after a restart. A dedicated systemd unit fixes this permanently.

```bash
sudo tee /etc/modules-load.d/dahdi.conf << 'EOF'
dahdi
dahdi_echocan_mg2
ax1600p
EOF
```

Create `/etc/systemd/system/dahdi-cfg.service`:

```bash
sudo tee /etc/systemd/system/dahdi-cfg.service << 'EOF'
[Unit]
Description=DAHDI configure
After=systemd-modules-load.service network.target
Requires=systemd-modules-load.service
Before=asterisk.service

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 5
ExecStartPre=/sbin/dahdi_genconf
ExecStartPre=/bin/sed -i 's/echocanceller=oslec/echocanceller=mg2/g' /etc/dahdi/system.conf
ExecStart=/sbin/dahdi_cfg
ExecStartPost=/bin/chown -R asterisk:asterisk /dev/dahdi
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable dahdi-cfg.service
```

The `sleep 5` gives the Tiger Jet chipset time to fully enumerate all spans
over PCI before `dahdi_genconf` runs — without it, `system.conf` can be
generated empty on a cold boot. `Before=asterisk.service` guarantees DAHDI
is fully configured before Asterisk starts, with no need for a
`Requires=` in the other direction (a hard `Requires=` dependency on
`dahdi-cfg.service` from Asterisk's own unit can cause Asterisk to refuse
to start at all if this service is ever delayed — avoid adding one).

### Step 7 — Fix Asterisk's systemd unit and verify

Issabel 5's default `asterisk.service` can ship with (or accumulate through
prior manual edits) a broken `ExecStart` path that fails silently on every
boot with `status=1/FAILURE` in a restart loop. Check it first:

```bash
systemctl cat asterisk
```

If `ExecStart`/`ExecReload` don't read exactly as below, fix them:

```bash
sudo systemctl edit --full asterisk.service
```

```ini
ExecStart=/usr/sbin/asterisk -U asterisk -G asterisk -mqf -C /etc/asterisk/asterisk.conf
ExecReload=/usr/sbin/asterisk -rx 'core reload'
```

Then enable everything and reboot to confirm it all comes up clean:

```bash
echo '#include dahdi-channels.conf' | sudo tee -a /etc/asterisk/chan_dahdi.conf
sudo systemctl daemon-reload
sudo systemctl enable asterisk
sudo reboot
```

After reboot, verify:

```bash
sudo asterisk -rx "dahdi show channels"
sudo asterisk -rx "core show channels"
```

You should see all physical FXO channels listed as `In Service` under
`from-pstn`, and Asterisk running without restarts (`systemctl status
asterisk` should show a single `active (running)` start, not a rising
`restart counter`).

## Expected Output After Successful Install

Check loaded modules:

```bash
$ lsmod | grep -E "dahdi|ax1600"
ax1600p             86016  0
dahdi_echocan_mg2    16384  0
dahdi               253952  2 ax1600p,dahdi_echocan_mg2
```

Check channels in Asterisk:

```
$ sudo asterisk -rx "dahdi show channels"
   Chan Extension       Context         Language   MOH Interpret        Blocked    In Service
 pseudo                 default                    default                         Yes
      1                 from-pstn                  default                         Yes
      2                 from-pstn                  default                         Yes
      3                 from-pstn                  default                         Yes
    ...
     16                 from-pstn                  default                         Yes
```

Check DAHDI span status:

```
$ cat /proc/dahdi/1
Span 1:  "" (MASTER)
           1 WCTDM/16/0 FXSKS (In use) RED
           2 WCTDM/16/1 FXSKS (In use)
           3 WCTDM/16/2 FXSKS (In use) RED
    ...
```

---

## Next Steps in Issabel Web GUI

1. **PBX → Trunks → Add DAHDI Trunk**
   - Identifier: `g0`
2. **PBX → Outbound Routes**
   - Pattern: `9|.`
   - Trunk: `DAHDI/g0`
3. Configure extensions and softphones as normal

---

## Troubleshooting

**"dahdi_rec: Invalid argument" when making calls**

DAHDI version mismatch between kernel modules and Asterisk's chan_dahdi.
Re-run the full installation from Step 3:

```bash
sudo systemctl stop asterisk
sudo rmmod ax1600p dahdi_echocan_mg2 dahdi 2>/dev/null || true
make && sudo make install && sudo depmod -a
sudo modprobe dahdi && sudo modprobe dahdi_echocan_mg2 && sudo modprobe ax1600p
sudo dahdi_cfg -vvv && sudo dahdi_genconf
sudo systemctl start asterisk
```

**No channels in Asterisk (only "pseudo")**

```bash
sudo dahdi_cfg -vvv
sudo dahdi_genconf
sudo systemctl restart asterisk
```

**"Unable to open /dev/dahdi/ctl: Permission denied"**

```bash
sudo chown -R asterisk:asterisk /dev/dahdi
sudo udevadm control --reload-rules
```

**"Timeout waiting for all spans to be assigned"**

```bash
sudo rmmod ax1600p dahdi_echocan_mg2 dahdi
sudo modprobe dahdi auto_assign_spans=1
sudo modprobe dahdi_echocan_mg2
sudo modprobe ax1600p
```

**RED alarms on channels**

Normal — RED alarm means no active PSTN line connected on that port.

**No audio on calls via VPN**

Ensure the Issabel server can reach the VPN client network:

```bash
# Add route (example: VPN network 10.8.0.0/24 via VPN server 10.61.16.7)
sudo ip route add 10.8.0.0/24 via 10.61.16.7

# Make permanent
echo '10.8.0.0/24 via 10.61.16.7' | sudo tee /etc/sysconfig/network-scripts/route-eth0
```

**Build fails after kernel update**

```bash
sudo dnf install -y kernel-devel-$(uname -r)
make clean && make && sudo make install
```

---

## Repository Structure

```
atcom-ax1600p-dahdi/
├── linux/
│   ├── drivers/dahdi/       # DAHDI 2.11.1 kernel driver source
│   │   ├── ax1600p.c        # ATCOM AX1600P driver (patched)
│   │   ├── dahdi-base.c     # Core DAHDI base (patched for kernel 4.18)
│   │   └── Kbuild           # Build config (ax1600p added)
│   └── include/dahdi/       # DAHDI kernel headers (patched for kernel 4.18)
├── tools/                   # DAHDI userspace tools
├── Makefile                 # Top-level build file
└── README.md                # This file
```

---

## Branch Plan

| Branch     | Target OS                  | DAHDI  | Kernel | Status      |
|------------|------------------------------|--------|--------|-------------|
| `main`     | Issabel 4 / CentOS 7          | 2.6.1  | 3.10   | ✅ Working  |
| `issabel5` | Issabel 5 / Rocky Linux 8     | 2.11.1 | 4.18   | ✅ Working  |
| `issabel6` | Issabel 6                     | TBD    | TBD    | 🔜 Planned  |

---

## Credits

- Original DAHDI driver source: ATCOM
- Original DAHDI Linux source: Digium / Sangoma
- Tested on: Issabel 5, Asterisk 18.19.0, Kernel 4.18.0-553.144.1.el8_10.x86_64
- Tested with: ATCOM AX1600P (14 FXO modules)

---

## License

The DAHDI source code is licensed under GPL v2. Patches and documentation
in this repository are provided freely for community use.
