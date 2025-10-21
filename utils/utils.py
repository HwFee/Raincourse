import json
import os


def dateToJsonFile(answer: list, info: dict, file_path: str, file_name: str) -> None:
    """
    将答案写入文件保存为json格式
    :param file_path:
    :param file_name:
    :param answer:
    :param info:
    :return:
    """
    to_dict = {
        f"{file_path}": answer,
        "info": info
    }
    # json.dumps 序列化时对中文默认使用的ascii编码.想输出真正的中文需要指定ensure_ascii=False
    json_data = json.dumps(to_dict, ensure_ascii=False)
    path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    path = os.path.join(path, f"{file_path}", f"{file_name}.json")
    # 没有文件夹就创建文件夹
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, 'w', encoding="utf-8") as f_:
        f_.write(json_data)


def jsonFileToDate(file_path: str, file_name: str) -> dict:
    path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    file = os.path.join(path, f"{file_path}", f"{file_name}")
    with open(file, 'r', encoding="utf-8") as f_:
        json_data = dict(json.loads(f_.read()))
    return json_data


def is_exist_answer_file(file_path: str, work_file_name: str) -> bool:
    answer_files = []
    dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    path = os.path.join(dir_path, f"{file_path}")
    for root, dirs, files in os.walk(path):
        answer_files.append(files)
    if work_file_name in answer_files[0]:
        return True
    else:
        return False


def get_files_in_directory(directory_path):
    """
    读取指定目录中的所有文件名（不包括后缀），并返回一个包含文件信息的列表。

    参数:
    directory_path (str): 要读取的目录的路径

    返回:
    list: 包含文件信息的列表，每个元素是一个字典 {'name': 文件名（不含后缀）}
    """
    try:
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            print(f"错误：'{directory_path}' 不是一个有效的目录。")
            return []

        files = [{'name': os.path.splitext(f)[0]} for f in os.listdir(directory_path)
                 if os.path.isfile(os.path.join(directory_path, f))]
        return files

    except Exception as e:
        print(f"发生错误：{str(e)}")
        return []


def get_exam_files(directory_name):
    """
    扫描指定目录，返回试题文件列表，包括状态信息。

    参数:
    directory_name (str): 要扫描的目录名称（相对于脚本所在目录）

    返回:
    list: 包含文件信息的列表，每个元素是一个字典，格式如下：
          {'name': '文件名（不含后缀）', 'exam_id': '试卷ID', 'exam_name': '试卷名称', 'status': True/False}
    """
    # 获取脚本所在目录的完整路径
    script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    # 构建完整的目录路径
    directory_path = os.path.join(script_dir, directory_name)

    files = {}
    result = []

    try:
        # 扫描目录中的所有文件
        for filename in os.listdir(directory_path):
            if filename.endswith('.json'):
                name_parts = filename.rsplit('_', 1)
                if len(name_parts) == 2:
                    base_name, file_type = name_parts
                    if base_name not in files:
                        files[base_name] = {'question': False, 'answer': False}
                    if file_type.startswith('question'):
                        files[base_name]['question'] = True
                    elif file_type.startswith('answer'):
                        files[base_name]['answer'] = True

        # 生成结果列表
        for base_name, status in files.items():
            answer_file_path = os.path.join(directory_path, f"{base_name}_answer.json")
            exam_name = ''
            if os.path.exists(answer_file_path):
                with open(answer_file_path, 'r', encoding='utf-8') as f:
                    answer_data = json.load(f)
                    exam_name = answer_data.get('info', {}).get('exam_name', '')

            result.append({
                'name': base_name,
                'exam_id': base_name,
                'exam_name': exam_name,
                'status': status['question'] and status['answer']
            })

        # 按文件名排序
        result.sort(key=lambda x: x['name'])
        return result

    except Exception as e:
        print(f"发生错误：{str(e)}")
        return []