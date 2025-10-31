import os
import glob
import yaml  # 需要安装 PyYAML: pip install pyyaml
import csv
import json
import requests
from minio_upload_innopc import upload_file_to_minio 
from minio_upload_innopc import get_db_connection

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
    
   
def upload_innopc_generat_scene(dataset_name ,dataset_dir):
    lidar1_innopc = glob.glob(os.path.join(dataset_dir, "Lidar1",  "*.inno_pc"))
    uuid1 = None
    innopc_name1 = None
    uuid2 = None
    innopc_name2 = None
    if lidar1_innopc:
        lidar_index = 1
        uuid1,innopc_name1 = process_inno_pc(dataset_name,lidar1_innopc[0],lidar_index)
        
    lidar2_innopc = glob.glob(os.path.join(dataset_dir, "Lidar2", "*.inno_pc"))
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
        
        # 检查是否存在同名场景
        connection = get_db_connection()
        if not connection:
            return None
        try:
            with connection.cursor() as cursor:
                sql = "SELECT COUNT(*) FROM dm_scene WHERE name = %s"
                cursor.execute(sql, (name,))
                result = cursor.fetchone()
                if result and result[0] > 0:
                    # 存在同名场景，添加时间戳
                    import time
                    name = f"{name}_{int(time.time())}"
        except Exception as e:
            print(f"[错误] 查询场景名称失败: {e}")
            return None
        finally:
            if connection:
                connection.close()
        
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
            # 查询 dm_innopc 表获取 innopc id
            connection = get_db_connection()
            if not connection:
                return None
            try:
                with connection.cursor() as cursor:
                    innopc_ids = []
                    if uuid1:
                        sql = "SELECT id FROM dm_innopc WHERE attach_id = %s  order by create_time desc"
                        cursor.execute(sql, (uuid1,))
                        result = cursor.fetchone()
                        if result:
                            innopc_ids.append(result[0])
                    if uuid2:
                        sql = "SELECT id FROM dm_innopc WHERE attach_id = %s  order by create_time desc"
                        cursor.execute(sql, (uuid2,))
                        result = cursor.fetchone()
                        if result:
                            innopc_ids.append(result[0])
                    print(f"[信息] 获取的 innopc id: {innopc_ids}")
                    return innopc_ids
            except Exception as e:
                print(f"[错误] 查询 innopc id 失败: {e}")
                return None
            finally:
                if connection:
                    connection.close()
        else:
            print(f"[错误] 场景数据提交失败，状态码: {response.status_code}")
            return None
    else:
        print("[错误] 文件上传失败")
        return None

def get_scene_id():
    connection = get_db_connection()
    if not connection:
        return None
    try:    
        with connection.cursor() as cursor:
            sql = "SELECT id FROM dm_scene ORDER BY create_time DESC LIMIT 1"
            cursor.execute(sql)
            result = cursor.fetchone()
            if result:
                scene_id = result[0]
                print(f"[信息] 最新场景 ID: {scene_id}")
                return scene_id
            else:
                print("[错误] 未找到场景记录")
                return None
    except Exception as e:
        print(f"[错误] 查询场景 ID 失败: {e}")
        return None
    finally:
        if connection:
            connection.close()  
    
    
def upload_meta_file_get_attach_id(file_path):
    if isinstance(file_path, list):
        file_path = file_path[0]
    print(f"\n🔧 [上传元数据文件] 文件: {file_path}")
    bucket_name = "meta20250616"
    file_name = os.path.basename(file_path)
    try:
        attach_id = upload_file_to_minio(bucket_name, file_name, file_path)
        return attach_id
    except Exception as e:
        print(f"[错误] 上传文件 {file_path} 失败: {e}")
        return None
def upload_metadata_to_scene(innopc_ids, scene_id,dataset_dir,dataset_name,group_name):
    '''
    上传元数据到场景
    /data/test/QLG_001_2_FK_PR$ tree
    .
    ├── BoxFilterROI
    │   └── qlg_50_150
    │       └── Box_filter_ROI_QLG_PR_0820.yaml
    ├── Flatten
    │   └── 01Parallel.yaml
    ├── Fusion
    │   ├── 1716455427_40s_gt.zip
    │   ├── default
    │   └── fusion.yaml
    ├── Lidar1
    │   ├── default
    │   │   └── qlg_lidar1_roi.yaml
    │   ├── LIDAR_220_18000MB_1716454815C050_6550.inno_pc
    │   ├── qlg_200_200
    │   │   └── qlg_lidar1_roi_modified_200_200_fusion_V2.4.yaml
    │   ├── qlg_50_150
    │   │   └── qlg_lidar1_roi_fusion_V2.0.yaml
    │   └── test
    │       └── qlg_lidar1_roi.yaml
    ├── Lidar2
    │   ├── default
    │   │   └── qlg_lidar2_roi.yaml
    │   ├── LIDAR_221_18000MB_1716454815_6050_6550.inno_pc
    │   ├── qlg_200_200
    │   │   └── qlg_lidar2_roi_modified_200_200_fusion_V2.4.yaml
    │   ├── qlg_50_150
    │   │   └── qlg_lidar2_roi_fusion_V2.0.yaml
    │   └── test
    │       └── qlg_lidar2_roi.yaml
    ├── ParamServer
    │   ├── qlg_200_200
    │   │   ├── params_multi.yaml
    │   │   └── params.yaml
    │   └── qlg_50_150
    │       ├── params_multi.yaml
    │       └── params.yaml
    ├── scene_config.yaml
    └── static_map
        └── static_5_result.pcd

    19 directories, 20 files

        封装成的json如下 
        {
        "name": "QLG_001_2_FK_PR_MetaGroup_qlg_50_150",
        "metaIds": [],
        "metas": [
            {
            "attachId": "1983771157453922306",
            "type": "lidar_zone",
            "innopcId": "1983766189883842561"
            },
            {
            "attachId": "1983771214299324417",
            "type": "lidar_zone",
            "innopcId": "1983766189892231169"
            },
            {
            "attachId": "1983771357232816131",
            "type": "flatten"
            },
            {
            "attachId": "1983771433812418562",
            "type": "fusion"
            },
            {
            "attachId": "1983771564121055234",
            "type": "params"
            },
            {
            "attachId": "1983771633033469954",
            "type": "label_zone"
            },
            {
            "attachId": "1983771705087418370",
            "type": "static_map_pcd"
            }
        ],
        "sceneId": "1983766189875453953"
        }
    '''
    if not scene_id:
        print("[错误] 无效的场景 ID，无法上传元数据")
        return
    meta_group_data = {
        "name": group_name,
        "metaIds": [],
        "metas": [],
        "sceneId": scene_id
    }
    # 1. event_gt/default/stop_bar.csv

    # 2. Flatten/*.yaml
    flatten_yaml = glob.glob(os.path.join(dataset_dir, "Flatten", "*.yaml"))
    flatten_yaml_id = None
    if flatten_yaml:
        flatten_yaml_id = upload_meta_file_get_attach_id(flatten_yaml[0])
    else:
        print("[⚠️] 未找到 Flatten YAML")
    if flatten_yaml_id:
        flatten_yaml_json =  {
        "attachId": flatten_yaml_id,
        "type": "flatten"
        }
        meta_group_data["metas"].append(flatten_yaml_json)
    

    # 3. Fusion/default/*.yaml
    fusion_yaml = glob.glob(os.path.join(dataset_dir, "Fusion", group_name, "*.yaml"))
    fusion_yaml_id = None
    if not fusion_yaml:
        fusion_yaml = glob.glob(os.path.join(dataset_dir, "Fusion", "*.yaml"))
    if fusion_yaml:
        fusion_yaml_id = upload_meta_file_get_attach_id(fusion_yaml[0])
    else:
        print("[⚠️] 未找到 Fusion YAML")
    if fusion_yaml_id:
        fusion_yaml_json =  {
        "attachId": fusion_yaml_id,
        "type": "fusion"
        }       
        meta_group_data["metas"].append(fusion_yaml_json)

 

    # 5. Lidar1/default/*.yaml
    lidar1_roi = glob.glob(os.path.join(dataset_dir, "Lidar1", group_name, "*.yaml"))
    if not lidar1_roi:
        lidar1_roi = glob.glob(os.path.join(dataset_dir, "Lidar1", "*.yaml"))
    lidar1_roi_id = None
    if lidar1_roi:    
        idar1_roi_id = upload_meta_file_get_attach_id(lidar1_roi[0])
    else:
        print("[⚠️] 未找到 Lidar1 ROI YAML 文件")
    if idar1_roi_id:
        lidar1_roi_json =  {
        "attachId": idar1_roi_id,
        "type": "lidar_zone",       
        "innopcId": innopc_ids[0] if innopc_ids else None
        }
        meta_group_data["metas"].append(lidar1_roi_json)
    

    # 6. Lidar2/default/*.yaml
    lidar2_roi = glob.glob(os.path.join(dataset_dir, "Lidar2", group_name, "*.yaml"))
    if not lidar2_roi:
        lidar2_roi = glob.glob(os.path.join(dataset_dir, "Lidar2", "*.yaml"))
    lidar2_roi_id = None
    if lidar2_roi:
        lidar2_roi_id = upload_meta_file_get_attach_id(lidar2_roi[0])
    else:
        print("[⚠️] 未找到 Lidar2 ROI YAML 文件")
    if lidar2_roi_id:
        lidar2_roi_json =  {
        "attachId": lidar2_roi_id,
        "type": "lidar_zone",       
        "innopcId": innopc_ids[1] if len(innopc_ids) >1 else None
        }
        meta_group_data["metas"].append(lidar2_roi_json)

    # 7. ParamServer/default/params_*.yaml
    param_dir = glob.glob(os.path.join(dataset_dir, "ParamServer", group_name,"*.yaml"))
    if not param_dir:
        param_dir = glob.glob(os.path.join(dataset_dir, "ParamServer", "*.yaml"))
    param_id = None
    if param_dir:       
        param_id = upload_meta_file_get_attach_id(param_dir[0])
    else:
        print("[⚠️] 未找到 ParamServer YAML 文件")
    if param_id:
        param_json =  {
        "attachId": param_id,
        "type": "params"
        }       
        meta_group_data["metas"].append(param_json)
    # 8. static_map/static_*.pcd
    static_map_pcd = glob.glob(os.path.join(dataset_dir, "static_map",group_name, "*.pcd"))
    if not static_map_pcd:
        static_map_pcd = glob.glob(os.path.join(dataset_dir, "static_map", "*.pcd"))
    static_map_pcd_id = None
    if static_map_pcd:
        static_map_pcd_id = upload_meta_file_get_attach_id(static_map_pcd[0])
    else:
        print("[⚠️] 未找到 static_map PCD 文件")
    if static_map_pcd_id:
        static_map_pcd_json =  {
        "attachId": static_map_pcd_id,
        "type": "static_map_pcd"
        }
        meta_group_data["metas"].append(static_map_pcd_json)
        
    # 9. label_zone (可选，视具体需求添加)      
    label_zone_file = glob.glob(os.path.join(dataset_dir, "BoxFilterROI", group_name, "*.yaml"))
    if not label_zone_file:
        label_zone_file = glob.glob(os.path.join(dataset_dir, "BoxFilterROI", "*.yaml"))
    label_zone_id = None    
    if label_zone_file:   
        label_zone_id = upload_meta_file_get_attach_id(label_zone_file)
        if label_zone_id:
            label_zone_json =  {
            "attachId": label_zone_id,
            "type": "label_zone"
            }
            meta_group_data["metas"].append(label_zone_json)
    else:
        print("[⚠️] 未找到 LabelZone YAML 文件")
    
    metadata_json = json.dumps(meta_group_data)
    print(f"[信息] 准备上传元数据到场景 ID {scene_id}")
    print(f"[信息] 元数据 JSON: {metadata_json}")
    url = f"http://localhost/dmapi/group"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, data=metadata_json, headers=headers)
    print(response.text)
    print(response.status_code)
    if response.status_code == 200:
        print("[信息] 元数据上传成功")
    else:
        print(f"[错误] 元数据上传失败，状态码: {response.status_code}")
        
        
# ======================
# 4. 主程序：遍历数据集并分发处理
# ======================
def process_dataset(dataset_name ,dataset_dir):
    print("=" * 50)
    print(f"🔍 正在处理数据集目录: {dataset_dir}")
    print("=" * 50)
    innopc_ids = upload_innopc_generat_scene(dataset_name ,dataset_dir)
    scene_id = get_scene_id()
    
    lidar1_path = os.path.join(dataset_dir, "Lidar1")
    # 遍历 Lidar1 下的所有文件夹，每个文件夹作为一个 group_name !!!
    group_names = [d for d in os.listdir(lidar1_path) if os.path.isdir(os.path.join(lidar1_path, d))]
    for group_name in group_names:
        print(f"[信息] 处理分组: {group_name}")
        upload_metadata_to_scene(innopc_ids,scene_id,dataset_dir,dataset_name ,group_name)
        
    return
   

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



def mount_nas():
        """
        挂载 NAS 存储到本地目录 /mnt
        """
        nas_path = "//172.16.98.52/inno_test_storage"
        mount_point = "/mnt"
        username = "share"
        password = "a12345678"
        command = f"sudo mount -t cifs {nas_path} {mount_point} -o username={username},password={password}"
        try:
            os.system(command)
            print(f"[信息] NAS 挂载成功: {nas_path} -> {mount_point}")
        except Exception as e:
            print(f"[错误] NAS 挂载失败: {e}")
            return False
        return True
#'Lidar1', 'static_map', 'ParamServer', 'Lidar2', 'InnoPCClient', 'Lidar3', 'BoxFilterROI', 'Fusion', 'scene_config.yaml', 'Lidar4', 'Flatten'
folders_types = ['Lidar1', 'static_map', 'ParamServer', 'Lidar2', 'Lidar3', 'BoxFilterROI', 'Fusion', 'Lidar4', 'Flatten','event_gt']

def meta_group_analysis(dataset_path):
    print("\n"+f"[信息] meta group 分析: {dataset_path}")  # for if condition test
    # print("\n"+f"[信息] 未处理文件: {dataset_path}")   # for else condition test
    for type_folder_name in os.listdir(dataset_path):
        if type_folder_name  in folders_types:
            type_folder = os.path.join(dataset_path, type_folder_name)
            if os.path.isdir(type_folder):
                sub = []
                for meta_group_name in os.listdir(type_folder):
                    if(os.path.isdir(os.path.join(type_folder,meta_group_name))):
                        # print(meta_group_name)
                        sub.append(meta_group_name)
                print("  ->["+type_folder_name+"], size="+str(len(sub))+" , detail: "+str(sub))
        # else:
        #      print(f"   -> {type_folder_name} ")
    
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

    # 1. 挂载 NAS
    # if not mount_nas():
    #     return
    
    # BASE_DIR = "/mnt/AIDataSet"
    BASE_DIR = "/home/demo/data/test"  # For testing
    if not os.path.isdir(BASE_DIR):
        print(f"[错误] 数据集根目录不存在: {BASE_DIR}")
        return
    innopc_empty_folder = os.path.join(os.getcwd(), "analysis/innopc_empty.txt")
    # 遍历 BASE_DIR 下的每个数据集文件夹（如 A01_001_2_FK_S）
    for item in os.listdir(BASE_DIR):
        dataset_path = os.path.join(BASE_DIR, item)
        #  !!!只运行一次 检查 Lidar1 和 Lidar2 目录下是否有 .inno_pc 文件, 生成 analysis/innopc_empty.txt
        # check_inno_pc_files(dataset_path,innopc_empty_folder)
        is_empty_innopc = os.path.basename(dataset_path) not in open(innopc_empty_folder, "r").read().splitlines()
        
        if os.path.isdir(dataset_path) and is_empty_innopc:
            #  !!!只运行一次 meta group 分析， 生成 analysis/meta_group_analysis.txt 和 analysis/not_handle_yet.txt
            # meta_group_analysis(dataset_path)   
            process_dataset(item,dataset_path)
        else:
            print(f"[跳过] 空目录或者缺失 innopc 文件: {dataset_path}")
        

if __name__ == "__main__":
    main()