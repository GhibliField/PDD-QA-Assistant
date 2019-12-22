from cocurrent import QA
from config import Config
config = Config()
config.display()
qa = QA(config)
def run(qa):
    qa_info = qa.get_info()
    try:
        qa.get_answer_by_wordcount_cocurrently(qa_info)
    except Exception as e:
        pass
# HOW-TO-RUN: shell> run(qa)
