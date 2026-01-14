# APK Tool

A lightweight, read-only APK parser focused on quickly extracting signature and channel information.

[Features](#features) • [Installation](#requirements--installation) • [Quick Start](#quick-start) • [Usage](#cli-usage--examples) • [FAQ](#faq)

---

## Overview

`apktool` is a command-line tool built with pure Python, designed to provide developers and QA engineers a fast and safe way to inspect the underlying structural information of Android applications (APKs). It operates in a read-only mode, accurately extracting signature scheme versions (V1/V2/V3), Signature Block layouts, critical offsets, and channel information embedded in the comment area or signature block, all without decompressing or modifying the APK file.

This tool is particularly useful for:

*   Quickly identifying which signature scheme an APK uses.
*   Verifying the integrity and alignment of V2/V3 signature blocks.
*   Analyzing custom data within the signature block (e.g., channel information from Meituan's Walle or Tencent's VasDolly).
*   Extracting channel data stored in the ZIP comment area of traditional V1-signed APKs.
*   Assisting with the validation of multi-channel packaging.

Most importantly, it **will not modify your APK file in any way**, ensuring absolute operational safety.

## Features

*   **Comprehensive Signature Scheme Identification**:
    *   Accurately detects whether an APK uses the V1, V2, or V3 signature scheme.
*   **Key Structure Offset Printing**:
    *   Clearly displays the starting offsets and sizes of the APK's Signature Block, Central Directory, and End of Central Directory (EOCD) record.
*   **Signature Block Alignment Check**:
    *   Automatically verifies if the V2/V3 signature block meets the 4096-byte alignment requirement.
*   **In-depth Signature Block Traversal**:
    *   Parses and annotates each data block within the Signature Block, including:
        *   V2/V3 signature data blocks
        *   Padding blocks
        *   Known channel info blocks, such as Walle (`0x71777777`) and VasDolly (`0x881155ff`).
*   **V1 Channel Info Parsing**:
    *   Intelligently parses the ZIP file's comment section, reverse-searching for a `[value|length|magic]` structure using a custom "magic suffix" to extract channel information.
*   **Data Block Dumping**:
    *   Provides an optional `-d/--dump` argument to save each block from the signature block as a separate binary file for in-depth analysis.

## Requirements & Installation

This tool is developed in Python 3 and requires no third-party libraries.

*   **Python Version**: Python 3.6+
*   **Operating System**: macOS / Linux / Windows

Simply download the `apktool.py` script to get started.

```bash
# Download the script (or copy it directly from the repository)
git clone https://github.com/wrestle/apk_channel_checker.git

cd apk_channel_checker

# Grant execution permissions (optional)
chmod +x apktool.py
```

## Quick Start

Analyzing an APK file is straightforward. A single command is all it takes to retrieve its core signature information.

Assuming you have a file named `my-app.apk`, run the following command:

```bash
python3 apktool.py -f my-app.apk
```

You will see output similar to the following, clearly showing the APK's signature version, key offsets, and alignment status.

```text
Apk Dynamic Package Version V2
Signature Block Offset: 0x123456
Signature Block Size: 8192
Central Directory Offset: 0x125456
End Of Central Directory Offset: 0x136789
Signature Block Detail: is valid signature? True
... (more signature block details)
```

## CLI Usage & Examples

### Basic Usage

```
usage: apktool.py [-h] -f FILE [-v1m V1M] [-d]

APK Tool

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  Specify the path to the APK file to analyze (required)
  -v1m V1M, --v1-magic V1M
                        Magic suffix for parsing V1 channel info (Base64 encoded)
  -d, --dump            Enable data block dump feature, saving each block to a file
```

### Examples

#### 1. Basic Analysis

This is the most common command, used to get a signature overview of an APK.

```bash
python3 apktool.py -f /path/to/your/app.apk
```

#### 2. Parsing Channel Information from a V1 Signature

If your APK uses a V1 channel scheme based on the ZIP comment area, you need to provide a "magic suffix" to help the tool locate the channel data. This suffix must be Base64 encoded.

For example, if the magic suffix is `ltlovezh`, its Base64 encoding is `bHRsb3Zlemg=`.

```bash
# The default magic suffix 'ltlovezh' does not need to be explicitly passed
python3 apktool.py -f /path/to/your/v1_channel_app.apk

# For a custom magic suffix, e.g., 'my-magic' (Base64: 'bXktbWFnaWM=')
echo -n 'my-magic' | base64  # Outputs bXktbWFnaWM=
python3 apktool.py -f /path/to/your/v1_channel_app.apk -v1m 'bXktbWFnaWM='
```

The tool will search backward from the end of the comment section and print any channel information it finds.

#### 3. Dumping All Blocks from the Signature Block

The `--dump` argument is useful when you need to perform a deep binary analysis on a specific block within the signature block (e.g., an encrypted channel info block).

```bash
python3 apktool.py -f /path/to/your/app.apk --dump
```

After execution, a series of files named `<apk_filename>.<block_id>.<length>` will be generated in the same directory as the APK. For example:

*   `app.apk.1896449946.4060` (V2 signature block)
*   `app.apk.1903901943.128` (Walle channel block)

## Sample Output

Here is a typical output from analyzing an APK that includes a V2 signature and Walle channel information:

```text
$ python3 apktool.py -f my-app-channel-test.apk

Apk Dynamic Package Version V2
Signature Block Offset: 0x2e6000
Signature Block Size: 4096
Central Directory Offset: 0x2e7000
End Of Central Directory Offset: 0x2f1b4f
Signature Block Detail: is valid signature? True
(0x2e6000)3038976 length=8 [head]total Signature Block size=4096

(0x7109871a)1896449946 (length[8]-id[4]-value[3888])[3900] version 2's special block
(0x71777777)1903901943 (length[8]-id[4]-value[ 112])[ 124] walle channel id, data={"channel":"GooglePlay","extra":"build20260114"}
(0x42726577)1114795383 (length[8]-id[4]-value[  44])[  56] padding blocks

(0x2e6fe8)3043208 length=8 [tail]total Signature Block size=4096
(0x2e6ff0)3043216 length=16 [tail]Signature Block Magic=APK Sig Block 42
Signature Block End
Apk Comment Length: 0
```

## FAQ

**Q1: Will this tool modify my APK file?**
A: **Absolutely not.** This tool operates in a completely read-only mode. It only reads and parses the file content without performing any write or modification operations, ensuring the integrity and safety of the original file.

**Q2: Why does the analysis of some APKs fail with a "seek eocd fail" error?**
A: This typically means the target file is not a valid ZIP archive (APKs are essentially ZIP files) or the file is corrupted, preventing the tool from finding the critical EOCD (End of Central Directory) record. In such abnormal scenarios, the tool provides a clear error message. Please ensure you are analyzing a complete and undamaged APK file.

**Q3: What does "Signature Block Detail: is valid signature? False" mean?**
A: This indicates that the APK's signature block size does not meet the 4096-byte alignment requirement for V2/V3 signatures. While some systems may still accept such unaligned signatures, it often points to an issue in the packaging process and could lead to installation failures on certain devices or platforms.

**Q4: Can I parse channel information for both V1 and V2/V3 schemes at the same time?**
A: Yes. The tool independently checks both the signature block and the ZIP comment area. If an APK contains channel information from both mechanisms (which is uncommon), the tool can theoretically parse and display both.

## Notes & Limitations

*   **Read-Only Analysis**: This tool **cannot** be used for repacking, signing, or writing channel information to an APK. It is purely an analysis tool.
*   **Channel Info Format**: The tool can identify and print channel blocks from Walle and VasDolly, attempting to decode their content as UTF-8 strings. If the channel information is encrypted or uses a different custom format, the tool will only display the raw binary data.
*   **Error Handling**: For structurally abnormal or corrupted APKs, the tool will attempt to provide a meaningful error message but may not be able to complete a full analysis.

## License

This project is licensed under the [MIT License](./LICENSE).