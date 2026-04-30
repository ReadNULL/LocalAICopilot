import sys
import io
from langchain_core.tools import tool


@tool
def execute_python_code(code: str) -> str:
    """
    在本地环境中执行 Python 代码并返回控制台的输出(stdout)。
    用于数学计算、数据处理或运行脚本。
    注意：代码应该使用 print() 来输出你想获取的结果。
    """
    # 捕获标准输出，这样大模型就能“看”到 print 的内容
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()

    try:
        # 在一个干净的全局字典中执行代码
        exec(code, globals())
        output = redirected_output.getvalue()
        return output if output else "代码执行成功，但没有产生任何输出 (请确保使用了 print)。"
    except Exception as e:
        return f"代码执行出错:\n{type(e).__name__}: {str(e)}"
    finally:
        # 无论成功失败，必须把标准输出恢复，否则你的 FastAPI 日志会罢工
        sys.stdout = old_stdout