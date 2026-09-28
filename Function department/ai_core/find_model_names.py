import re

filepath = r"C:\Users\TUF\AppData\Local\Programs\node24\node_modules\n8n\node_modules\@n8n\n8n-nodes-langchain\dist\nodes\llms\LmChatGoogleGemini\LmChatGoogleGemini.node.js"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# find modelName or default models
matches = re.findall(r"(modelName|models/[a-zA-Z0-9\.\-]+|gemini\-[a-zA-Z0-9\.\-]+)", content)
print("Unique model identifiers:", set(matches))
