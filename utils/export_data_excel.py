import os
import re
import html
from utils.utils import jsonFileToDate  # 保持原来的导入
import openpyxl
from openpyxl.styles import Alignment, Border, Side, Font, PatternFill


# remove_html_tags 和 base_problem_id_get_answer 函数与之前版本相同
def remove_html_tags(text_input):
    if not isinstance(text_input, str):
        return ""
    text = text_input
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def base_problem_id_get_answer(base_problem_id: str, answer_list: list):
    if not base_problem_id or not isinstance(answer_list, list):
        return None
    for answer_entry in answer_list:
        if isinstance(answer_entry, dict) and answer_entry.get('problem_id') == base_problem_id:
            return answer_entry.get('answer')
    return None


def process_exam_data(exam_id: str):
    exam_question_full_data = jsonFileToDate(f"exam", f"{exam_id}_question.json")
    exam_answer_full_data = jsonFileToDate(f"exam", f"{exam_id}_answer.json")

    exam_question_data = exam_question_full_data.get('exam', {}).get('data', {})
    exam_answer_data = exam_answer_full_data.get('exam', {}).get('data', {})

    problems = exam_question_data.get('problems', [])
    problem_results = exam_answer_data.get('problem_results', [])

    question_data_list = []

    for question in problems:
        if not isinstance(question, dict):
            print(f"Warning: Skipping invalid question entry: {question}")
            continue

        question_data = {
            "question_type": "未知",
            "exam_question": "题目内容缺失",
            "question_options": [],
            "question_answer": "答案信息缺失",  # 将在此处填充 A, B, C, D 等
            "question_analysis": "解析缺失"
        }

        try:
            problem_id = question.get('problem_id')
            type_text = question.get('TypeText', '未知题型')

            question_data['exam_question'] = remove_html_tags(question.get('Body', ''))
            question_data['question_analysis'] = remove_html_tags(question.get('Remark', ''))

            raw_answer_keys_from_json = base_problem_id_get_answer(problem_id,
                                                                   problem_results)  # e.g., ["A"] or ["B", "D"]

            options_list = question.get('Options', [])
            # 选项文本仍然需要提取用于Excel的 "选项A", "选项B" 等列
            question_data['question_options'] = [remove_html_tags(opt.get('value', '')) for opt in options_list if
                                                 isinstance(opt, dict)]

            if type_text == "单选题" or type_text == "多选题":
                question_data['question_type'] = "1" if type_text == "单选题" else "2"

                if raw_answer_keys_from_json and isinstance(raw_answer_keys_from_json,
                                                            list) and raw_answer_keys_from_json:
                    correct_option_letters = []
                    for answer_key in raw_answer_keys_from_json:  # Iterate through keys like "A", "B"
                        found_option_at_index = -1
                        for index, option_item in enumerate(options_list):
                            if isinstance(option_item, dict) and option_item.get("key") == answer_key:
                                found_option_at_index = index
                                break

                        if found_option_at_index != -1:
                            # Convert index (0, 1, 2, 3...) to letter (A, B, C, D...)
                            # chr(65) is 'A'
                            correct_option_letters.append(chr(ord('A') + found_option_at_index))
                        else:
                            # Handle case where a key in "Answer" is not found in "Options" keys
                            correct_option_letters.append(f"[{answer_key}-答案键未在选项中匹配]")

                    question_data['question_answer'] = ", ".join(correct_option_letters)
                elif raw_answer_keys_from_json is None:
                    question_data['question_answer'] = "该题答案未获取"
                else:
                    question_data['question_answer'] = f"答案键列表格式错误: {raw_answer_keys_from_json}"

            elif type_text == "判断题":
                question_data['question_type'] = "3"
                # 判断题的答案通常是 'true'/'false' 或直接用 'A'/'B' 代表
                # export_excel 函数会处理这个
                question_data['question_answer'] = raw_answer_keys_from_json

            elif type_text == "填空题":
                question_data['question_type'] = "4"
                question_data['question_answer'] = raw_answer_keys_from_json

            else:
                print(f"Warning: Unknown question type '{type_text}' for problem_id '{problem_id}'")
                question_data['question_type'] = type_text
                question_data['exam_question'] = f"未知题型 ({type_text}): {question_data['exam_question']}"

        except Exception as e:
            print(f"Error processing question (problem_id: {question.get('problem_id', 'N/A')}): {e}")
            question_data['exam_question'] = f"处理问题时发生错误: {e}"

        question_data_list.append(question_data)

    return question_data_list


# export_excel 函数保持不变，因为它现在会接收已经转换好的字母作为答案
def export_excel(exam_id: str, exam_name: str):
    exam_data_list = process_exam_data(exam_id)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = exam_name

    headers = ['题型', '试题标题', '题目', '选项A', '选项B', '选项C', '选项D', '选项E', '选项F', '正确答案', '解析']
    ws.append(headers)

    for question_item in exam_data_list:
        if not isinstance(question_item, dict):
            print(f"Skipping invalid question data: {question_item}")
            continue

        row_data = [
            question_item.get('question_type', '未知'),
            exam_name,
            question_item.get('exam_question', '题目内容缺失')
        ]

        options_for_excel = question_item.get('question_options', [])  # 这是选项的文本列表
        row_data.extend(options_for_excel + [''] * (6 - len(options_for_excel)))

        correct_answer_display = "答案处理错误"
        answer_data_from_processing = question_item.get('question_answer')  # 这现在是字母 "D" 或 "B, D" 等
        q_type = question_item.get('question_type')

        if q_type == '1' or q_type == '2':  # 单选题或多选题
            # answer_data_from_processing 已经是我们想要的字母或字母组合了
            if isinstance(answer_data_from_processing, str):
                correct_answer_display = answer_data_from_processing
            elif answer_data_from_processing is None or answer_data_from_processing == "该题答案未获取":
                correct_answer_display = answer_data_from_processing if answer_data_from_processing is not None else "答案未获取"
            else:  # 应该不会到这里，因为 process_exam_data 应该返回字符串
                correct_answer_display = f"答案格式非预期: {answer_data_from_processing}"

        elif q_type == '3':  # 判断题
            if isinstance(answer_data_from_processing, list) and len(answer_data_from_processing) > 0:
                val = str(answer_data_from_processing[0]).lower()
                if val == 'true':
                    correct_answer_display = 'A'  # 或者 '正确'
                elif val == 'false':
                    correct_answer_display = 'B'  # 或者 '错误'
                else:  # 如果答案直接是 'A' 或 'B'
                    if val.upper() in ['A', 'B']:
                        correct_answer_display = val.upper()
                    else:
                        correct_answer_display = f"未知判断值: {answer_data_from_processing[0]}"
            elif answer_data_from_processing is None:
                correct_answer_display = "该题答案未获取"
            else:
                correct_answer_display = f"判断题答案格式错误: {answer_data_from_processing}"

        elif q_type == '4':  # 填空题
            if isinstance(answer_data_from_processing, dict):
                try:
                    sorted_keys = sorted(answer_data_from_processing.keys(), key=lambda k: int(k) if k.isdigit() else k)
                    correct_answer_parts = [
                        f"【{answer_data_from_processing[key][0] if isinstance(answer_data_from_processing.get(key), list) and answer_data_from_processing[key] else (answer_data_from_processing.get(key) if isinstance(answer_data_from_processing.get(key), str) else '')}】"
                        for key in sorted_keys]
                    correct_answer_display = ''.join(correct_answer_parts)
                except Exception:
                    correct_answer_parts = [
                        f"【{v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else '')}】" for v in
                        answer_data_from_processing.values()]
                    correct_answer_display = ''.join(correct_answer_parts)
            elif isinstance(answer_data_from_processing, list):
                correct_answer_parts = [
                    f"【{item[0] if isinstance(item, list) and item else (item if isinstance(item, str) else '')}】" for
                    item in answer_data_from_processing]
                correct_answer_display = ''.join(correct_answer_parts)
            elif answer_data_from_processing is None:
                correct_answer_display = "该题答案未获取"
            else:
                correct_answer_display = f"填空题答案格式错误: {answer_data_from_processing}"

        elif answer_data_from_processing == "答案信息缺失" or answer_data_from_processing == "该题答案未获取":
            correct_answer_display = answer_data_from_processing

        row_data.append(correct_answer_display)
        row_data.append(question_item.get('question_analysis', '解析缺失'))
        ws.append(row_data)

    current_path = os.getcwd()
    excel_dir = os.path.join(current_path, "excel")
    if not os.path.exists(excel_dir):
        try:
            os.makedirs(excel_dir)
        except OSError as e:
            print(f"创建目录 {excel_dir} 失败: {e}. 将尝试保存在当前目录。")
            excel_dir = current_path

    file_name = f"{exam_name}.xlsx"
    full_path = os.path.join(excel_dir, file_name)

    try:
        wb.save(full_path)
        print(f"Excel 文件 '{full_path}' 已成功创建。")
    except Exception as e:
        print(f"保存 Excel 文件 '{full_path}' 失败: {e}")

# 示例用法注释掉，因为依赖外部文件
# if __name__ == '__main__':
#     test_exam_id = "your_exam_id"
#     test_exam_name = "Your Exam Name"
#     export_excel(test_exam_id, test_exam_name)