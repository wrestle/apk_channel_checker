# APK 解析工具

一个轻量级的只读型 APK 解析器，专注于快速提取签名与渠道信息。

[特性](#特性亮点) • [安装](#环境要求与安装) • [快速上手](#快速上手) • [用法](#命令行用法与示例) • [FAQ](#常见问题-faq)

---

## 工具简介

`apktool` 是一个纯 Python 实现的命令行工具，旨在为开发者和测试工程师提供一种快速、安全的方式来审查 Android 应用（APK）的底层结构信息。它以只读方式工作，无需解压或修改 APK 文件，即可精准提取其签名方案版本 (V1/V2/V3)、签名块 (Signature Block) 布局、关键偏移量以及嵌入在注释区或签名块中的渠道信息。

本工具特别适用于以下场景：

*   快速判断一个 APK 使用了哪种签名方案。
*   检查 V2/V3 签名块的完整性和对齐状态。
*   分析签名块中包含的自定义数据（如美团 Walle、腾讯 VasDolly 产生的渠道信息）。
*   提取传统的 V1 签名方案中存储在 ZIP 注释区的渠道数据。
*   辅助进行多渠道打包的校验工作。

最重要的是，它**不会以任何方式修改你的 APK 文件**，确保了操作的绝对安全。

## 特性亮点

*   **全面签名方案识别**:
    *   准确检测 APK 使用的是 V1、V2 还是 V3 签名方案。
*   **关键结构偏移打印**:
    *   清晰展示 APK 签名块、中央目录 (Central Directory) 和中央目录结尾记录 (EOCD) 的起始偏移与大小。
*   **签名块对齐校验**:
    *   自动检查 V2/V3 签名块是否满足 4096 字节的对齐要求。
*   **深度签名块遍历**:
    *   逐一解析并标注签名块 (Signature Block) 中的每一个数据块 (Block)，包括：
        *   V2/V3 签名数据块
        *   填充块 (Padding Block)
        *   已知的渠道信息块，如 Walle (`0x71777777`) 和 VasDolly (`0x881155ff`)。
*   **V1 渠道信息解析**:
    *   智能解析 ZIP 文件注释区，通过自定义的“魔法后缀”反向查找 `[value|length|magic]` 结构，提取渠道信息。
*   **数据块转储 (Dump)**:
    *   提供可选的 `-d/--dump` 参数，可将签名块中的每一个 Block 单独存为二进制文件，便于深度分析。

## 环境要求与安装

本工具基于 Python 3 开发，无需安装任何第三方库。

*   **Python 版本**: Python 3.6+
*   **操作系统**: macOS / Linux / Windows

你只需要下载 `apktool.py` 脚本文件，即可直接使用。

```bash
# 下载脚本 (或直接从仓库复制)
git clone https://github.com/wrestle/apk_channel_checker.git

cd apk_channel_checker

# 赋予执行权限 (可选)
chmod +x apktool.py
```

## 快速上手

分析一个 APK 文件非常简单。只需一个命令，即可获取其核心签名信息。

假设你有一个名为 `my-app.apk` 的文件，执行以下命令：

```bash
python3 apktool.py -f my-app.apk
```

你会看到类似下面的输出，清晰地展示了 APK 的签名版本、关键偏移量和签名块的对齐状态。

```text
Apk Dynamic Package Version V2
Signature Block Offset: 0x123456
Signature Block Size: 8192
Central Directory Offset: 0x125456
End Of Central Directory Offset: 0x136789
Signature Block Detail: is valid signature? True
... (更多签名块细节)
```

## 命令行用法与示例

### 基本用法

```
usage: apktool.py [-h] -f FILE [-v1m V1M] [-d]

APK Tool

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  指定要分析的 apk 文件路径 (必需)
  -v1m V1M, --v1-magic V1M
                        用于解析 V1 渠道信息的魔法后缀 (需提供 Base64 编码)
  -d, --dump            开启数据块转储功能，会将签名块中的每个 block 保存为独立文件
```

### 示例

#### 1. 基础分析

这是最常用的命令，用于获取 APK 的签名概览。

```bash
python3 apktool.py -f /path/to/your/app.apk
```

#### 2. 解析 V1 签名中的渠道信息

如果你的 APK 使用了基于 ZIP 注释区的 V1 渠道方案，你需要提供一个“魔法后缀”来帮助工具定位渠道信息。这个后缀需要经过 Base64 编码。

例如，如果魔法后缀是 `ltlovezh`，其 Base64 编码为 `bHRsb3Zlemg=`。

```bash
# 默认的魔法后缀 'ltlovezh' 无需显式传递
python3 apktool.py -f /path/to/your/v1_channel_app.apk

# 如果使用自定义魔法后缀，例如 'my-magic' (Base64: 'bXktbWFnaWM=')
echo -n 'my-magic' | base64  # 输出 bXktbWFnaWM=
python3 apktool.py -f /path/to/your/v1_channel_app.apk -v1m 'bXktbWFnaWM='
```

工具会从注释区尾部开始搜索，并打印出找到的渠道信息。

#### 3. 转储签名块中的所有 Block

当你需要对签名块中的某个特定 Block (例如某个加密的渠道信息块) 进行深入的二进制分析时，`--dump` 参数会非常有用。

```bash
python3 apktool.py -f /path/to/your/app.apk --dump
```

执行后，在 APK 文件所在的目录下，会生成一系列名为 `<apk文件名>.<block_id>.<length>` 的文件。例如：

*   `app.apk.1896449946.4060` (V2 签名块)
*   `app.apk.1903901943.128` (Walle 渠道块)

## 示例输出片段

下面是一个分析包含 V2 签名和 Walle 渠道信息的 APK 后的典型输出：

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

## 常见问题 (FAQ)

**Q1: 这个工具会修改我的 APK 文件吗？**
A: **绝对不会**。本工具以完全只读的模式运行，仅读取和解析文件内容，不进行任何写入或修改操作，确保原始文件的完整性和安全性。

**Q2: 为什么有些 APK 分析会失败并提示 "seek eocd fail"？**
A: 这通常意味着目标文件不是一个有效的 ZIP 归档（APK 本质上是 ZIP 格式），或者文件已损坏，导致工具无法找到关键的 EOCD (End of Central Directory) 记录。请确保你分析的是一个完整且未损坏的 APK 文件。

**Q3: "Signature Block Detail: is valid signature? False" 是什么意思？**
A: 这表示 APK 的签名块大小不符合 V2/V3 签名的 4096 字节对齐要求。虽然某些系统可能仍会接受这种不对齐的签名，但这通常表明打包过程存在问题，可能导致在某些设备或平台上安装失败。

**Q4: 我可以同时解析 V1 和 V2/V3 的渠道信息吗？**
A: 可以。工具会独立地检查签名块和 ZIP 注释区。如果一个 APK 同时包含了两种机制的渠道信息（虽然不常见），工具理论上可以分别解析并展示它们。

## 注意事项与局限

*   **只读解析**: 本工具**不能**用于 APK 的重打包、签名或渠道信息写入。它是一个纯粹的分析工具。
*   **渠道信息格式**: 工具能识别并打印出 Walle 和 VasDolly 的渠道块，并尝试将其中的内容解码为 UTF-8 字符串。如果渠道信息经过加密或使用了其他自定义格式，工具将仅显示原始的二进制数据。
*   **错误处理**: 对于结构异常或损坏的 APK，工具会尽力提供有意义的错误信息，但可能无法完成完整的解析。

## 许可
本项目采用 [MIT License](./LICENSE) 许可。
