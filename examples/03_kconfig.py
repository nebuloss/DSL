"""
Kconfig generation: all Kconfig DSL features.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dsl import kconfig as kc

# ── Helpers ──────────────────────────────────────────────────────────────────

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)

# ── Variables and constants ──────────────────────────────────────────────────

section("Leaf types: KVar, KBool, KInt, KHex, KString, KNull")
print("KVar('MY_FLAG')     :", kc.KVar("MY_FLAG"))
print("KVar('my.flag')     :", kc.KVar("my.flag"))  # dots → underscores, uppercase
print("KBool(True)         :", kc.KBool(True))
print("KBool('y')          :", kc.KBool("y"))
print("KBool('n')          :", kc.KBool("n"))
print("KInt(42)            :", kc.KInt(42))
print("KHex(0xFF00)        :", kc.KHex(0xFF00))
print("KHex('0x1000')      :", kc.KHex("0x1000"))
print("KString('hello')    :", kc.KString("hello"))
print("KNull()             :", kc.KNull())
print("kNULL singleton     :", kc.kNULL is kc.KNull())

section("Boolean expressions: KAnd, KOr, KNot and simplification")
A = kc.KVar("ARCH_ARM")
B = kc.KVar("HAVE_MMU")
C = kc.KVar("SMP")

print("A && B              :", A & B)
print("A || B              :", A | B)
print("!A                  :", ~A)
print("!(A && B)           :", ~(A & B))    # De Morgan => !A || !B
print("!(A || B)           :", ~(A | B))    # De Morgan => !A && !B
print("A && true           :", A & kc.KBool.true())   # => A
print("A || false          :", A | kc.KBool.false())  # => A
print("A && A              :", A & A)       # idempotent => A
print("A && ~A             :", A & ~A)      # contradiction => n
print("A || ~A             :", A | ~A)      # tautology => y

section("any_of / all_of helpers")
print("any_of(A,B,C)       :", kc.any_of(A, B, C))
print("all_of(A,B,C)       :", kc.all_of(A, B, C))

# ── Simple top-level elements ─────────────────────────────────────────────────

section("KSource and KComment")
print(kc.KSource("arch/arm/Kconfig"))
print(kc.KComment("This is a Kconfig comment"))

# ── KOption variants ──────────────────────────────────────────────────────────

section("KOptionBool — bool option with all attributes")
opt_bool = (
    kc.KOptionBool(kc.KVar("MY_DRIVER"), "Enable My Driver")
    .add_depends(kc.KVar("HAS_HARDWARE"))
    .add_depends(A & B)
    .add_selects(kc.KVar("DRIVER_CORE"), kc.KVar("DMA_ENGINE"))
    .add_default(kc.KBool.true(), when=kc.KVar("BOARD_DEFAULT"))
    .add_default(kc.KBool.false())
    .add_help(
        "Enable the My Driver subsystem.",
        "",
        "This driver requires HAS_HARDWARE and MMU support.",
        "It will auto-select DRIVER_CORE and DMA_ENGINE.",
    )
)
print(opt_bool)

section("KOptionString — string option")
opt_str = (
    kc.KOptionString(kc.KVar("CMDLINE"), "Default kernel command line")
    .add_default(kc.KString("console=ttyS0,115200"))
    .add_depends(kc.KVar("CMDLINE_OVERRIDE"))
    .add_help("Extra arguments appended to the boot command line.")
)
print(opt_str)

section("KOptionInt — int option with range")
opt_int = (
    kc.KOptionInt(kc.KVar("NR_CPUS"), "Maximum number of CPUs")
    .add_range(kc.KInt(1), kc.KInt(512))
    .add_default(kc.KInt(8))
    .add_help("Set the upper limit for SMP CPU count.")
)
print(opt_int)

section("KOptionHex — hex option with conditional range")
opt_hex = (
    kc.KOptionHex(kc.KVar("PHYS_OFFSET"), "Physical memory base address")
    .add_range(kc.KHex("0x0"), kc.KHex("0xFFFFFFFF"))
    .add_default(kc.KHex("0x80000000"), when=kc.KVar("ARCH_ARM"))
    .add_default(kc.KHex("0x0"))
    .add_help("Base address of physical RAM as seen from the CPU.")
)
print(opt_hex)

section("KMenuConfig — menuconfig entry")
mc = (
    kc.KMenuConfig(kc.KVar("NETWORKING"), "Networking support")
    .add_help("Enable the full networking stack.")
)
print(mc)

# ── KMenu ─────────────────────────────────────────────────────────────────────

section("KMenu — menu block")
menu = kc.KMenu(
    "Memory management options",
    kc.KOptionBool(kc.KVar("MMU"), "MMU-based memory management").add_help("Enable the MMU."),
    kc.KOptionBool(kc.KVar("SPARSEMEM"), "Sparse memory model")
        .add_depends(kc.KVar("MMU"))
        .add_help("Use the sparse memory model for discontiguous RAM."),
    kc.KOptionInt(kc.KVar("PAGE_SHIFT"), "Page size (log2)")
        .add_range(kc.KInt(12), kc.KInt(16))
        .add_default(kc.KInt(12)),
)
print(menu)

# ── KIf ───────────────────────────────────────────────────────────────────────

section("KIf — conditional block")
kif = kc.KIf(
    kc.KVar("ARCH_ARM") & kc.KVar("HAVE_MMU"),
    kc.KOptionBool(kc.KVar("ARM_LPAE"), "Large Physical Address Extension"),
    kc.KOptionBool(kc.KVar("ARM_PTE_AF"), "Access flag support"),
)
print(kif)

# ── KChoice ───────────────────────────────────────────────────────────────────

section("KChoice — exclusive selection block")
choice = kc.KChoice(
    "Kernel compression format",
    kc.KOptionBool(kc.KVar("KERNEL_GZIP"), "Gzip").add_help("Compress the kernel with gzip."),
    kc.KOptionBool(kc.KVar("KERNEL_LZ4"), "LZ4").add_help("Compress the kernel with lz4 (fast)."),
    kc.KOptionBool(kc.KVar("KERNEL_ZSTD"), "Zstd").add_help("Compress the kernel with zstd."),
)
print(choice)

# ── Full KConfig ──────────────────────────────────────────────────────────────

section("Full Kconfig example — realistic kernel-style config")
cfg = kc.KConfig(
    kc.KComment("Main Kconfig — generated by DSL"),
    kc.KSource("arch/$(ARCH)/Kconfig"),

    kc.KMenu(
        "General setup",
        kc.KOptionString(kc.KVar("LOCALVERSION"), "Local version suffix")
            .add_default(kc.KString(""))
            .add_help("Append an extra string to the end of the kernel version."),
        kc.KOptionBool(kc.KVar("SWAP"), "Support for paging of anonymous memory")
            .add_help("Enable swap space support."),
        kc.KOptionInt(kc.KVar("HZ"), "Timer frequency")
            .add_range(kc.KInt(100), kc.KInt(1000))
            .add_default(kc.KInt(250), when=kc.KVar("HZ_250"))
            .add_default(kc.KInt(1000), when=kc.KVar("HZ_1000"))
            .add_default(kc.KInt(100))
            .add_help("The frequency of the timer interrupt."),
    ),

    kc.KMenu(
        "CPU features",
        kc.KMenuConfig(kc.KVar("SMP"), "Symmetric multi-processing support")
            .add_depends(kc.KVar("ARCH_SMP_POSSIBLE"))
            .add_help("Enable SMP kernel."),
        kc.KIf(kc.KVar("SMP"),
            kc.KOptionInt(kc.KVar("NR_CPUS"), "Maximum number of CPUs")
                .add_range(kc.KInt(2), kc.KInt(512))
                .add_default(kc.KInt(4))
                .add_help("Limit the maximum number of CPUs the kernel supports."),
        ),
        kc.KChoice(
            "Preemption model",
            kc.KOptionBool(kc.KVar("PREEMPT_NONE"), "No forced preemption"),
            kc.KOptionBool(kc.KVar("PREEMPT_VOLUNTARY"), "Voluntary kernel preemption"),
            kc.KOptionBool(kc.KVar("PREEMPT"), "Preemptible kernel"),
        ),
    ),

    kc.KMenu(
        "Device drivers",
        kc.KOptionBool(kc.KVar("NET"), "Networking support")
            .add_selects(kc.KVar("NET_CORE"))
            .add_help("Enable full network stack."),
        kc.KIf(kc.KVar("NET"),
            kc.KOptionBool(kc.KVar("INET"), "TCP/IP networking")
                .add_depends(kc.KVar("NET"))
                .add_help("Enable TCP/IP support."),
            kc.KOptionBool(kc.KVar("IPV6"), "IPv6 support")
                .add_depends(kc.KVar("INET"))
                .add_help("Enable IPv6 protocol support."),
        ),
    ),
)
print(cfg)
