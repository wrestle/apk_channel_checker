#!/usr/bin/env python3
import argparse
import base64
import struct
import os
import sys
from typing import BinaryIO, List, Tuple, Optional, Callable

# 常量定义
MAX_EOCD_SIZE = 1024
MIN_EOCD_SIZE = 22
APK_SIGNATURE_BLOCK_ALIGN = 4096

# Block IDs
VERSION_2_BLOCK_ID = 0x7109871a
VERSION_3_BLOCK_ID = 0xf05368c0
DEFAULT_PADDING_BLOCK_ID = 0x42726577
CHANNEL_WALLE_BLOCK_ID = 0x71777777
CHANNEL_VAS_DOLLY_BLOCK_ID = 0x881155ff

# Magic bytes
EOCD_BYTES = bytes([0x50, 0x4b, 0x05, 0x06])
MAGIC_BYTES = b'APK Sig Block 42'

# APK版本枚举
class APKVersion:
    UNKNOWN = 0
    V1 = 1
    V2 = 2
    V3 = 3

class Meta:
    def __init__(self):
        self.sign_offset = 0
        self.sign_block_buf = None
        self.sign_block_size = 0
        self.cd_offset = 0
        self.cd_offset_pos = 0
        self.eocd_offset = 0
        self.comment_len = 0
        self.comment_len_pos = 0
        self.content_len = 0

    def get_sign_block(self) -> Optional[bytes]:
        return self.sign_block_buf

    def get_comment_len(self) -> int:
        return self.comment_len

    def get_comment_len_pos(self) -> int:
        return self.comment_len_pos

    def get_apk_version(self) -> int:
        """返回APK版本"""
        if self.get_sign_block() is None:
            return APKVersion.V1

        if self.ids_exist_in_sign_block([VERSION_3_BLOCK_ID]):
            return APKVersion.V3

        if self.ids_exist_in_sign_block([VERSION_2_BLOCK_ID]):
            return APKVersion.V2

        return APKVersion.UNKNOWN

    def ids_exist_in_sign_block(self, ids: List[int]) -> bool:
        """检查指定的Block ID是否存在于Signature Block中"""
        if not self.sign_block_buf:
            return False

        buf = self.sign_block_buf
        sign_buf_len = len(buf)
        buf = buf[8:sign_buf_len-24]  # 去掉头尾

        offset = 0
        while buf:
            left = len(buf)
            if left == 0:
                break
            if left <= 12:
                return False

            # 读取size (8字节，小端序)
            size = struct.unpack('<Q', buf[:8])[0]
            if left - 8 < size:
                return False

            # 读取key ID (4字节，小端序)
            key_id = struct.unpack('<I', buf[8:12])[0]

            for id_val in ids:
                if key_id == id_val:
                    return True

            # 移动到下一个block
            offset += size + 8
            buf = buf[8 + size:]

        return False

    def for_each_sign_block(self, each_func: Callable[[int, bytes, int], bool]) -> None:
        """遍历每个sign block"""
        if not self.sign_block_buf:
            return

        buf = self.sign_block_buf
        sign_buf_len = len(buf)
        buf = buf[8:sign_buf_len-24]  # 去掉头尾

        while buf:
            left = len(buf)
            if left == 0:
                break
            if left <= 12:
                return

            # 读取size (8字节，小端序)
            size = struct.unpack('<Q', buf[:8])[0]
            if left - 8 < size:
                raise ValueError(f"left size {left-8} no more than size {size}")

            # 读取key ID (4字节，小端序)
            key_id = struct.unpack('<I', buf[8:12])[0]
            data = buf[12:8+size]

            # 调用回调函数
            if not each_func(key_id, data, size):
                return

            buf = buf[8 + size:]


def get_raw_body(file_obj: BinaryIO, offset: int, length: int) -> bytes:
    """从指定偏移量读取指定长度的数据"""
    file_obj.seek(offset)
    return file_obj.read(length)


def parse_meta(file_obj: BinaryIO, content_len: int) -> Meta:
    """解析APK元数据"""
    # 读取EOCD区域
    buf = get_raw_body(file_obj, content_len - MAX_EOCD_SIZE, MAX_EOCD_SIZE)

    # 查找EOCD标记
    idx = buf.find(EOCD_BYTES)
    if idx < 0:
        raise ValueError("seek eocd fail")

    if len(buf[idx:]) < MIN_EOCD_SIZE:
        raise ValueError(f"eocd block size less then 22, len:{len(buf[idx:])}")

    m = Meta()
    m.content_len = content_len

    # 记录各个偏移量
    m.eocd_offset = content_len - MAX_EOCD_SIZE + idx
    m.cd_offset_pos = m.eocd_offset + 16
    m.cd_offset = struct.unpack('<I', buf[idx+16:idx+20])[0]
    m.comment_len_pos = m.eocd_offset + 20
    m.comment_len = struct.unpack('<H', buf[idx+20:idx+22])[0]

    try:
        sign_block_buf, sign_block_size = parse_sign_block_and_size(file_obj, m)
        m.sign_block_buf = sign_block_buf
        m.sign_block_size = sign_block_size
        m.sign_offset = m.cd_offset - 8 - sign_block_size
    except Exception as e:
        # 如果解析签名块失败，继续返回基础元数据
        print(f"Parse sign block failed: {e}")

    return m


def parse_sign_block_and_size(file_obj: BinaryIO, meta: Meta) -> Tuple[bytes, int]:
    """解析签名块和大小"""
    # 读取签名魔数区域
    sign_magic_buf = get_raw_body(file_obj, meta.cd_offset - 24, 24)
    if len(sign_magic_buf) < 24:
        raise ValueError("read sign magic fail: buffer less than 24")

    # 检查魔数
    if sign_magic_buf[8:24] != MAGIC_BYTES:
        raise ValueError(f"unmatch magic sig 42, buf:{sign_magic_buf[0:24]}")

    # 读取签名块大小 (8字节，小端序)
    sign_block_size = struct.unpack('<Q', sign_magic_buf[0:8])[0]

    # 读取完整的签名块
    sign_block_buf = get_raw_body(file_obj, meta.cd_offset - 8 - sign_block_size, sign_block_size + 8)
    if len(sign_block_buf) < sign_block_size + 8:
        raise ValueError(f"read sig sign block fail: less than {sign_block_size + 8}")

    return sign_block_buf, sign_block_size


def is_magic_suffix(data: bytes, magic: bytes) -> bool:
    """检查是否是魔法后缀"""
    if len(data) < len(magic):
        return False
    return data[:len(magic)] == magic


def parse_special_data(raw: bytes, magic_suffix: bytes) -> None:
    """解析特殊数据（渠道信息等）"""
    magic_len = len(magic_suffix)

    if len(raw) < magic_len + 2:
        return

    # 从后往前查找魔法后缀
    for i in range(len(raw) - magic_len, -1, -1):
        if not is_magic_suffix(raw[i:], magic_suffix):
            continue

        # 检查长度字段位置是否有效
        if i < 2:
            continue

        length_start = i - 2
        value_length = struct.unpack('<H', raw[length_start:i])[0]

        # 检查值字段是否在数据范围内
        if length_start < value_length:
            print(f"at {i}: valueLength {value_length} out of range for {length_start}")
            continue

        value_start = length_start - value_length

        # 提取三个部分
        value_part = raw[value_start:length_start]
        length_part = raw[length_start:length_start+2]
        magic_part = raw[i:i+magic_len]

        # 输出结果
        print(f"Found Channel at (Position {value_start}-{i+magic_len-1}):")
        print(f"  New Comment Value: {value_part} (Channel: {value_part.decode('utf-8', errors='ignore')})")
        print(f"  New Comment Length: {length_part} (LittleEndian: {value_length})")
        print(f"  New Comment Magic Suffix: {magic_part} (String: {magic_part.decode('utf-8', errors='ignore')})")
        print("---")

        # 继续在前面的数据中查找
        if value_start > 0:
            parse_special_data(raw[:value_start], magic_suffix)
        return


def help():
    """显示帮助信息"""
    print("Usage: apktool.py -f <apkfile>")
    print("Usage: apktool.py -f <apkfile> -v1m <version 1's magic suffix(base64 encode)>")


def main():
    parser = argparse.ArgumentParser(description='APK Tool')
    parser.add_argument('-f', '--file', dest='file', required=True, help='apk file')
    parser.add_argument('-v1m', '--v1-magic', dest='v1m', default='',
                       help="version 1's magic suffix(base64 encode)")
    parser.add_argument('-d', '--dump', dest='dump', action='store_true',
                       help='dump apk')

    args = parser.parse_args()

    if not args.file:
        print("no apk file input")
        help()
        return

    v1m = "ltlovezh"
    if args.v1m:
        try:
            _v1m = base64.b64decode(args.v1m)
            v1m = _v1m.decode('utf-8')
        except Exception as e:
            print(f"decode version 1's magic suffix(base64 encode) fail: {e}")
            return

    try:
        with open(args.file, 'rb') as f:
            file_size = os.path.getsize(args.file)
            meta = parse_meta(f, file_size)

            version = meta.get_apk_version()
            version_names = {
                APKVersion.UNKNOWN: "Unknown",
                APKVersion.V1: "V1",
                APKVersion.V2: "V2",
                APKVersion.V3: "V3"
            }

            print(f"Apk Dynamic Package Version {version_names.get(version, 'Unknown')}")
            print(f"Signature Block Offset: 0x{meta.sign_offset:x}")
            print(f"Signature Block Size: {meta.sign_block_size + 8}")
            print(f"Central Directory Offset: 0x{meta.cd_offset:x}")
            print(f"End Of Central Directory Offset: 0x{meta.eocd_offset:x}")

            if version == APKVersion.V2 or version == APKVersion.V3:
                is_valid = ((meta.sign_block_size + 8) % APK_SIGNATURE_BLOCK_ALIGN) == 0
                print(f"Signature Block Detail: is valid signature? {is_valid}")
                print(f"(0x{meta.sign_offset:x}){meta.sign_offset} length=8 [head]total Signature Block size={meta.sign_block_size + 8}\n")

                def each_block_handler(block_id, data, length):
                    block_size = length + 8
                    if block_id == VERSION_2_BLOCK_ID:
                        print(f"(0x{block_id:x}){block_id} (length[8]-id[4]-value[{length-4:4d}])[{block_size:4d}] version 2's special block")
                    elif block_id == VERSION_3_BLOCK_ID:
                        print(f"(0x{block_id:x}){block_id} (length[8]-id[4]-value[{length-4:4d}])[{block_size:4d}] version 3's special block")
                    elif block_id == DEFAULT_PADDING_BLOCK_ID:
                        print(f"(0x{block_id:x}){block_id} (length[8]-id[4]-value[{length-4:4d}])[{block_size:4d}] padding blocks")
                    elif block_id == CHANNEL_VAS_DOLLY_BLOCK_ID:
                        print(f"(0x{block_id:x}){block_id} (length[8]-id[4]-value[{length-4:4d}])[{block_size:4d}] vasdolly channel id, data={data.decode('utf-8', errors='ignore')}")
                    elif block_id == CHANNEL_WALLE_BLOCK_ID:
                        print(f"(0x{block_id:x}){block_id} (length[8]-id[4]-value[{length-4:4d}])[{block_size:4d}] walle channel id, data={data.decode('utf-8', errors='ignore')}")
                    else:
                        print(f"(0x{block_id:x}){block_id} (length[8]-id[4]-value[{length-4}])[{block_size}] data={data.decode('utf-8', errors='ignore')}")

                    # 保存块数据到文件
                    try:
                        dump_filename = f"{args.file}.{block_id}.{length}"
                        with open(dump_filename, 'wb') as dump_file:
                            dump_file.write(data)
                    except Exception as e:
                        print(f"Create Dump File failed: {e}")

                    return True

                meta.for_each_sign_block(each_block_handler)

                print(f"\n(0x{meta.cd_offset-24:x}){meta.cd_offset-24} length=8 [tail]total Signature Block size={meta.sign_block_size + 8}")
                print(f"(0x{meta.cd_offset-16:x}){meta.cd_offset-16} length=16 [tail]Signature Block Magic={MAGIC_BYTES.decode('utf-8')}")
                print("Signature Block End")

            # 读取注释
            f.seek(meta.get_comment_len_pos() + 2)
            comment = f.read(meta.get_comment_len())

            print(f"Apk Comment Length: {meta.get_comment_len()}")
            if meta.get_comment_len() > 0:
                print(f"Apk Comment: {comment.decode('utf-8', errors='ignore')}")
                parse_special_data(comment, v1m.encode('utf-8'))

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
