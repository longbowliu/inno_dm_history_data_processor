import os
import glob
import yaml  # 需要安装 PyYAML: pip install pyyaml
import csv
import json
import requests
from minio_upload_innopc import upload_file_to_minio

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

def process_inno_pc(dataset_name, file_path, lidar_index):
    print(f"\n🔧 [处理 Inno PC] 文件: {file_path}")
    bucket_name = "inno-pc"
    file_name = os.path.basename(file_path)
    try:
        file_id = upload_file_to_minio(bucket_name, file_name, file_path)
        return file_id, file_name
    except Exception as e:
        print(f"[错误] 上传文件 {file_path} 失败: {e}")
        return None, None
    
   


# ======================
# 4. 主程序：遍历数据集并分发处理
# ======================
def process_dataset(dataset_name ,dataset_dir, innopc_empty_folder):
    print("=" * 50)
    print(f"🔍 正在处理数据集目录: {dataset_dir}")
    print("=" * 50)
    
    lidar1_innopc = glob.glob(os.path.join(dataset_dir, "Lidar1",  "*.inno_pc"))
    uuid1 = None
    innopc_name1 = None
    uuid2 = None
    innopc_name2 = None
    if lidar1_innopc:
        lidar_index = 1
        uuid1,innopc_name1 = process_inno_pc(dataset_name,lidar1_innopc[0],lidar_index)
        
    lidar2_innopc = glob.glob(os.path.join(dataset_dir, "Lidar2", "default", "*.inno_pc"))
    if lidar2_innopc:
        lidar_index = 2
        uuid2,innopc_name2 = process_inno_pc(dataset_name,lidar2_innopc[0],lidar_index)
        
    if uuid1 or uuid2:
        print(f"[信息] 文件上传成功，唯一ID: {uuid1 if uuid1 else uuid2}")
        name = dataset_name
        position = "s"
        sdk = "inno_pc_client_3.102.9_x86"
        tags = []
        innopcs = []
        if uuid1:
            innopcs.append({
                "attachId": uuid1,
                "lidarName": "Lidar_1",
                "lidarModel": None,
                "scanMode": None
            })
        if uuid2:
            innopcs.append({
                "attachId": uuid2,
                "lidarName": "Lidar_2",
                "lidarModel": None,
                "scanMode": None
            })
        scene_data = {
            "name": name,
            "position": position,
            "sdk": sdk,
            "tags": tags,
            "innopcs": innopcs
        }
        scene_data_json = json.dumps(scene_data)
        print(scene_data_json)
        url = "http://localhost/dmapi/scene"
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, data=scene_data_json, headers=headers)
        print(response.text)
        print(response.status_code)
        if response.status_code == 200:
            print("[信息] 场景数据提交成功")
        else:
            print(f"[错误] 场景数据提交失败，状态码: {response.status_code}")
    else:
        print("[错误] 文件上传失败")
    '''
    Post http://localhost/dmapi/scene
    request body:
    {"name":"C_B23_E_1_FK_DFT_11999","position":"s","sdk":"inno_pc_client_3.102.9_x86","tags":[],"innopcs":[{"attachId":"1971086096573210626","lidarName":"Lidar_1","lidarModel":null,"scanMode":null}]}
    '''    
    
    
    
        
    return
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

def check_inno_pc_files(dataset_dir,dest_file="innopc_empty.txt"):
    """
    检查 Lidar1 和 Lidar2 目录下是否有 .inno_pc 文件
    如果没有，则将数据集根目录写入 innopc_empty.txt 文件
    """
    lidar1_inno_pc = glob.glob(os.path.join(dataset_dir, "Lidar1", "*.inno_pc"))
    lidar2_inno_pc = glob.glob(os.path.join(dataset_dir, "Lidar2", "*.inno_pc"))
    if not lidar1_inno_pc or not lidar2_inno_pc:
        with open(dest_file, "a") as f:
            f.write(os.path.basename(dataset_dir) + "\n")

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
# 5. 主入口
# ======================
def main():
    '''
    demo@demo-OMEN-by-HP-Laptop-16-b0xxx:/mnt/AIDataSet$ tree
    .
    ├── A01_001_2_FK_S
    │   ├── event_gt
    │   │   └── default
    │   │       └── stop_bar.csv
    │   ├── Flatten
    │   │   └── 01_parallel_0114_A01_falcon.yaml
    │   ├── Fusion
    │   │   ├── default
    │   │   │   └── stopbar_ad_A01.yaml
    │   │   └── fusion_matrix_0114_A01_falcon.yaml
    │   ├── fusion_cubiao.zip
    │   ├── Lidar1
    │   │   ├── default
    │   │   │   └── lidar1_loop_0114_A01_falcon.yaml
    │   │   └── P-A01-11-FK-DFT-001.inno_pc
    │   ├── Lidar2
    │   │   ├── default
    │   │   │   └── lidar2_loop_0114_A01_falcon.yaml
    │   │   └── P-A01-12-FK-DFT-001.inno_pc
    │   ├── ParamServer
    │   │   └── default
    │   │       ├── params_multi.yaml
    │   │       └── params.yaml
    │   └── static_map
    │       └── static_5_result.pcd
    ├── A10_001_2_FK_PR
    │   ├── BoxFilterROI
    │   │   └── FK_A10_50_150
    │   │       └── Box_filter_ROI_A10_PR_0820.yaml
    │   ├── Flatten
    │   │   └── Ground_alignment_A10_FK.yaml
    │   ├── Fusion
    │   │   ├── default
    │   │   ├── fusion_matrix_A10_FK.yaml
    │   │   └── gt.zip
    │   ├── InnoPCClient
    │   │   └── inno_pc_client
    │   ├── Lidar1
    │   │   ├── 50_150
    │   │   │   └── lidar1_roi_center_road_A10_FK_analyse.yaml
    │   │   ├── FK_A10_200_200
    │   │   │   └── lidar1_roi_200_200.yaml
    │   │   ├── FK_A10_50_150
    │   │   │   └── lidar1_roi_center_road_A10_FK_upload.yaml
    │   │   └── P-A10-11-FK-DFT-001-validation.inno_pc
    │   ├── Lidar2
    │   │   ├── 50_150
    │   │   │   └── lidar2_roi_center_road_A10_FK_analyse.yaml
    │   │   ├── FK_A10_200_200
    │   │   │   └── lidar2_roi_200_200.yaml
    │   │   ├── FK_A10_50_150
    │   │   │   └── lidar2_roi_center_road_A10_FK_upload.yaml
    │   │   └── P-A10-12-FK-DFT-001-validation.inno_pc
    │   ├── ParamServer
    │   │   ├── FK_A10_200_200
    │   │   │   ├── params_multi.yaml
    │   │   │   └── params.yaml
    │   │   └── FK_A10_50_150
    │   │       ├── params_multi.yaml
    │   │       └── params.yaml
    │   ├── scene_config.yaml
    │   └── static_map
    │       └── static_5_result.pcd
    ├── A10_001_2_FK_PR_1057
    ......

    '''
	

    BASE_DIR = "/mnt/AIDataSet"
    if not os.path.isdir(BASE_DIR):
        print(f"[错误] 数据集根目录不存在: {BASE_DIR}")
        return
    innopc_empty_folder = os.path.join(os.getcwd(), "innopc_empty.txt")
    # 遍历 BASE_DIR 下的每个数据集文件夹（如 A01_001_2_FK_S）
    for item in os.listdir(BASE_DIR):
        dataset_path = os.path.join(BASE_DIR, item)
        is_empty_innopc = os.path.basename(dataset_path) not in open(innopc_empty_folder, "r").read().splitlines()
        if os.path.isdir(dataset_path) and is_empty_innopc:
            # 1, 检查 Lidar1 和 Lidar2 目录下是否有 .inno_pc 文件, 并记录缺失的目录.只运行一次
            # check_inno_pc_files(dataset_path,innopc_empty_folder)
            process_dataset(item,dataset_path,innopc_empty_folder)
        else:
            print(f"[跳过] 空目录或者缺失 innopc 文件: {dataset_path}")

if __name__ == "__main__":
    main()