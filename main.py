import threading
import re
import concurrent.futures
import jieba
import nltk
from nltk.tokenize import sent_tokenize
import requests
import json
import queue
import io
import os
from chardet.universaldetector import UniversalDetector
from docx import Document
rawtext = read_text("Path/to/input.txt") #输入的参考文档，支持txt、doc、docx
topic = 'The topic of you article' #你想要写作的题目，注意不需要书名号《》，直接写即可
file_path = "Path/to/save.txt" #输出文档保存的路径


def convert_to_utf8(text):
    detector = UniversalDetector()
    detector.feed(text)
    detector.close()
    if detector.result['encoding'] != 'utf-8':
        text = text.decode(detector.result['encoding']).encode('utf-8')
    return text

def read_text(filepath):
    ext = os.path.splitext(filepath)[-1].lower()
    if ext == ".txt":
        with open(filepath, "rb") as f:
            text = f.read()
            text = convert_to_utf8(text)
            return text.decode('utf-8')
    elif ext in [".docx", ".doc"]:
        doc = Document(filepath)
        text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        return text
    else:
        raise ValueError("Unsupported file format: {}".format(ext))



#摘要部份

#判断文本语言
def is_chinese(text):
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

#摘要
def summarize(text):
    # Step 1
    beginning = text[:1000].rsplit(' ', 1)[0] if not is_chinese(text) else text[:500]

    # Step 2
    ending = text[-1000:].split(' ', 1)[-1] if not is_chinese(text) else text[-500:]

    # Step 3
    summary = ""
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        if paragraph:
            if is_chinese(paragraph):
                sentences = list(jieba.cut(paragraph))
                summary += sentences[0] + ' ' + sentences[-1] + ' '
            else:
                sentences = sent_tokenize(paragraph)
                summary += sentences[0] + ' ' + sentences[-1] + ' '

    summary_slices = []
    while len(summary) > 1000:
        slice_end = summary[:1000].rsplit(' ', 1)[0] if not is_chinese(summary) else summary[:500]
        summary_slices.append(slice_end)
        summary = summary[len(slice_end) + 1:]

    if summary:
        summary_slices.append(summary)

    # Step 4
    result = [beginning, ending] + summary_slices
    return result

#需要示例的聊天函数，用于需要有严格格式要求的输出
def rwkv_chat(user_message,Template_q,Template_a):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_OPENAI_API_KEY"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": Template_q},
            {"role": "assistant", "content": Template_a},
            {"role": "user", "content": user_message}
        ]
    }

    response = requests.post("https://rwkv.ai-creator.net/chntuned/v1/chat/completions", headers=headers, json=data)
    response_json = response.json()

    # 提取助手的回复
    assistant_reply = response_json["choices"][0]["message"]["content"]
    return assistant_reply



def rwkv_chat_s(user_message):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_OPENAI_API_KEY"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    response = requests.post("https://rwkv.ai-creator.net/chntuned/v1/chat/completions", headers=headers, json=data)

    # Print response content for debugging
    print("Response status code:", response.status_code)
    print("Response content:", response.content)

    # Check if response is not empty before parsing it as JSON
    if response.content.strip():
        try:
            response_json = response.json()

            # Extract the assistant's reply
            assistant_reply = response_json["choices"][0]["message"]["content"]
            return assistant_reply

        except Exception as e:
            print(f"Error while extracting the assistant's reply: {e}")
            return ""
    else:
        return "No reply from the server"  # or any default value you think is appropriate



def get_main_point(text):
    point_format = """
    请用以下格式输出，不要输出多余的东西：
    {
      观点1：“这里是文档的第一个观点”
      观点2：“这里是文档的第二个观点”
      观点3：“这里是文档的第三个观点”
    }
    """
    Tq = """
    你是一位信息处理专家，请在以下文档中提取5个观点：“题目：人工智能对法律领域的影响与挑战

    摘要：  
    随着人工智能（AI）技术的快速发展和广泛应用，它已经开始深刻地影响到各个领域，包括法律领域。本论文旨在探讨人工智能对法律领域的影响和挑战，并提出一些应对策略。首先，我们将概述人工智能在法律领域的应用，包括智能合同、法律研究、司法决策和法律服务等方面的运用。其次，我们将讨论人工智能对法律行业的影响，包括加速信息处理、提高效率、降低成本、改善法律决策的准确性等方面的影响。然后，我们将探讨人工智能在法律领域所面临的挑战，包括隐私和数据保护、道德和伦理问题、法律责任和监管等方面的挑战。最后，我们将提出应对策略，包括建立适应人工智能的法律框架、加强教育和培训、加强监管和合规等方面的策略。通过深入研究和探讨，我们可以更好地理解人工智能对法律领域的影响，并提出合理有效的对策，以确保人工智能在法律领域的应用能够发挥其最大的潜力，同时保护公众利益和法律体系的稳定性。

    关键词：人工智能，法律领域，应用，影响，挑战，对策

    一、引言  
    人工智能（AI）作为一种新兴技术，正在以惊人的速度改变着社会各个领域。在法律领域，人工智能的应用已经取得了令人瞩目的成就。然而，与之同时，人工智能也带来了一系列的挑战和问题。本论文旨在系统地探讨人工智能对法律领域的影响和挑战，并提出相应的对策。

    二、人工智能在法律领域的应用

    智能合同：通过人工智能技术，智能合同的生成和执行变得更加高效和准确。  
    法律研究：人工智能可以帮助律师和研究人员更快地获取和分析大量的法律文献和案例。  
    司法决策：人工智能可以辅助法官进行案件分析和决策，提高司法效率和公正性。  
    法律服务：人工智能可以为律师事务所和法律服务机构提供自动化的服务，从而降低成本和提高效率。  
    三、人工智能对法律行业的影响

    加速信息处理：人工智能可以高效处理大量的法律信息和数据，加快法律程序和决策的速度。  
    提高效率：人工智能可以自动化许多繁琐的法律任务，节省律师的时间和精力。  
    降低成本：人工智能的应用可以降低法律服务的成本，使法律服务更加普惠和可及。  
    改善决策准确性：人工智能可以通过数据分析和模式识别提供更准确的法律决策支持，减少人为错误的发生。  
    四、人工智能在法律领域所面临的挑战

    隐私和数据保护：人工智能需要处理大量的个人数据，涉及隐私和数据保护的问题。  
    道德和伦理问题：人工智能的决策过程可能涉及道德和伦理问题，如公平性、歧视性等。  
    法律责任和监管：人工智能的应用可能带来法律责任和监管的挑战，如算法歧视、不透明性等。  
    五、应对策略

    建立适应人工智能的法律框架：制定相关法律法规，明确人工智能在法律领域的应用和限制。  
    加强教育和培训：培养法律专业人才对人工智能的理解和应用能力，提高法律从业者的数字素养。  
    加强监管和合规：建立有效的监管机制，监督人工智能的应用，保障公众利益和法律体系的稳定性。  
    促进合作与跨界对话：法律领域需要与技术领域进行更多的合作与对话，共同应对人工智能带来的挑战。  
    六、结论  
    人工智能对法律领域具有深远的影响和

    挑战。为了充分发挥人工智能在法律领域的潜力，我们需要制定适应人工智能的法律框架，加强教育培训，加强监管合规，并促进领域间的合作与对话。通过这些努力，我们可以确保人工智能在法律领域的应用更好地服务于社会公众，并维护法律体系的稳定和公正。”

    请用以下格式输出，不要输出多余的东西：  
    {  
    观点1：“这里是文档的第一个观点”  
    观点2：“这里是文档的第二个观点”  
    观点3：“这里是文档的第三个观点”  
    }"""

    Ta = """
    {
    观点1：“人工智能在法律领域的应用包括智能合同的生成和执行、法律研究的辅助、司法决策的支持，以及自动化的法律服务提供。”
    观点2：“人工智能对法律行业的影响表现在加速信息处理、提高工作效率、降低服务成本，以及改善法律决策的准确性等方面。”
    观点3：“人工智能在法律领域所面临的挑战包括隐私和数据保护、道德和伦理问题、以及法律责任和监管问题。”
    }"""
    main_point = rwkv_chat("你是一位信息处理专家，请在以下文档中提取5个观点：“" + text +"”"+ point_format, Tq, Ta)
    return main_point



# 假设 sumtext 和 get_main_point 函数已经定义好了
# sumtext = [...]  
# def get_main_point(s: str) -> str: ...

def worker0(text, q):
    result = get_main_point(text)
    q.put(result)

def summarize_text(text_list):
    q = queue.Queue()
    threads = []
    for text in text_list:
        t = threading.Thread(target=worker0, args=(text, q))
        t.start()
        threads.append(t)
    # 等待所有线程完成
    for t in threads:
        t.join()
    # 收集结果
    points = ""
    while not q.empty():
        points += q.get()
    return points

# 调用函数，把sumtext的内容通过多线程进行总结




def get_outline(point,topic):
    main_point = rwkv_chat_s("以下是几个观点：" + point + "请参考这些观点写一个论文提纲,题目为《"+ topic + "》，要求观点具体，论证翔实，令人信服")
    print(main_point)
    file_path = "/Users/a.h./Documents/rwkv_write/testonline.txt"
    save_string_to_file(main_point, file_path)
    return main_point      






def split_outline(text):
    lines = text.split('\n')

    secondary_headings = []
    tertiary_headings = []

    # 处理每一行，提取标题
    for line in lines:
        line = line.strip()
        if re.match("^[一二三四五六七八九十]+、", line):
            continue
        elif re.match("^A.|^B.|^C.|^D.|^E.|^F.|^G.|^H.|^I.|^J.|^K.|^L.|^M.|^N.|^O.|^P.|^Q.|^R.|^S.|^T.|^U.|^V.|^W.|^X.|^Y.|^Z.", line):
            secondary_headings.append(line)
        elif re.match("^\d+.", line):
            tertiary_headings.append(line)

    # 将二级和三级标题放入一个元组
    combined_headings = secondary_headings + tertiary_headings
    headings_tuple = tuple(combined_headings)
    print(headings_tuple)
    return headings_tuple




def get_keyword(topic,sub_titles):
    keyword = rwkv_chat("你现在需要写作主题为《" + topic + "》的论文的一部份：“"+ sub_titles + """”，请分析搜索你可能需要的资料所需要的关键词，用以下格式输出，不要有多余的文字或内容，直接输出关键词即可：
["关键词1","关键词2","关键词3","关键词4","关键词5"]""","""你现在需要写作主题为《人工智能时代的隐私保护》的论文的一部份：“1. 数据泄露风险分析”，请分析搜索你可能需要的资料所需要的关键词，用以下格式输出，不要有多余的文字或内容，直接输出关键词即可：
["关键词1","关键词2","关键词3","关键词4","关键词5"]""","""["人工智能与数据泄露","隐私保护技术","数据加密","网络安全风险","大数据隐私"]""")
    print("keyword" + keyword)
    return keyword


def find_keyword_context(text, keyword, context_len=250):
    # 检查输入类型，如果text是字节类型，尝试解码为字符串
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8')  # 这里假设文本是utf-8编码，你可能需要根据具体情况修改
        except Exception as e:
            print(f'Error while decoding text: {e}')
            return []
    
    keyword = re.escape(keyword) 
    # 用正则表达式找出关键词的位置
    # matches = [m.start() for m in re.finditer(keyword, text)]
    matches = [m.start() for m in re.finditer(keyword, text)]
    # 对于每一个关键词，提取前后context_len个字符的上下文
    contexts = []
    for match in matches:
        start = max(0, match - context_len)
        end = min(len(text), match + len(keyword) + context_len)
        context = text[start:end]
        contexts.append(context)    
    return contexts

def get_related_content(sub_titles,findtext):
    findtext = "".join(findtext)
    print("findtext" + findtext)
    related_content = rwkv_chat_s("在以下资料中提取：“" + sub_titles + "”主题有关的信息，如果没有相关信息，请自行写作相关信息:" + "\n" + findtext)
    
    print("related_content" + related_content)
    return related_content
         

def rwkv_summairze(sub_titles,alltext):
    
    summairze = rwkv_chat_s("总结以下信息中与“" + sub_titles + "”主题有关的信息，要求在500字以内" + "\n" + alltext)
    print("summairze" + summairze)
    return summairze
    

def get_write(topic,sub_titles,material):
    paragraph = rwkv_chat_s("请根据主题《" + topic + "》对下列段落进行详细的撰写：" + "\n" + sub_titles + "参考以下资料" + material)
    print(paragraph)
    return paragraph


def worker(i, topic, sub_title, text, results):
    keywords = get_keyword(topic, sub_title)
    alltext = ""

    for keyword in keywords:
        # contexts = find_keyword_context(text, keyword, context_len=250)
        # if contexts:  # 判断contexts是否为空
        #     context = contexts[-1] # 取第一个context
        #     related_content = get_related_content(sub_title, context)
        #     alltext += ' ' + related_content

        contexts = find_keyword_context(text, keyword, context_len=250)

        if contexts:  # 检查contexts是否为空
            middle_index = len(contexts) // 2  # 计算中间索引
            context = contexts[middle_index]  # 获取中间的上下文

            related_content = get_related_content(sub_title, context)
            alltext += ' ' + related_content



    material = rwkv_summairze(sub_title, alltext.strip())
    paragraph = get_write(topic, sub_title, material)
    results[i] = paragraph  # Put result into correct place in list



def write_paper(points, topic, text):
    outline = get_outline(points, topic)
    sub_titles = split_outline(outline)
    
    results = [None] * len(sub_titles)  # Create list to store results
    
    for i, sub_title in enumerate(sub_titles):
        worker(i, topic, sub_title, text, results)  # Call worker directly
    
    paper = ''.join(results)
    return paper




def save_string_to_file(string, file_path):
    try:
        with open(file_path, 'w') as file:
            file.write(string)
        print("字符串成功保存到文件中！")
    except IOError:
        print("写入文件时发生错误！")
    except Exception as e:
        print("发生未知错误:", str(e))

def main():
    print(rawtext)
    sumtext = summarize(rawtext)
    print(sumtext)
    points = summarize_text(sumtext)
    print(points)
    # points = 'some points'

    text = rawtext
    paper = write_paper(points, topic, text)
    # print(paper)
    save_string_to_file(paper, file_path)
if __name__ == '__main__':
    main()

