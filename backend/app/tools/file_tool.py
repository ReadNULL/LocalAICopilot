import os
from langchain_core.tools import tool


@tool
def read_local_file(file_path: str) -> str:
    """读取本地文件的内容。提供绝对路径或相对路径。"""
    try:
        if not os.path.exists(file_path):
            return f"错误：文件 {file_path} 不存在。"
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"读取文件失败: {str(e)}"


@tool
def list_directory(directory_path: str = ".") -> str:
    """列出指定目录下的所有文件和文件夹。"""
    try:
        if not os.path.exists(directory_path):
            return f"错误：目录 {directory_path} 不存在。"
        items = os.listdir(directory_path)
        return "\n".join(items) if items else "目录为空。"
    except Exception as e:
        return f"列出目录失败: {str(e)}"


@tool
def write_local_file(file_path: str, content: str) -> str:
    """将内容写入本地文件。如果文件所在目录不存在会自动创建，如果文件存在则覆盖。"""
    try:
        # 获取目录路径，确保它存在
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"成功：内容已写入 {file_path}"
    except Exception as e:
        return f"写入文件失败: {str(e)}"