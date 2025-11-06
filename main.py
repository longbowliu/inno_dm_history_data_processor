import os
import glob
import yaml  # 需要安装 PyYAML: pip install pyyaml
import csv
import json
import requests
from minio_upload_innopc import upload_file_to_minio ,id_generator
from minio_upload_innopc import get_db_connection, get_sl_connection


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
    print(f"\n🔧 每一个meta group 除了自己的配置外还需要加载其他共用的基础配置，比如拉平、融合等。如果没有该分组，则该配置会作为共用配置")
    if not scene_id:
        print("[错误] 无效的场景 ID，无法上传元数据")
        return
    meta_group_data = {
        "name": group_name,
        "metaIds": [],
        "metas": [],
        "sceneId": scene_id
    }
    # 1. 查找所有子目录中的 .zip 文件
    zip_files = glob.glob(os.path.join(dataset_dir, "**", "*.zip"), recursive=True)
    if zip_files:
        print(f"[信息] 找到以下 .zip 文件: {zip_files}")
    else:
        print("[⚠️] 未找到 .zip 文件")

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
    

    # 3. Fusion/**/*.yaml
    fusion_zone_yaml = glob.glob(os.path.join(dataset_dir, "Fusion", group_name, "*.yaml"))
    fusion_zone_id = None
    if  fusion_zone_yaml:
        fusion_zone_id = upload_meta_file_get_attach_id( fusion_zone_yaml[0])
        
    if fusion_zone_id:
        fusion_zone_json =  {
        "attachId": fusion_zone_id,
        "type": "fusion_zone"
        }       
        meta_group_data["metas"].append(fusion_zone_json)
        
    # Fusion/*.yaml    
    fusion_yaml_id = None
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

 

    # 5. Lidar1/**/*.yaml
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
    

    # 6. Lidar2/**/*.yaml
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
        "innopcId": innopc_ids[1] if innopc_ids and len(innopc_ids) >1 else None
        }
        meta_group_data["metas"].append(lidar2_roi_json)

    # 7. ParamServer/**/params_*.yaml
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
        
    #10. other, scene_config.yaml
    scene_config_id = None
    scene_config = glob.glob(os.path.join(dataset_dir, "**", "scene_config.yaml"), recursive=True)
    if scene_config:
        scene_config_id = upload_meta_file_get_attach_id(scene_config[0])
    else:
        print("[⚠️] 未找到 Fusion YAML")
    if scene_config_id:
        scene_config_json =  {
        "attachId": scene_config_id,
        "type": "other"
        }       
        meta_group_data["metas"].append(scene_config_json)
        
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
    meta_group_names = [d for d in os.listdir(lidar1_path) if os.path.isdir(os.path.join(lidar1_path, d))]
    group_id_default = None
    group_id = None
    # GT 默认关联default meta_group, 根据分析,每个数据集中只存在一个GT zip 文件(一般存在于 dataset_dir/或者 dataset_dir/Fusion/ 下) 
    # 如果不存在default group，则意味着只有一组meta_group，关联GT数据到该group_id
    group_records = [] 
    for group_name in meta_group_names:
        print(f"[信息] 处理分组: {group_name}")
        upload_metadata_to_scene(innopc_ids,scene_id,dataset_dir,dataset_name ,group_name)
        group_id = find_group_id_by_name_and_scene_id(scene_id, group_name)
        group_records.append((group_name, group_id))
        if group_name == "default" :
            group_id_default = group_id
    if group_id_default:
        group_id = group_id_default
    requirement_id = create_requirements( dataset_name, group_id, scene_id)
    
    zip_files = glob.glob(os.path.join(dataset_dir, "**", "*.zip"), recursive=True)
    if zip_files:
        print(f"[信息] 找到以下 .zip 文件: {zip_files}")
        gt_file = zip_files[0]
        upload_gt(gt_file,requirement_id)
    else:
        print("[⚠️] 未找到 .zip GT文件")
    manual = False
    for group_name, group_id in group_records:
        event_csv_files = glob.glob(os.path.join(dataset_dir, "event_gt", group_name, "*.csv"))
        for event_csv_file in event_csv_files:
            event_type = None
            if event_csv_file.endswith("advance_detection.csv"):
                event_type = "advance_detection"
            elif event_csv_file.endswith("stop_bar.csv"):
                event_type = "stop_bar"
            else:
                print(f"[⚠️] 未知的事件文件类型: {event_csv_file}")
                continue    
            print(f"[信息] 处理事件文件: {event_csv_file} for group: {group_name}")
              
            upload_event_by_group(requirement_id,event_csv_file,event_type,group_id,manual)
            
def upload_event_by_group(equirement_id,event_csv_file,event_type,group_id,manual=False):
    
    print(f"\n🔧 [上传 Event 文件] 文件: {event_csv_file}, 需求 ID: {equirement_id}, 事件类型: {event_type}")
    file_name = os.path.basename(event_csv_file)
    
    try:    
        # 构造 multipart/form-data 请求
        url = "http://localhost/dmapi/cognition-truth/upload"
        data = {
            "requirementId": equirement_id,
            "eventType": event_type,
            "groupId": group_id,
            "manual": manual
        }
        
        with open(event_csv_file, 'rb') as f:
            files = {'file': (file_name, f, 'text/csv')}
            response = requests.post(url, data=data, files=files)
            print(response.text)
            print(f"[信息] 状态码: {response.status_code}")
            if response.status_code == 200:
                print("[信息] Event 文件提交成功")
                return True
            else:
                print(f"[错误] Event 文件提交失败，状态码: {response.status_code}")
                return False
    except Exception as e:
        print(f"[错误] 上传 Event 文件时发生错误: {e}")
        return False    
    
    

        
    return

def upload_gt(gt_file, requirement_id):
    """
    上传 GT 文件到后端接口
    param file: GT zip文件路径
    param requirement_id: 需求 ID
    return: 上传结果（成功或失败）
    """
    print(f"\n🔧 [上传 GT 文件] 文件: {gt_file}, 需求 ID: {requirement_id}")
    # bucket_name = "gt-files"
    file_name = os.path.basename(gt_file)
    # 解压gt_file,遍历其中.txt文件的数量作为frame_count,汇总每个.txt文件中的行数（每行为一个box）作为box_count。
    # 如果gt_file中没有.txt文件，则box_count和frame_count为-1 ，最后删除解压的文件夹
    box_count = 0
    frame_count = 0
    import zipfile
    import shutil
    temp_extract_dir = os.path.join(os.path.dirname(gt_file), "temp_gt_extract")
    try:
        with zipfile.ZipFile(gt_file, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
        txt_files = glob.glob(os.path.join(temp_extract_dir, "**", "*.txt"), recursive=True)
        frame_count = len(txt_files)
        for txt_file in txt_files:
            with open(txt_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                box_count += len(lines)
        print(f"[信息] 计算得到 frame_count: {frame_count}, box_count: {box_count}")
    except Exception as e:
        print(f"[错误] 计算 GT 文件信息失败: {e}")
    finally:
        if os.path.isdir(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)       
    
    
    try:

        # 构造 multipart/form-data 请求
        url = "http://localhost/dmapi/perception-truth/upload"
        data = {
            "requirementId": requirement_id,
            "boxCount": box_count,
            "frameCount": frame_count
        }
        
        with open(gt_file, 'rb') as f:
            files = {'file': (file_name, f, 'application/zip')}
            response = requests.post(url, data=data, files=files)
            print(response.text)
            print(f"[信息] 状态码: {response.status_code}")
            if response.status_code == 200:
                print("[信息] GT 文件提交成功")
                return True
            else:
                print(f"[错误] GT 文件提交失败，状态码: {response.status_code}")
                return False

        
    except Exception as e:
        print(f"[错误] GT 文件上传或提交失败: {e}")
        return False
        



def create_requirements(dataset_name, group_id, scene_id):
    '''
    插入数据到 ad_sl_requirement 和 dm_requirement_scene_group 表中
    '''
    if not group_id or not scene_id:
        print("[错误] 无效的 group ID 或 scene ID，无法创建需求文件")
        return
    requirement_id = None
    requirement_scene_group_id = None
    # 获取数据库连接
    connection = get_sl_connection()
    if not connection:
        print("[错误] 无法获取数据库连接")
        return

    try:
        with connection.cursor() as cursor:
            # 插入数据到 ad_sl_requirement 表
            requirement_sql = """
                INSERT INTO ad_sl_requirement (name, config_id, priority, simpl_version, lost_info, create_time, update_time,is_deleted)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW(),1)
            """
            cursor.execute(requirement_sql, (
                f"{dataset_name}_demand",  # name
                "1792801536928169986",     # config_id
                3,                          # priority
                "SIMPL_2_6",               # simpl_version
                None                        # lost_info
            ))
            requirement_id = cursor.lastrowid
            print(f"[信息] 插入 ad_sl_requirement 表成功，ID: {requirement_id}")
        # 提交事务
        connection.commit()
        print("[信息] 需求文件创建成功")

    except Exception as e:
        print(f"[错误] 数据库操作失败: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()   
            
     # 获取数据库连接
    connection = get_db_connection()
    if not connection:
        print("[错误] 无法获取数据库连接")
        return

    try:
        with connection.cursor() as cursor:
            # 插入数据到 ad_sl_requirement 表

            # 插入数据到 dm_requirement_scene_group 表
            requirement_scene_group_sql = """
                INSERT INTO dm_requirement_scene_group (id, requirement_id, scene_id, group_id, create_time, update_time)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(requirement_scene_group_sql, (
                id_generator.generate_id(),  # id
                requirement_id,    # requirement_id
                scene_id,          # scene_id
                group_id           # group_id
            ))
            print("[信息] 插入 dm_requirement_scene_group 表成功")

        # 提交事务
        connection.commit()
        print("[信息] 需求文件创建成功")
        return requirement_id

    except Exception as e:
        print(f"[错误] 数据库操作失败: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()   
        
        
def find_group_id_by_name_and_scene_id(scene_id, group_name):
    connection = get_db_connection()
    if not connection:
        return None
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id FROM dm_group WHERE scene_id = %s AND name = %s ORDER BY create_time DESC LIMIT 1"
            cursor.execute(sql, (scene_id, group_name))
            result = cursor.fetchone()
            if result:
                group_id = result[0]
                print(f"[信息] 元数据分组 ID: {group_id}")
                return group_id
            else:
                print("[错误] 未找到元数据分组记录")
                return None
    except Exception as e:
        print(f"[错误] 查询元数据分组 ID 失败: {e}")
        return None
    finally:
        if connection:
            connection.close()
            

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
   
    # 1. 挂载 NAS
    # if not mount_nas():
    #     return
    
    # BASE_DIR = "/mnt/AIDataSet"
    BASE_DIR = "/home/demo/data/test"  # For testing
    if not os.path.isdir(BASE_DIR):
        print(f"[错误] 数据集根目录不存在: {BASE_DIR}")
        return
    innopc_empty_folder = os.path.join(os.getcwd(), "analysis/innopc_empty.txt")
    # 预加载 innopc_empty.txt 文件内容到集合
    with open(innopc_empty_folder, "r") as f:
        empty_innopc_set = set(line.strip() for line in f)
    
    
    processed_folder = os.path.join(os.getcwd(), "analysis/processed_datasets.txt")
    # 预加载 innopc_empty.txt 文件内容到集合
    with open(processed_folder, "r") as f:
        processed_set = set(line.strip() for line in f)
        
    # 遍历 BASE_DIR 下的每个数据集文件夹（如 A01_001_2_FK_S）
    for item in os.listdir(BASE_DIR):
        dataset_path = os.path.join(BASE_DIR, item)
        #  !!!只运行一次 检查 Lidar1 和 Lidar2 目录下是否有 .inno_pc 文件, 生成 analysis/innopc_empty.txt
        # check_inno_pc_files(dataset_path,innopc_empty_folder)
        not_empty_innopc = os.path.basename(dataset_path) not in empty_innopc_set
        not_processed = os.path.basename(dataset_path) not in processed_set
        if os.path.isdir(dataset_path) and not_empty_innopc and not_processed:
            #  !!!只运行一次 meta group 分析， 生成 analysis/meta_group_analysis.txt 和 analysis/not_handle_yet.txt
            # meta_group_analysis(dataset_path)   
            process_dataset(item,dataset_path)
            # 把item追加到 analysis/processed_datasets.txt 文件中，表示已经处理过该数据集
            processed_datasets_file = os.path.join(os.getcwd(), "analysis/processed_datasets.txt")
            with open(processed_datasets_file, "a") as f:
                f.write(item + "\n")
            print(f"[信息] 数据集处理完成: {dataset_path}") 
        else:
            print(f"[跳过] 空目录或者缺失 innopc 文件: {dataset_path}")
        

if __name__ == "__main__":
    main()