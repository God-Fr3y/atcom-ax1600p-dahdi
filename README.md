# ATCOM AX1600P / AX800P — Patched DAHDI Driver for Issabel 4 / CentOS 7

Kernel: `3.10.0-xxxx.el7.x86_64`

---

## What Is This?

This repository contains the **pre-patched** Atcom DAHDI 2.6.1 driver source
for the ATCOM AX1600P and AX800P FXO telephony cards, ready to compile on
Issabel 4 / CentOS 7 running kernel 3.10.

The official Atcom DAHDI 2.6.1 source was written for older kernels and fails
to compile on kernel 3.10 without modifications. All required patches have
already been applied to the source in this repository — just clone, compile,
and install. No downloading from Atcom's website required.

---

## Compatible Hardware

| Card Model    | PCI Chipset       | PCI Subsystem ID |
|---------------|-------------------|------------------|
| ATCOM AX1600P | Tiger Jet TJ3XX   | b700:0003        |
| ATCOM AX800P  | Tiger Jet TJ3XX   | b700:0003        |

Verify your card is detected before installing:
```bash
lspci -nn | grep -i tiger
# Expected:
# XX:XX.X Communication controller: Tiger Jet Network Inc. Tiger3XX [e159:0001]
#     Subsystem: Device b700:0003
```

---

## Tested Environment

| Component   | Version                        |
|-------------|--------------------------------|
| OS          | Issabel 4 (CentOS 7)           |
| Kernel      | 3.10.0-1062.el7.x86_64         |
| Asterisk    | 16.7.0                         |
| DAHDI       | 2.6.1 (Atcom custom build)     |
| Echo Cancel | MG2                            |

---

## Patches Applied

The following changes were made to the original Atcom DAHDI 2.6.1 source
to make it compile on kernel 3.10:

1. **dahdi-base.c** — `PDE(inode)->data` → `PDE_DATA(inode)`
2. **dahdi-base.c** — `create_proc_entry()` → `proc_create_data()` with updated signature
3. **dahdi-base.c** — `proc_create_data` multi-line argument restructure
4. **Kbuild** — Removed `dahdi_dynamic_ethmf` (uses removed proc API)
5. **xpp/Kbuild** — Disabled Xorcom USB module (not needed for FXO cards)
6. **All driver .c/.h files** — Added `__devinit`/`__devexit` compat macros
   (these were removed in kernel 3.10; affects ax1600p.c and other drivers)

---

## Installation

### Step 1 — Install build dependencies
```bash
sudo yum install -y gcc make perl kernel-devel-$(uname -r) kernel-headers
```

### Step 2 — Clone this repo
```bash
git clone https://github.com/God-Fr3y/atcom-ax1600p-dahdi.git
cd atcom-ax1600p-dahdi
```

### Step 3 — Stop services and unload old modules
```bash
sudo asterisk -rx "core stop now" 2>/dev/null || true
sudo service dahdi stop 2>/dev/null || true

for mod in opvxa1200 opvxd115 opvxa24xx wctdm fxo200m d100m oct612x \
           ax1600p dahdi_echocan_mg2 dahdi_echocan_oslec dahdi; do
    sudo rmmod "$mod" 2>/dev/null || true
done
```

### Step 4 — Remove old conflicting DAHDI modules
```bash
sudo rm -f /lib/modules/$(uname -r)/extra/dahdi*.ko.xz
sudo depmod -a
```

### Step 5 — Compile and install
```bash
sudo make all
sudo make install
sudo make config
```

### Step 6 — Configure echo canceller
```bash
sudo sed -i 's/echocanceller=oslec/echocanceller=mg2/g' /etc/dahdi/system.conf
```

### Step 7 — Set modules to load at boot
```bash
cat << 'MODEOF' | sudo tee /etc/modules-load.d/dahdi.conf
dahdi
ax1600p
dahdi_echocan_mg2
MODEOF
```

### Step 8 — Load modules and start services
```bash
sudo depmod -a
sudo modprobe dahdi
sudo modprobe ax1600p
sudo modprobe dahdi_echocan_mg2
sudo dahdi_genconf
sudo sed -i 's/echocanceller=oslec/echocanceller=mg2/g' /etc/dahdi/system.conf
sudo dahdi_cfg -v
sudo systemctl enable dahdi
sudo service dahdi start
sudo service asterisk restart
```

### Step 9 — Verify
```bash
lsmod | grep -E "dahdi|ax1600"
sudo -u asterisk asterisk -rx "dahdi show channels"
sudo -u asterisk asterisk -rx "dahdi show status"
```

---

## Expected Output After Successful Install
```
# lsmod | grep -E "dahdi|ax1600"
ax1600p             49863  0
dahdi              220358  2 ax1600p,dahdi_echocan_mg2
crc_ccitt           12707  1 dahdi

# asterisk -rx "dahdi show channels"
   Chan  Context    MOH       Blocked   In Service
      1  from-pstn  default             Y
      2  from-pstn  default             Yes
    ...
     16  from-pstn  de
```

---

## Troubleshooting

**"Invalid argument" when loading ax1600p**
Old DAHDI module conflict. Run:
```bash
rmmod dahdi
find /lib/modules/$(uname -r)/extra -name "dahdi*.ko.xz" -delete
depmod -a
modprobe dahdi && modprobe ax1600p
```

**"dahdi_hardware" shows nothing**
Normal for Tiger Jet cards. Use `dahdi_scan` instead.

**RED alarms on channels**
Normal — RED alarm means no active PSTN line connected on that port.

**Build fails after kernel update**
Recompile: run `make all && make install` again from the repo directory.
The `kernel-devel` package must match your running kernel exactly.

---

## Repository Structure
```
atcom-ax1600p-dahdi/
├── linux/drivers/dahdi/     # Patched DAHDI kernel driver source
│   ├── ax1600p.c            # Main AX1600P driver (patched)
│   ├── dahdi-base.c         # Core DAHDI base (patched)
│   └── Kbuild               # Build config (ethmf removed)
├── tools/                   # DAHDI userspace tools
├── Makefile                 # Top-level build file
└── README.md                # This file
```

---

## Branch Plan

| Branch    | Target OS         | Kernel | Status      |
|-----------|-------------------|--------|-------------|
| `main`    | Issabel 4 / CentOS 7 | 3.10 | ✅ Working |
| `issabel5`| Issabel 5 / CentOS 8 | 4.18 | 🔜 Planned  |
| `issabel6`| Issabel 6         | TBD    | 🔜 Planned  |

---

## Credits

- Original DAHDI driver source: ATCOM (www.atcom.cn)
- Kernel 3.10 compatibility patches: Godfrey Padua
- Tested on: Issabel 4, Asterisk 16.7.0, Kernel 3.10.0-1062.el7.x86_64
- Tested on: Issabel 4, Asterisk 16.7.0, Kernel 3.10.0-1160.119.1.el7.x86_64
---

## License

Patches and documentation in this repository are provided freely for
community use. The DAHDI source code is licensed under GPL v2.
EOF
