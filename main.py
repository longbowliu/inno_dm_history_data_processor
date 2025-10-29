import os
import glob
import yaml  # 需要安装 PyYAML: pip install pyyaml
import csv

# ======================
# 1. 配置部分
# ======================
BASE_DIR = "/mnt/AIDataSet"  # 数据集根目录

# ======================
# 2. 工具函数：安全读取文件
# ======================
def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[错误] 无法读取文件 {file_path}: {e}")
        return None

# ======================
# 3. 各文件处理函数（可逐步完善）
# ======================

def process_stop_bar_csv(file_path):
    print(f"\n🔧 [处理 stop_bar.csv] 文件: {file_path}")
    content = read_file(file_path)
    if content:
        # 简单打印前 5 行，你可以用 csv 模块进一步解析
        lines = content.strip().split('\n')[:5]
        for line in lines:
            print(line)

def process_flatten_yaml(file_path):
    print(f"\n🔧 [处理 Flatten YAML] 文件: {file_path}")
    content = read_file(file_path)
    if content:
        print(content)  # 或用 yaml.safe_load(content) 解析

def process_fusion_default_yaml(file_path):
    print(f"\n🔧 [处理 Fusion (default) YAML] 文件: {file_path}")
    content = read_file(file_path)
    if content:
        print(content)  # 或 yaml.safe_load(content)

def process_fusion_matrix_yaml(file_path):
    print(f"\n🔧 [处理 Fusion Matrix YAML] 文件: {file_path}")
    content = read_file(file_path)
    if content:
        print(content)

def process_lidar1_yaml(file_path):
    print(f"\n🔧 [处理 Lidar1 YAML] 文件: {file_path}")
    content = read_file(file_path)
    if content:
        print(content)

def process_lidar2_yaml(file_path):
    print(f"\n🔧 [处理 Lidar2 YAML] 文件: {file_path}")
    content = read_file(file_path)
    if content:
        print(content)

def process_paramserver_yaml(file_path):
    print(f"\n🔧 [处理 ParamServer YAML] 文件: {file_path}")
    content = read_file(file_path)
    if content:
        print(content)

# ======================
# 4. 主程序：遍历数据集并分发处理
# ======================
def process_dataset(dataset_dir):
    print("=" * 50)
    print(f"🔍 正在处理数据集目录: {dataset_dir}")
    print("=" * 50)

    # 1. stop_bar.csv
    stop_bar_csv = os.path.join(dataset_dir, "event_gt", "default", "stop_bar.csv")
    if os.path.isfile(stop_bar_csv):
        process_stop_bar_csv(stop_bar_csv)
    else:
        print("[⚠️] 未找到 stop_bar.csv")

    # 2. Flatten/*.yaml
    flatten_yaml = glob.glob(os.path.join(dataset_dir, "Flatten", "*.yaml"))
    if flatten_yaml:
        process_flatten_yaml(flatten_yaml[0])
    else:
        print("[⚠️] 未找到 Flatten YAML")

    # 3. Fusion/default/*.yaml
    fusion_default_yaml = glob.glob(os.path.join(dataset_dir, "Fusion", "default", "*.yaml"))
    if fusion_default_yaml:
        process_fusion_default_yaml(fusion_default_yaml[0])
    else:
        print("[⚠️] 未找到 Fusion (default) YAML")

    # 4. Fusion/fusion_matrix_*.yaml
    fusion_matrix_yaml = glob.glob(os.path.join(dataset_dir, "Fusion", "fusion_matrix_*.yaml"))
    if fusion_matrix_yaml:
        process_fusion_matrix_yaml(fusion_matrix_yaml[0])
    else:
        print("[⚠️] 未找到 Fusion Matrix YAML")

    # 5. Lidar1/default/*.yaml
    lidar1_yaml = glob.glob(os.path.join(dataset_dir, "Lidar1", "default", "*.yaml"))
    if lidar1_yaml:
        process_lidar1_yaml(lidar1_yaml[0])
    else:
        print("[⚠️] 未找到 Lidar1 YAML")

    # 6. Lidar2/default/*.yaml
    lidar2_yaml = glob.glob(os.path.join(dataset_dir, "Lidar2", "default", "*.yaml"))
    if lidar2_yaml:
        process_lidar2_yaml(lidar2_yaml[0])
    else:
        print("[⚠️] 未找到 Lidar2 YAML")

    # 7. ParamServer/default/params_*.yaml
    param_dir = os.path.join(dataset_dir, "ParamServer", "default")
    param_yamls = glob.glob(os.path.join(param_dir, "params_*.yaml")) + \
                  glob.glob(os.path.join(param_dir, "params.yaml"))
    for param_yaml in param_yamls:
        process_paramserver_yaml(param_yaml)

    # 可继续添加：static_map/static_*.pcd 等

# ======================
# 5. 主入口
# ======================
def main():
    if not os.path.isdir(BASE_DIR):
        print(f"[错误] 数据集根目录不存在: {BASE_DIR}")
        return

    # 遍历 BASE_DIR 下的每个数据集文件夹（如 A01_001_2_FK_S）
    for item in os.listdir(BASE_DIR):
        dataset_path = os.path.join(BASE_DIR, item)
        if os.path.isdir(dataset_path):
            process_dataset(dataset_path)

if __name__ == "__main__":
    main()