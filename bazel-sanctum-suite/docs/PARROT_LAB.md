# Parrot OS lab preflight

This workflow prepares and checks a **local Parrot Security ISO** for an operator-managed virtual machine. It does not download an image, install tools, create or start a VM/container, or connect to a target.

## Select and verify an image

Use the official [Parrot download page](https://parrotsec.org/download/) to choose the current edition and release. The official page lists Security, Home, HTB, IoT, and special editions; those choices and release artifacts may change. This repository deliberately does not hard-code a "latest" version, image digest, or edition as the latest.

1. Download the selected ISO and its checksum/signature material from the official Parrot source.
2. Independently verify the checksum/signature material using the method published by Parrot. Do not trust a checksum copied from an unrelated mirror or supplied alongside an untrusted image.
3. Run the preflight with the expected SHA-256 from that verified source:

```powershell
sanctum parrot-lab-preflight `
  --iso "C:\Lab\parrot-security.iso" `
  --sha256 "<64-hex-SHA-256-from-verified-official-manifest>" `
  --edition Security `
  --version "<exact-version-from-official-download>" `
  --architecture amd64
```

The command checks that the local file has an ISO9660 primary volume descriptor and that its SHA-256 matches the operator-supplied value. It reports the edition/version/architecture provided by the operator and an availability-only tool inventory for the **host running the command**. It does not inspect packages inside the ISO. A matching hash proves equality with the supplied value; the command cannot establish that the value itself came from Parrot or that the publisher signature was independently verified. A successful result remains `CHECKSUM_MATCHED_PENDING_AUTHENTICITY_REVIEW` for that reason.

## Isolate the virtual machine

Create and operate the VM outside SANCTUM-SUITE. Before booting:

- Use a disposable VM and retain a clean snapshot.
- Disable bridged networking. Prefer no virtual network adapter; if a network is essential, use a dedicated isolated segment with no route to production or the public Internet.
- Disable shared folders, shared clipboard, drag-and-drop, USB passthrough, and host integration.
- Do not mount host credentials, production data, or sensitive evidence.
- Use synthetic targets/data for training. For any active testing, obtain written authorization and constrain the targets at the VM/network boundary.
- Record the ISO checksum provenance, VM configuration, operator, authorization scope, and snapshot identifier.

The checklist printed by the preflight is guidance, not an enforced sandbox or proof of isolation. Do not treat a VM or container as a security boundary without validating the hypervisor, its configuration, and host controls.

## Tool inventory and capability boundary

The report lists whether selected executable names are discoverable on the host. It does not execute or version those tools, establish that they are included in the Parrot image, or assess their safety or suitability. Check installed tools and versions from inside the isolated VM using the operating system's package manager and trusted package metadata.

The existing Parrot engine and container orchestrator remain non-executing: they do not run reconnaissance, provision containers, download images, or start a lab. The preflight also makes no network requests and never launches the ISO.
