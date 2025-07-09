#!/usr/bin/env python3
"""
BigWorld Engine Map Upgrader
支持将1.8版本的地图文件升级到2.0或14.4.1版本
"""

import os
import sys
import zipfile
import struct
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BWVersion(Enum):
    """BigWorld版本枚举"""
    V1_8 = "1.8"
    V2_0 = "2.0"
    V14_4_1 = "14.4.1"

@dataclass
class ChunkHeader:
    """Chunk文件头结构"""
    magic: bytes
    version: int
    size: int
    chunk_id: str
    bounds: tuple  # (min_x, min_y, min_z, max_x, max_y, max_z)

@dataclass
class TerrainBlock:
    """地形块数据结构"""
    height_map: List[List[float]]
    blend_map: List[List[int]]
    texture_layers: List[str]
    normal_map: Optional[bytes] = None

class ChunkProcessor:
    """Chunk数据处理器"""
    
    def __init__(self, source_version: BWVersion, target_version: BWVersion):
        self.source_version = source_version
        self.target_version = target_version
        self.version_configs = self._load_version_configs()
    
    def _load_version_configs(self) -> Dict[str, Any]:
        """加载版本配置信息"""
        return {
            "1.8": {
                "chunk_magic": b"BWC1",
                "terrain_format": "legacy",
                "coordinate_scale": 1.0,
                "texture_format": "dds",
                "chunk_size": 100.0
            },
            "2.0": {
                "chunk_magic": b"BWC2",
                "terrain_format": "enhanced",
                "coordinate_scale": 1.0,
                "texture_format": "dds",
                "chunk_size": 100.0
            },
            "14.4.1": {
                "chunk_magic": b"BWCO",  # OSE version
                "terrain_format": "modern",
                "coordinate_scale": 1.0,
                "texture_format": "bc7",
                "chunk_size": 100.0
            }
        }
    
    def read_chunk_header(self, data: bytes) -> ChunkHeader:
        """读取chunk头信息"""
        if len(data) < 32:
            raise ValueError("Chunk数据太短")
        
        magic = data[:4]
        version = struct.unpack('<I', data[4:8])[0]
        size = struct.unpack('<I', data[8:12])[0]
        
        # 解析chunk ID (通常是坐标信息)
        chunk_id_raw = data[12:28]
        chunk_id = chunk_id_raw.decode('ascii', errors='ignore').strip('\x00')
        
        # 解析边界框
        bounds = struct.unpack('<ffffff', data[28:52])
        
        return ChunkHeader(magic, version, size, chunk_id, bounds)
    
    def read_terrain_data(self, data: bytes, header: ChunkHeader) -> TerrainBlock:
        """读取地形数据"""
        offset = 52  # 跳过头部
        
        # 读取高度图 (假设100x100)
        height_map = []
        for i in range(100):
            row = []
            for j in range(100):
                height_bytes = data[offset:offset+4]
                height = struct.unpack('<f', height_bytes)[0]
                row.append(height)
                offset += 4
            height_map.append(row)
        
        # 读取混合图
        blend_map = []
        for i in range(100):
            row = []
            for j in range(100):
                blend_bytes = data[offset:offset+4]
                blend = struct.unpack('<I', blend_bytes)[0]
                row.append(blend)
                offset += 4
            blend_map.append(row)
        
        # 读取纹理层信息
        texture_count = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        
        texture_layers = []
        for _ in range(texture_count):
            # 读取纹理路径长度
            path_length = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            # 读取纹理路径
            texture_path = data[offset:offset+path_length].decode('utf-8')
            texture_layers.append(texture_path)
            offset += path_length
        
        return TerrainBlock(height_map, blend_map, texture_layers)
    
    def convert_terrain_format(self, terrain: TerrainBlock) -> TerrainBlock:
        """转换地形格式"""
        if self.source_version == BWVersion.V1_8 and self.target_version == BWVersion.V14_4_1:
            # 1.8 -> 14.4.1 需要特殊处理
            return self._convert_1_8_to_14_4_1(terrain)
        elif self.source_version == BWVersion.V1_8 and self.target_version == BWVersion.V2_0:
            # 1.8 -> 2.0 相对简单
            return self._convert_1_8_to_2_0(terrain)
        else:
            return terrain
    
    def _convert_1_8_to_14_4_1(self, terrain: TerrainBlock) -> TerrainBlock:
        """1.8格式转换为14.4.1格式"""
        # 高度图保持不变
        new_height_map = terrain.height_map
        
        # 混合图可能需要重新计算
        new_blend_map = []
        for row in terrain.blend_map:
            new_row = []
            for blend_value in row:
                # 14.4.1版本可能使用不同的混合算法
                new_blend_value = self._convert_blend_value(blend_value)
                new_row.append(new_blend_value)
            new_blend_map.append(new_row)
        
        # 纹理路径可能需要更新
        new_texture_layers = []
        for texture_path in terrain.texture_layers:
            new_path = self._convert_texture_path(texture_path)
            new_texture_layers.append(new_path)
        
        return TerrainBlock(new_height_map, new_blend_map, new_texture_layers)
    
    def _convert_1_8_to_2_0(self, terrain: TerrainBlock) -> TerrainBlock:
        """1.8格式转换为2.0格式"""
        # 2.0版本与1.8相对接近，主要是细节调整
        return TerrainBlock(
            terrain.height_map,
            terrain.blend_map,
            terrain.texture_layers
        )
    
    def _convert_blend_value(self, old_value: int) -> int:
        """转换混合值"""
        # 根据版本差异调整混合算法
        if self.target_version == BWVersion.V14_4_1:
            # 14.4.1可能使用更高精度的混合
            return min(old_value * 2, 255)
        return old_value
    
    def _convert_texture_path(self, old_path: str) -> str:
        """转换纹理路径"""
        # 更新纹理路径格式
        if self.target_version == BWVersion.V14_4_1:
            # 14.4.1可能使用不同的纹理格式
            return old_path.replace('.dds', '.bc7')
        return old_path
    
    def write_chunk_data(self, header: ChunkHeader, terrain: TerrainBlock) -> bytes:
        """写入chunk数据"""
        # 更新头部信息
        target_config = self.version_configs[self.target_version.value]
        new_header = ChunkHeader(
            target_config["chunk_magic"],
            header.version + 1,  # 版本递增
            header.size,
            header.chunk_id,
            header.bounds
        )
        
        # 构建数据
        data = bytearray()
        
        # 写入头部
        data.extend(new_header.magic)
        data.extend(struct.pack('<I', new_header.version))
        data.extend(struct.pack('<I', new_header.size))
        data.extend(new_header.chunk_id.encode('ascii').ljust(16, b'\x00'))
        data.extend(struct.pack('<ffffff', *new_header.bounds))
        
        # 写入高度图
        for row in terrain.height_map:
            for height in row:
                data.extend(struct.pack('<f', height))
        
        # 写入混合图
        for row in terrain.blend_map:
            for blend in row:
                data.extend(struct.pack('<I', blend))
        
        # 写入纹理层
        data.extend(struct.pack('<I', len(terrain.texture_layers)))
        for texture_path in terrain.texture_layers:
            path_bytes = texture_path.encode('utf-8')
            data.extend(struct.pack('<I', len(path_bytes)))
            data.extend(path_bytes)
        
        return bytes(data)

class MapUpgrader:
    """地图升级器主类"""
    
    def __init__(self, source_version: BWVersion, target_version: BWVersion):
        self.source_version = source_version
        self.target_version = target_version
        self.processor = ChunkProcessor(source_version, target_version)
    
    def upgrade_map(self, input_path: str, output_path: str) -> bool:
        """升级地图文件"""
        try:
            logger.info(f"开始升级地图: {input_path}")
            logger.info(f"源版本: {self.source_version.value} -> 目标版本: {self.target_version.value}")
            
            # 确保输出目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 处理space文件夹
            if os.path.isdir(input_path):
                return self._upgrade_space_folder(input_path, output_path)
            else:
                return self._upgrade_single_file(input_path, output_path)
            
        except Exception as e:
            logger.error(f"升级失败: {str(e)}")
            return False
    
    def _upgrade_space_folder(self, input_folder: str, output_folder: str) -> bool:
        """升级整个space文件夹"""
        success_count = 0
        total_count = 0
        
        for root, dirs, files in os.walk(input_folder):
            for file in files:
                if file.endswith('.cdata'):
                    total_count += 1
                    input_file = os.path.join(root, file)
                    
                    # 保持相对路径结构
                    rel_path = os.path.relpath(input_file, input_folder)
                    output_file = os.path.join(output_folder, rel_path)
                    
                    if self._upgrade_single_file(input_file, output_file):
                        success_count += 1
        
        logger.info(f"升级完成: {success_count}/{total_count} 文件成功")
        return success_count == total_count
    
    def _upgrade_single_file(self, input_file: str, output_file: str) -> bool:
        """升级单个cdata文件"""
        try:
            logger.info(f"处理文件: {input_file}")
            
            # 确保输出目录存在
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            # 读取原文件
            with zipfile.ZipFile(input_file, 'r') as zip_in:
                with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                    
                    # 处理每个zip内的文件
                    for item in zip_in.namelist():
                        data = zip_in.read(item)
                        
                        if item.endswith('.chunk'):
                            # 处理chunk文件
                            converted_data = self._process_chunk_file(data)
                            zip_out.writestr(item, converted_data)
                        else:
                            # 其他文件直接复制
                            zip_out.writestr(item, data)
            
            logger.info(f"文件升级完成: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"处理文件失败 {input_file}: {str(e)}")
            return False
    
    def _process_chunk_file(self, chunk_data: bytes) -> bytes:
        """处理单个chunk文件"""
        try:
            # 读取原始数据
            header = self.processor.read_chunk_header(chunk_data)
            terrain = self.processor.read_terrain_data(chunk_data, header)
            
            # 转换格式
            converted_terrain = self.processor.convert_terrain_format(terrain)
            
            # 写入新格式
            new_data = self.processor.write_chunk_data(header, converted_terrain)
            
            return new_data
            
        except Exception as e:
            logger.error(f"处理chunk数据失败: {str(e)}")
            return chunk_data  # 失败时返回原始数据

def main():
    """主函数"""
    if len(sys.argv) != 4:
        print("用法: python map_upgrader.py <源版本> <目标版本> <输入路径> <输出路径>")
        print("版本选项: 1.8, 2.0, 14.4.1")
        print("示例: python map_upgrader.py 1.8 14.4.1 ./old_map ./new_map")
        sys.exit(1)
    
    source_ver = sys.argv[1]
    target_ver = sys.argv[2]
    input_path = sys.argv[3]
    output_path = sys.argv[4]
    
    # 验证版本
    version_map = {
        "1.8": BWVersion.V1_8,
        "2.0": BWVersion.V2_0,
        "14.4.1": BWVersion.V14_4_1
    }
    
    if source_ver not in version_map or target_ver not in version_map:
        print("错误: 不支持的版本")
        sys.exit(1)
    
    # 创建升级器
    upgrader = MapUpgrader(version_map[source_ver], version_map[target_ver])
    
    # 执行升级
    success = upgrader.upgrade_map(input_path, output_path)
    
    if success:
        print("地图升级成功!")
        sys.exit(0)
    else:
        print("地图升级失败!")
        sys.exit(1)

if __name__ == "__main__":
    main()