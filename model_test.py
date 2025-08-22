import ollama
import os
import time

if __name__ == '__main__':
    prompt = ("You are a highly talented Slovak journalist, and you want to classify articles as either liberal, "
              "neutral, or conservative.  In your responses, you can only list a single classification, "
              "and cannot list any other words.  For example, if you classify an article as politically neutral, "
              "you will only say the word neutral.  If you classify an article as liberal, you will only "
              "say the word liberal.  If you classify an article as conservative, you will also only say the word "
              "conservative. Under no circumstances should you list more than a single classification in your "
              "responses, or a single word other than the classification.  Classify the following article:")
    models = ["gemma3", "deepseek-r1:8b"]

    for model in models:
        avg_time = 0
        accuracy = 0
        cnt = 0
        for article_type in ["neutral", "conservative", "liberal"]:
            for file in os.listdir(os.fsencode(f"data/{article_type}")):
                filename = os.fsdecode(file)
                start_time = time.time()
                result = ollama.generate(model=model, prompt=prompt)
                avg_time += time.time() - start_time
                judgement = result["response"].split("</think>")[-1]
                if judgement.strip().lower() == article_type:
                    accuracy += 1
                cnt += 1
        accuracy = accuracy / cnt
        avg_time = avg_time / cnt
        with open("model_logs", "a") as f:
            f.write(f"Accuracy of {model} was {accuracy} with average time {avg_time}\n")